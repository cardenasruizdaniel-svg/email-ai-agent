import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.settings import settings
from database.db import AsyncSessionLocal
from backend.email_client.factory import get_email_client
from backend.services.dispatcher import EmailDispatcher

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def poll_and_process_emails():
    """Periodic job to fetch and process new emails."""
    logger.info("[Scheduler] Polling for new incoming emails...")
    email_client = get_email_client()
    dispatcher = EmailDispatcher(email_client)

    try:
        new_emails = await email_client.fetch_unprocessed_emails(max_results=20)
        if not new_emails:
            logger.info("[Scheduler] No new emails found.")
            return

        logger.info(f"[Scheduler] Found {len(new_emails)} emails to process.")
        
        async with AsyncSessionLocal() as db:
            for email_raw in new_emails:
                try:
                    await dispatcher.process_incoming_email(email_raw, db)
                except Exception as ex:
                    logger.error(f"[Scheduler] Error processing email {email_raw.get('id')}: {ex}", exc_info=True)
                    
    except Exception as e:
        logger.error(f"[Scheduler] Error during polling cycle: {e}", exc_info=True)


def start_scheduler():
    interval = settings.POLL_INTERVAL_MINUTES
    scheduler.add_job(
        poll_and_process_emails,
        'interval',
        minutes=interval,
        id='poll_emails_job',
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"[Scheduler] Background scheduler started (Polling every {interval} minute(s)).")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] Scheduler stopped.")
