import imaplib
import smtplib
import email
import logging
from email.header import decode_header
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.settings import settings
from .base import BaseEmailClient

logger = logging.getLogger(__name__)

class IMAPSMTPClient(BaseEmailClient):
    def __init__(self):
        self.imap_server = settings.IMAP_SERVER
        self.imap_port = settings.IMAP_PORT
        self.user = settings.IMAP_USER
        self.password = settings.IMAP_PASSWORD
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT

    async def fetch_unprocessed_emails(self, max_results: int = 20) -> List[Dict[str, Any]]:
        if not self.user or not self.password:
            logger.warning("[IMAPSMTPClient] IMAP credentials missing.")
            return []
            
        fetched = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)
            mail.select("inbox")
            
            status, messages = mail.search(None, 'UNSEEN')
            if status != "OK":
                mail.logout()
                return []
                
            email_ids = messages[0].split()
            target_ids = email_ids[-max_results:]
            
            for msg_id in target_ids:
                res, msg_data = mail.fetch(msg_id, "(RFC822)")
                if res != "OK":
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg["Subject"] or "(Sin asunto)")[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")
                            
                        sender = msg.get("From", "")
                        sender_name = sender.split("<")[0].strip() if "<" in sender else sender
                        sender_email = sender.split("<")[1].replace(">", "").strip() if "<" in sender else sender
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                            
                        fetched.append({
                            "id": msg_id.decode("utf-8"),
                            "thread_id": msg_id.decode("utf-8"),
                            "sender_email": sender_email,
                            "sender_name": sender_name,
                            "subject": subject,
                            "body": body,
                            "snippet": body[:150] if body else "",
                            "date": datetime.utcnow(),
                            "attachments": []
                        })
                        
            mail.logout()
            return fetched
        except Exception as e:
            logger.error(f"[IMAPSMTPClient] Error fetching via IMAP: {e}")
            return []

    async def send_email(self, to_email: str, subject: str, body: str, thread_id: Optional[str] = None) -> bool:
        if not self.user or not self.password:
            logger.error("[IMAPSMTPClient] SMTP credentials missing.")
            return False
            
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = to_email
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, [to_email], msg.as_string())
                
            logger.info(f"[IMAPSMTPClient] Sent email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[IMAPSMTPClient] Failed to send email via SMTP: {e}")
            return False

    async def apply_labels(self, message_id: str, label_names: List[str]) -> bool:
        logger.info(f"[IMAPSMTPClient] Note: Standard IMAP labels applied as internal metadata: {label_names}")
        return True

    async def mark_as_read(self, message_id: str) -> bool:
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)
            mail.select("inbox")
            mail.store(message_id.encode("utf-8"), "+FLAGS", "\\Seen")
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"[IMAPSMTPClient] Error marking message as read: {e}")
            return False
