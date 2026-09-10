import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.email_client.base import BaseEmailClient
from ai.analyzer import EmailAnalyzer
from database.repository import Repository
from .decision_engine import DecisionEngine
from .reply_generator import ReplyGenerator

logger = logging.getLogger(__name__)

class EmailDispatcher:
    def __init__(self, email_client: BaseEmailClient):
        self.email_client = email_client
        self.analyzer = EmailAnalyzer()
        self.reply_generator = ReplyGenerator()

    async def process_incoming_email(self, email_raw: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Executes the 7-step fundamental rule pipeline:
        1. Understand -> 2. Classify -> 3. Prioritize -> 4. Organize -> 5. Decide -> 6. Respond -> 7. Record
        """
        msg_id = email_raw["id"]
        thread_id = email_raw.get("thread_id", msg_id)
        sender_email = email_raw["sender_email"]
        sender_name = email_raw.get("sender_name", "")
        subject = email_raw.get("subject", "")
        body = email_raw.get("body", "")
        attachments = email_raw.get("attachments", [])

        logger.info(f"[EmailDispatcher] Processing incoming email '{subject}' from {sender_email}")

        # Step 1: Check past conversation thread memory
        past_thread = await Repository.get_thread_history(db, thread_id)
        thread_context_str = ""
        if past_thread:
            thread_context_str = f" [Hilo previo de conversación con {len(past_thread)} mensajes asociados]"
            logger.info(f"[EmailDispatcher] Associated email with existing thread {thread_id}")

        # Step 2: Run AI Intent & Classification Analysis
        ai_analysis = await self.analyzer.process_email(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            body=body + thread_context_str,
            attachments=attachments
        )

        # Step 3: Fetch active custom rules & evaluate Decision Engine
        rules = await Repository.get_active_rules(db)
        decision = DecisionEngine.evaluate(ai_analysis, rules)

        # Step 4: Generate draft reply if reply is possible
        draft_reply = ""
        if decision.get("can_auto_reply") or decision.get("requires_human_review"):
            draft_reply = await self.reply_generator.generate_response(decision)

        decision["draft_reply"] = draft_reply

        # Step 5: Update Sender Memory Profile
        sender_profile = await Repository.get_or_create_sender(
            db=db,
            email=sender_email,
            name=sender_name,
            company=decision.get("company", ""),
            topic=decision.get("category", ""),
            priority=decision.get("priority", "MEDIA")
        )

        # Step 6: Save email record to SQLite DB
        db_email_dict = {
            "id": msg_id,
            "thread_id": thread_id,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "company": decision.get("company", sender_profile.company),
            "subject": subject,
            "body": body,
            "snippet": email_raw.get("snippet", body[:150]),
            "date": email_raw.get("date"),
            "category": decision["category"],
            "subcategories": decision.get("subcategories", []),
            "tags": decision.get("tags", []),
            "priority": decision["priority"],
            "confidence": decision["confidence"],
            "risk_level": decision["risk_level"],
            "risk_reasons": decision.get("risk_reasons", []),
            "requires_human_review": decision["requires_human_review"],
            "can_auto_reply": decision["can_auto_reply"],
            "status": decision.get("status", "PENDIENTE"),
            "intent_summary": decision.get("intent_summary", ""),
            "draft_reply": draft_reply,
            "sent_reply": "",
            "attachments_info": attachments
        }

        # Step 7: Apply Email Labels via Email Client API
        if decision.get("tags"):
            await self.email_client.apply_labels(msg_id, decision["tags"])

        # Step 8: Execute Auto-Reply if allowed
        sent_success = False
        action_name = "CLASIFICADO_Y_ETIQUETADO"

        if decision.get("can_auto_reply") and draft_reply:
            logger.info(f"[EmailDispatcher] Auto-replying to email {msg_id}")
            reply_subject = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
            sent_success = await self.email_client.send_email(
                to_email=sender_email,
                subject=reply_subject,
                body=draft_reply,
                thread_id=thread_id
            )
            if sent_success:
                db_email_dict["status"] = "RESPONDIDO_IA"
                db_email_dict["sent_reply"] = draft_reply
                action_name = "RESPONDIDO_AUTOMATICO"
        elif decision.get("requires_human_review"):
            action_name = "ENVIADO_REVISION_HUMANA"

        # Mark email as read in remote client
        await self.email_client.mark_as_read(msg_id)

        # Save to database
        saved_record = await Repository.save_email(db, db_email_dict)

        # Log action to audit history
        await Repository.log_activity(
            db=db,
            email_id=msg_id,
            sender_email=sender_email,
            subject=subject,
            category=decision["category"],
            confidence=decision["confidence"],
            action_taken=action_name,
            details=f"Prioridad: {decision['priority']} | Riesgo: {decision['risk_level']} | Confianza: {decision['confidence']}%",
            status="SUCCESS" if (not decision.get("can_auto_reply") or sent_success) else "WARNING"
        )

        return db_email_dict
