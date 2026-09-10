import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Sender, EmailMessage, CustomRule, ActivityLog, UserCorrection

logger = logging.getLogger(__name__)

class Repository:
    @staticmethod
    async def get_or_create_sender(
        db: AsyncSession,
        email: str,
        name: str = "",
        company: str = "",
        topic: str = "",
        priority: str = "MEDIA"
    ) -> Sender:
        """Retrieves or creates a sender profile, updating interaction counts and history."""
        email_clean = email.strip().lower()
        stmt = select(Sender).where(Sender.email == email_clean)
        result = await db.execute(stmt)
        sender = result.scalar_one_or_none()

        if sender:
            sender.last_interaction = datetime.utcnow()
            sender.total_emails += 1
            if name and not sender.name:
                sender.name = name
            if company and not sender.company:
                sender.company = company
                
            # Update frequent topics list
            topics = json.loads(sender.frequent_topics or "[]")
            if topic and topic not in topics:
                topics.append(topic)
                sender.frequent_topics = json.dumps(topics[:10])
        else:
            topics = [topic] if topic else []
            sender = Sender(
                email=email_clean,
                name=name,
                company=company,
                frequent_topics=json.dumps(topics),
                last_interaction=datetime.utcnow(),
                priority=priority,
                status="Activo",
                total_emails=1
            )
            db.add(sender)

        await db.commit()
        await db.refresh(sender)
        return sender

    @staticmethod
    async def get_thread_history(db: AsyncSession, thread_id: str) -> List[EmailMessage]:
        """Fetches all past emails in the same thread for conversation memory."""
        stmt = select(EmailMessage).where(EmailMessage.thread_id == thread_id).order_by(EmailMessage.date.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def save_email(db: AsyncSession, email_data: Dict[str, Any]) -> EmailMessage:
        """Saves or updates an email record in SQLite."""
        msg_id = email_data["id"]
        stmt = select(EmailMessage).where(EmailMessage.id == msg_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        tags_json = json.dumps(email_data.get("tags", []))
        subcategories_json = json.dumps(email_data.get("subcategories", []))
        risk_reasons_json = json.dumps(email_data.get("risk_reasons", []))
        attachments_json = json.dumps(email_data.get("attachments_info", []))

        if existing:
            for key in ["category", "priority", "confidence", "risk_level", "requires_human_review",
                        "can_auto_reply", "status", "intent_summary", "draft_reply", "sent_reply"]:
                if key in email_data:
                    setattr(existing, key, email_data[key])
            existing.tags = tags_json
            existing.subcategories = subcategories_json
            existing.risk_reasons = risk_reasons_json
            existing.updated_at = datetime.utcnow()
            email_record = existing
        else:
            email_record = EmailMessage(
                id=msg_id,
                thread_id=email_data.get("thread_id", msg_id),
                sender_email=email_data["sender_email"].strip().lower(),
                sender_name=email_data.get("sender_name", ""),
                company=email_data.get("company", ""),
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
                snippet=email_data.get("snippet", ""),
                date=email_data.get("date", datetime.utcnow()),
                category=email_data.get("category", "INFORMACION"),
                subcategories=subcategories_json,
                tags=tags_json,
                priority=email_data.get("priority", "MEDIA"),
                confidence=email_data.get("confidence", 0.0),
                risk_level=email_data.get("risk_level", "BAJO"),
                risk_reasons=risk_reasons_json,
                requires_human_review=email_data.get("requires_human_review", False),
                can_auto_reply=email_data.get("can_auto_reply", False),
                status=email_data.get("status", "PENDIENTE"),
                intent_summary=email_data.get("intent_summary", ""),
                draft_reply=email_data.get("draft_reply", ""),
                sent_reply=email_data.get("sent_reply", ""),
                attachments_info=attachments_json
            )
            db.add(email_record)

        await db.commit()
        await db.refresh(email_record)
        return email_record

    @staticmethod
    async def log_activity(
        db: AsyncSession,
        email_id: str,
        sender_email: str,
        subject: str,
        category: str,
        confidence: float,
        action_taken: str,
        details: str = "",
        status: str = "SUCCESS"
    ) -> ActivityLog:
        """Records an operational event in activity_logs."""
        log = ActivityLog(
            timestamp=datetime.utcnow(),
            email_id=email_id,
            sender_email=sender_email,
            subject=subject,
            category=category,
            confidence=confidence,
            action_taken=action_taken,
            details=details,
            status=status
        )
        db.add(log)
        await db.commit()
        return log

    @staticmethod
    async def get_active_rules(db: AsyncSession) -> List[CustomRule]:
        """Retrieves all active custom user rules."""
        stmt = select(CustomRule).where(CustomRule.is_active == True)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_dashboard_metrics(db: AsyncSession) -> Dict[str, Any]:
        """Calculates dashboard counter statistics."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Total received
        stmt_total = select(func.count(EmailMessage.id))
        total_rec = (await db.execute(stmt_total)).scalar() or 0

        # Auto-replied
        stmt_replied = select(func.count(EmailMessage.id)).where(EmailMessage.status == "RESPONDIDO_IA")
        total_replied = (await db.execute(stmt_replied)).scalar() or 0

        # Relevant info
        stmt_info = select(func.count(EmailMessage.id)).where(EmailMessage.category == "INFORMACION")
        total_info = (await db.execute(stmt_info)).scalar() or 0

        # Require human review
        stmt_review = select(func.count(EmailMessage.id)).where(EmailMessage.requires_human_review == True, EmailMessage.status == "PENDIENTE")
        total_review = (await db.execute(stmt_review)).scalar() or 0

        # Urgent emails
        stmt_urgent = select(func.count(EmailMessage.id)).where(EmailMessage.priority == "CRITICA")
        total_urgent = (await db.execute(stmt_urgent)).scalar() or 0

        # Emails with attachments
        stmt_attach = select(func.count(EmailMessage.id)).where(EmailMessage.attachments_info != "[]")
        total_attach = (await db.execute(stmt_attach)).scalar() or 0

        return {
            "total_received": total_rec,
            "auto_replied": total_replied,
            "info_relevant": total_info,
            "pending_review": total_review,
            "urgent": total_urgent,
            "with_attachments": total_attach
        }
