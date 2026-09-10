import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from config.settings import settings
from database.db import init_db, get_db
from database.models import EmailMessage, Sender, CustomRule, ActivityLog, UserCorrection
from database.repository import Repository
from backend.email_client.factory import get_email_client
from backend.services.scheduler import start_scheduler, stop_scheduler, poll_and_process_emails

# Configure Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email_agent_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing Database...")
    await init_db()
    
    logger.info("Starting 24/7 Background Scheduler...")
    start_scheduler()
    
    # Run initial sync on startup
    asyncio.create_task(poll_and_process_emails())
    
    yield
    
    # Shutdown logic
    stop_scheduler()
    logger.info("Application Shutdown Complete.")

app = FastAPI(
    title="AI Email Management Agent",
    description="100% Autonomous, Zero-Cost AI Email Management Agent API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ENDPOINTS ---

@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Returns dashboard counter statistics."""
    metrics = await Repository.get_dashboard_metrics(db)
    metrics["mode"] = settings.OPERATIONAL_MODE
    metrics["ai_provider"] = settings.AI_PROVIDER
    metrics["email_provider"] = settings.EMAIL_PROVIDER
    return metrics

@app.get("/api/emails")
async def list_emails(
    category: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    requires_review: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Lists email messages with optional filtering."""
    stmt = select(EmailMessage).order_by(EmailMessage.date.desc())

    if category:
        stmt = stmt.where(EmailMessage.category == category.upper())
    if status:
        stmt = stmt.where(EmailMessage.status == status.upper())
    if priority:
        stmt = stmt.where(EmailMessage.priority == priority.upper())
    if requires_review is not None:
        stmt = stmt.where(EmailMessage.requires_human_review == requires_review)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (EmailMessage.subject.ilike(pattern)) |
            (EmailMessage.sender_email.ilike(pattern)) |
            (EmailMessage.sender_name.ilike(pattern)) |
            (EmailMessage.body.ilike(pattern))
        )

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    output = []
    for msg in messages:
        output.append({
            "id": msg.id,
            "thread_id": msg.thread_id,
            "sender_email": msg.sender_email,
            "sender_name": msg.sender_name,
            "company": msg.company,
            "subject": msg.subject,
            "snippet": msg.snippet,
            "date": msg.date.isoformat() if msg.date else "",
            "category": msg.category,
            "tags": json.loads(msg.tags or "[]"),
            "subcategories": json.loads(msg.subcategories or "[]"),
            "priority": msg.priority,
            "confidence": msg.confidence,
            "risk_level": msg.risk_level,
            "risk_reasons": json.loads(msg.risk_reasons or "[]"),
            "requires_human_review": msg.requires_human_review,
            "can_auto_reply": msg.can_auto_reply,
            "status": msg.status,
            "intent_summary": msg.intent_summary,
            "draft_reply": msg.draft_reply,
            "sent_reply": msg.sent_reply,
            "has_attachment": bool(json.loads(msg.attachments_info or "[]"))
        })

    return output

@app.get("/api/emails/{msg_id}")
async def get_email_detail(msg_id: str, db: AsyncSession = Depends(get_db)):
    """Returns complete details of a single email message."""
    stmt = select(EmailMessage).where(EmailMessage.id == msg_id)
    result = await db.execute(stmt)
    msg = result.scalar_one_or_none()

    if not msg:
        raise HTTPException(status_code=404, detail="Email not found")

    thread_msgs = await Repository.get_thread_history(db, msg.thread_id)

    return {
        "id": msg.id,
        "thread_id": msg.thread_id,
        "sender_email": msg.sender_email,
        "sender_name": msg.sender_name,
        "company": msg.company,
        "subject": msg.subject,
        "body": msg.body,
        "snippet": msg.snippet,
        "date": msg.date.isoformat() if msg.date else "",
        "category": msg.category,
        "subcategories": json.loads(msg.subcategories or "[]"),
        "tags": json.loads(msg.tags or "[]"),
        "priority": msg.priority,
        "confidence": msg.confidence,
        "risk_level": msg.risk_level,
        "risk_reasons": json.loads(msg.risk_reasons or "[]"),
        "requires_human_review": msg.requires_human_review,
        "can_auto_reply": msg.can_auto_reply,
        "status": msg.status,
        "intent_summary": msg.intent_summary,
        "draft_reply": msg.draft_reply,
        "sent_reply": msg.sent_reply,
        "attachments": json.loads(msg.attachments_info or "[]"),
        "thread_count": len(thread_msgs)
    }

@app.post("/api/emails/{msg_id}/approve-reply")
async def approve_reply(
    msg_id: str,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Human approval / edit action to send reply."""
    reply_text = payload.get("reply_text")
    
    stmt = select(EmailMessage).where(EmailMessage.id == msg_id)
    result = await db.execute(stmt)
    msg = result.scalar_one_or_none()

    if not msg:
        raise HTTPException(status_code=404, detail="Email not found")

    text_to_send = reply_text if reply_text else msg.draft_reply
    if not text_to_send:
        raise HTTPException(status_code=400, detail="No reply text available to send.")

    email_client = get_email_client()
    reply_subject = f"Re: {msg.subject}" if not msg.subject.lower().startswith("re:") else msg.subject
    
    success = await email_client.send_email(
        to_email=msg.sender_email,
        subject=reply_subject,
        body=text_to_send,
        thread_id=msg.thread_id
    )

    if success:
        msg.status = "REVISADO_HUMANO"
        msg.sent_reply = text_to_send
        msg.requires_human_review = False
        
        # Add tag
        tags = json.loads(msg.tags or "[]")
        if "Respondido por IA" not in tags:
            tags.append("Respondido por IA")
        msg.tags = json.dumps(tags)
        
        await db.commit()

        await Repository.log_activity(
            db=db,
            email_id=msg.id,
            sender_email=msg.sender_email,
            subject=msg.subject,
            category=msg.category,
            confidence=msg.confidence,
            action_taken="APROBADO_Y_ENVIADO_HUMANO",
            details="Respuesta enviada exitosamente tras aprobación supervisada.",
            status="SUCCESS"
        )
        return {"status": "success", "message": "Respuesta enviada correctamente."}
    else:
        raise HTTPException(status_code=500, detail="Error al enviar el correo a través del cliente de correo.")

@app.post("/api/emails/{msg_id}/reclassify")
async def reclassify_email(
    msg_id: str,
    payload: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Allows user to correct category, priority, and tags for AI learning."""
    new_category = payload.get("category")
    new_priority = payload.get("priority")
    notes = payload.get("notes", "")

    stmt = select(EmailMessage).where(EmailMessage.id == msg_id)
    result = await db.execute(stmt)
    msg = result.scalar_one_or_none()

    if not msg:
        raise HTTPException(status_code=404, detail="Email not found")

    orig_category = msg.category
    orig_tags = msg.tags

    if new_category:
        msg.category = new_category.upper()
    if new_priority:
        msg.priority = new_priority.upper()

    await db.commit()

    # Save User Correction Record
    correction = UserCorrection(
        email_id=msg_id,
        original_category=orig_category,
        corrected_category=msg.category,
        original_tags=orig_tags,
        corrected_tags=msg.tags,
        notes=notes
    )
    db.add(correction)
    await db.commit()

    await Repository.log_activity(
        db=db,
        email_id=msg_id,
        sender_email=msg.sender_email,
        subject=msg.subject,
        category=msg.category,
        confidence=msg.confidence,
        action_taken="CORRECCION_USUARIO",
        details=f"Reclasificado de {orig_category} a {msg.category}. Notas: {notes}",
        status="SUCCESS"
    )

    return {"status": "success", "message": "Clasificación actualizada correctamente."}

@app.get("/api/senders")
async def list_senders(db: AsyncSession = Depends(get_db)):
    """Lists all remembered senders and statistics."""
    stmt = select(Sender).order_by(Sender.total_emails.desc())
    result = await db.execute(stmt)
    senders = result.scalars().all()

    output = []
    for s in senders:
        output.append({
            "id": s.id,
            "email": s.email,
            "name": s.name,
            "company": s.company,
            "frequent_topics": json.loads(s.frequent_topics or "[]"),
            "last_interaction": s.last_interaction.isoformat() if s.last_interaction else "",
            "priority": s.priority,
            "status": s.status,
            "total_emails": s.total_emails
        })
    return output

@app.get("/api/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    """Lists custom user rules."""
    stmt = select(CustomRule).order_by(CustomRule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return rules

@app.post("/api/rules")
async def create_rule(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Creates a custom rule."""
    rule = CustomRule(
        name=payload["name"],
        condition_type=payload["condition_type"],
        condition_value=payload["condition_value"],
        action_priority=payload.get("action_priority", ""),
        action_category=payload.get("action_category", ""),
        action_label=payload.get("action_label", ""),
        action_allow_autoreply=payload.get("action_allow_autoreply"),
        is_active=payload.get("is_active", True)
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Deletes a custom rule."""
    stmt = delete(CustomRule).where(CustomRule.id == rule_id)
    await db.execute(stmt)
    await db.commit()
    return {"status": "success"}

@app.get("/api/logs")
async def list_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Lists operational audit logs."""
    stmt = select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    output = []
    for l in logs:
        output.append({
            "id": l.id,
            "timestamp": l.timestamp.isoformat() if l.timestamp else "",
            "email_id": l.email_id,
            "sender_email": l.sender_email,
            "subject": l.subject,
            "category": l.category,
            "confidence": l.confidence,
            "action_taken": l.action_taken,
            "details": l.details,
            "status": l.status
        })
    return output

@app.post("/api/config/mode")
async def set_mode(payload: Dict[str, Any] = Body(...)):
    """Toggles operational mode between automatic and supervised."""
    new_mode = payload.get("mode", "automatic").lower()
    if new_mode not in ["automatic", "supervised"]:
        raise HTTPException(status_code=400, detail="Mode must be 'automatic' or 'supervised'")
    settings.OPERATIONAL_MODE = new_mode
    logger.info(f"[Config] Operational mode updated to: {new_mode}")
    return {"status": "success", "mode": settings.OPERATIONAL_MODE}

@app.post("/api/trigger-sync")
async def trigger_sync():
    """Triggers an immediate polling and execution cycle."""
    asyncio.create_task(poll_and_process_emails())
    return {"status": "success", "message": "Ciclo de lectura y clasificación iniciado."}


# Mount Static Frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
