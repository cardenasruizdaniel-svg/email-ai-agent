from config.settings import settings
from .base import BaseEmailClient
from .mock_client import MockEmailClient
from .gmail_client import GmailAPIClient
from .imap_client import IMAPSMTPClient

def get_email_client() -> BaseEmailClient:
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "gmail":
        return GmailAPIClient()
    elif provider == "imap":
        return IMAPSMTPClient()
    else:
        return MockEmailClient()
