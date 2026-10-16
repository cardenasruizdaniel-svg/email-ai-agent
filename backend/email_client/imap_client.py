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
                        attachments = []
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition", ""))
                                filename = part.get_filename()
                                if filename:
                                    dh = decode_header(filename)[0]
                                    if isinstance(dh[0], bytes):
                                        filename = dh[0].decode(dh[1] or "utf-8", errors="ignore")
                                    payload = part.get_payload(decode=True)
                                    attachments.append({
                                        "filename": filename,
                                        "mime_type": content_type,
                                        "bytes": payload,
                                        "content_text": ""
                                    })
                                elif content_type == "text/plain" and "attachment" not in content_disposition:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body += payload.decode("utf-8", errors="ignore") + "\n"
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="ignore")
                            
                        fetched.append({
                            "id": msg_id.decode("utf-8"),
                            "thread_id": msg_id.decode("utf-8"),
                            "sender_email": sender_email,
                            "sender_name": sender_name,
                            "subject": subject,
                            "body": body,
                            "snippet": body[:150] if body else "",
                            "date": datetime.utcnow(),
                            "attachments": attachments
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
            if thread_id:
                msg["In-Reply-To"] = f"<{thread_id}>"
                msg["References"] = f"<{thread_id}>"
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, [to_email], msg.as_string())
                
            logger.info(f"[IMAPSMTPClient] Sent email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[IMAPSMTPClient] Failed to send email via SMTP: {e}")
            return False

    async def forward_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        thread_id: Optional[str] = None,
        original_email_id: Optional[str] = None
    ) -> bool:
        if not self.user or not self.password:
            logger.error("[IMAPSMTPClient] SMTP credentials missing.")
            return False

        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = to_email
            if thread_id:
                msg["In-Reply-To"] = f"<{thread_id}>"
                msg["References"] = f"<{thread_id}>"

            msg.attach(MIMEText(body, "plain", "utf-8"))

            if attachments:
                for att in attachments:
                    fname = att.get("filename", "adjunto.pdf")
                    fbytes = att.get("bytes")
                    if not fbytes and att.get("content_text"):
                        fbytes = att.get("content_text").encode("utf-8")
                    if fbytes:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(fbytes)
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
                        msg.attach(part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, [to_email], msg.as_string())

            logger.info(f"[IMAPSMTPClient] Forwarded email to {to_email} with {len(attachments or [])} attachments")
            return True
        except Exception as e:
            logger.error(f"[IMAPSMTPClient] Failed to forward email: {e}")
            return False

    async def move_to_folder(self, message_id: str, folder_name: str) -> bool:
        if not self.user or not self.password:
            return False
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.user, self.password)
            try:
                mail.create(f'"{folder_name}"')
            except Exception:
                pass
            mail.select("inbox")
            res, _ = mail.copy(message_id.encode("utf-8"), f'"{folder_name}"')
            if res == "OK":
                mail.store(message_id.encode("utf-8"), "+FLAGS", "\\Deleted")
                mail.expunge()
                logger.info(f"[IMAPSMTPClient] Moved message {message_id} to folder '{folder_name}'")
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"[IMAPSMTPClient] Error moving to folder '{folder_name}': {e}")
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
