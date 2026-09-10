import os
import base64
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from email.mime.text import MIMEText

from config.settings import settings
from .base import BaseEmailClient

logger = logging.getLogger(__name__)

class GmailAPIClient(BaseEmailClient):
    def __init__(self):
        self.service = None
        self._init_service()

    def _init_service(self):
        """Initializes the Google API client service if credentials exist."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            
            creds = None
            token_path = settings.GMAIL_TOKEN_FILE
            
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/gmail.modify'])
            
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as token_file:
                    token_file.write(creds.to_json())
                    
            if creds and creds.valid:
                self.service = build('gmail', 'v1', credentials=creds)
                logger.info("[GmailAPIClient] Successfully initialized Gmail API service.")
            else:
                logger.warning("[GmailAPIClient] Gmail token not found or invalid. Set up OAuth credentials or use MOCK/IMAP mode.")
        except Exception as e:
            logger.error(f"[GmailAPIClient] Error initializing Gmail API: {e}")
            self.service = None

    async def fetch_unprocessed_emails(self, max_results: int = 20) -> List[Dict[str, Any]]:
        if not self.service:
            logger.warning("[GmailAPIClient] Service not initialized. Returning empty email list.")
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread label:INBOX',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            fetched = []
            
            for msg_summary in messages:
                msg_id = msg_summary['id']
                msg = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                
                payload = msg.get('payload', {})
                headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
                
                subject = headers.get('subject', '(Sin asunto)')
                sender = headers.get('from', '')
                date_str = headers.get('date', '')
                
                sender_name = sender.split('<')[0].strip() if '<' in sender else sender
                sender_email = sender.split('<')[1].replace('>', '').strip() if '<' in sender else sender
                
                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                            body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif 'body' in payload and 'data' in payload['body']:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                    
                fetched.append({
                    "id": msg_id,
                    "thread_id": msg.get("threadId", msg_id),
                    "sender_email": sender_email,
                    "sender_name": sender_name,
                    "subject": subject,
                    "body": body or msg.get("snippet", ""),
                    "snippet": msg.get("snippet", ""),
                    "date": datetime.utcnow(),
                    "attachments": []
                })
            return fetched
        except Exception as e:
            logger.error(f"[GmailAPIClient] Error fetching emails: {e}")
            return []

    async def send_email(self, to_email: str, subject: str, body: str, thread_id: Optional[str] = None) -> bool:
        if not self.service:
            logger.error("[GmailAPIClient] Cannot send email; service not initialized.")
            return False
            
        try:
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            body_dict = {'raw': raw_message}
            if thread_id:
                body_dict['threadId'] = thread_id
                
            self.service.users().messages().send(userId='me', body=body_dict).execute()
            logger.info(f"[GmailAPIClient] Sent email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[GmailAPIClient] Failed to send email: {e}")
            return False

    async def apply_labels(self, message_id: str, label_names: List[str]) -> bool:
        if not self.service:
            return False
            
        try:
            # Check or create labels
            existing_labels = self.service.users().labels().list(userId='me').execute().get('labels', [])
            label_map = {l['name']: l['id'] for l in existing_labels}
            
            add_ids = []
            for name in label_names:
                if name not in label_map:
                    # Create new label
                    new_lbl = self.service.users().labels().create(
                        userId='me',
                        body={'name': name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
                    ).execute()
                    label_map[name] = new_lbl['id']
                add_ids.append(label_map[name])
                
            if add_ids:
                self.service.users().messages().batchModify(
                    userId='me',
                    body={'ids': [message_id], 'addLabelIds': add_ids}
                ).execute()
            return True
        except Exception as e:
            logger.error(f"[GmailAPIClient] Error applying labels: {e}")
            return False

    async def mark_as_read(self, message_id: str) -> bool:
        if not self.service:
            return False
        try:
            self.service.users().messages().batchModify(
                userId='me',
                body={'ids': [message_id], 'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"[GmailAPIClient] Error marking message as read: {e}")
            return False
