from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

class BaseEmailClient(ABC):

    @abstractmethod
    async def fetch_unprocessed_emails(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Fetches new, unread, or unprocessed emails.
        Returns a list of dicts with keys:
        - id: str
        - thread_id: str
        - sender_email: str
        - sender_name: str
        - subject: str
        - body: str
        - snippet: str
        - date: datetime
        - attachments: List[Dict[str, Any]] (e.g. filename, content_bytes, mime_type)
        """
        pass

    @abstractmethod
    async def send_email(self, to_email: str, subject: str, body: str, thread_id: Optional[str] = None) -> bool:
        """Sends an email response to the specified recipient."""
        pass

    @abstractmethod
    async def apply_labels(self, message_id: str, label_names: List[str]) -> bool:
        """Applies labels/tags to the email message."""
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Marks the email message as processed/read."""
        pass
