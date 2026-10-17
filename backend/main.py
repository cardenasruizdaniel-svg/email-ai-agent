import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from config.settings import settings
from database.db import init_db, get_db
from database.models import (
    EmailMessage, Sender, CustomRule, ActivityLog, UserCorrection,
    WorkflowDefinition, CaseTicket, CaseHistoryLog, UserAccount
)
from database.repository import Repository
from backend.services.auth import AuthService
from backend.email_client.factory import get_email_client
from backend.services.scheduler import start_scheduler, stop_scheduler, poll_and_process_emails
from backend.services.workflow_engine import WorkflowEngine

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
    
    # Seed default workflows & users for IPS Domiciliaria
    from database.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            await Repository.get_or_create_default_workflows(session)
            await Repository.seed_default_users(session)
        except Exception as e:
            logger.warning(f"Could not run seeds on startup: {e}")

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

@app.get("/api/config/full")
async def get_full_config():
    """Returns complete dynamic system configuration."""
    return {
        "email_provider": settings.EMAIL_PROVIDER,
        "imap_user": settings.IMAP_USER,
        "imap_password": settings.IMAP_PASSWORD,
        "imap_server": settings.IMAP_SERVER,
        "imap_port": settings.IMAP_PORT,
        "smtp_server": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
        "ai_provider": settings.AI_PROVIDER,
        "gemini_api_key": settings.GEMINI_API_KEY,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "operational_mode": settings.OPERATIONAL_MODE,
        "poll_interval_minutes": settings.POLL_INTERVAL_MINUTES,
        "company_name": settings.COMPANY_NAME,
        "agent_name": settings.AGENT_NAME,
        "agent_role": settings.AGENT_ROLE,
        "reply_signature": settings.REPLY_SIGNATURE,
        "supervisor_email": getattr(settings, "SUPERVISOR_EMAIL", "coordinacion@clinica.com")
    }

@app.post("/api/config/full")
async def update_full_config(payload: Dict[str, Any] = Body(...)):
    """Dynamically updates system configuration in real-time."""
    for key, val in payload.items():
        attr = key.upper()
        if hasattr(settings, attr) and val is not None:
            setattr(settings, attr, val)

    logger.info(f"[Config] Dynamic system configuration updated for email: {settings.IMAP_USER}")
    
    # Save to .env if possible
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        lines = []
        for key in settings.model_fields.keys():
            val = getattr(settings, key)
            lines.append(f"{key}={val}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        logger.warning(f"[Config] Could not write to .env file: {e}")

    return {"status": "success", "message": "Configuración actualizada e implementada en tiempo real."}

@app.post("/api/trigger-sync")
async def trigger_sync():
    """Triggers an immediate polling and execution cycle."""
    asyncio.create_task(poll_and_process_emails())
    return {"status": "success", "message": "Ciclo de lectura y clasificación iniciado."}

# --- WORKFLOW & CASE TRACKING ENDPOINTS ---

@app.get("/api/workflows")
async def list_workflows(db: AsyncSession = Depends(get_db)):
    """Lists all configured workflows, seeding default clinical workflows if empty."""
    workflows = await Repository.get_or_create_default_workflows(db)
    output = []
    for wf in workflows:
        output.append({
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "trigger_keywords": json.loads(wf.trigger_keywords or "[]"),
            "trigger_category": wf.trigger_category,
            "target_folder": wf.target_folder,
            "supervisor_email": wf.supervisor_email,
            "steps": json.loads(wf.steps or "[]"),
            "is_active": wf.is_active
        })
    return output

@app.post("/api/workflows")
async def save_workflow(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Creates or updates a workflow definition."""
    wf_id = payload.get("id")
    steps_json = json.dumps(payload.get("steps", []))
    keywords_json = json.dumps(payload.get("trigger_keywords", []))

    if wf_id:
        stmt = select(WorkflowDefinition).where(WorkflowDefinition.id == wf_id)
        wf = (await db.execute(stmt)).scalar_one_or_none()
        if not wf:
            raise HTTPException(status_code=404, detail="Flujo no encontrado")
        wf.name = payload.get("name", wf.name)
        wf.description = payload.get("description", wf.description)
        wf.trigger_keywords = keywords_json
        wf.target_folder = payload.get("target_folder", wf.target_folder)
        wf.supervisor_email = payload.get("supervisor_email", wf.supervisor_email)
        wf.steps = steps_json
        wf.is_active = payload.get("is_active", True)
    else:
        wf = WorkflowDefinition(
            name=payload.get("name", "Nuevo Flujo"),
            description=payload.get("description", ""),
            trigger_keywords=keywords_json,
            target_folder=payload.get("target_folder", "General"),
            supervisor_email=payload.get("supervisor_email", settings.SUPERVISOR_EMAIL),
            steps=steps_json,
            is_active=payload.get("is_active", True)
        )
        db.add(wf)

    await db.commit()
    return {"status": "success", "message": "Flujo de trabajo guardado exitosamente."}

@app.get("/api/cases")
async def list_cases(
    status: Optional[str] = None,
    folder: Optional[str] = None,
    assigned_email: Optional[str] = None,
    stage: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Lists case tickets with traceability status, current holder, returns count, and folders."""
    cases = await Repository.get_cases(
        db, status=status, folder=folder,
        assigned_email=assigned_email, stage=stage,
        limit=limit
    )
    return cases

@app.get("/api/cases/{case_id}")
async def get_case_details(case_id: int, db: AsyncSession = Depends(get_db)):
    """Returns full case ticket details and complete history audit trail."""
    case = await Repository.get_case_details(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return case

@app.post("/api/cases/{case_id}/advance")
async def advance_case_step(case_id: int, payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Advances case to next user in chain or completes it back to the supervisor."""
    stmt = select(CaseTicket).where(CaseTicket.id == case_id)
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    actor_email = payload.get("actor_email") or case.current_assigned_email
    comments = payload.get("comments") or "Aprobado manualmente desde el panel de control"

    engine = WorkflowEngine(get_email_client())
    updated_case = await engine.advance_step(db, case, actor_email=actor_email, comments=comments)

    return {
        "status": "success",
        "case_code": updated_case.case_code,
        "new_status": updated_case.status,
        "current_step_name": updated_case.current_step_name,
        "current_assigned_email": updated_case.current_assigned_email,
        "total_transitions": updated_case.total_transitions
    }

@app.post("/api/cases/{case_id}/problem")
async def report_case_problem(case_id: int, payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Reports a problem/rejection, immediately alerting the Supervisor (Principal User)."""
    stmt = select(CaseTicket).where(CaseTicket.id == case_id)
    case = (await db.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    actor_email = payload.get("actor_email") or case.current_assigned_email
    reason = payload.get("reason") or "Problema o retraso reportado"
    bottleneck_category = payload.get("bottleneck_category") or "Rechazo / Inconsistencia"

    engine = WorkflowEngine(get_email_client())
    updated_case = await engine.report_problem(
        db, case,
        actor_email=actor_email,
        reason=reason,
        bottleneck_category=bottleneck_category
    )

    return {
        "status": "success",
        "case_code": updated_case.case_code,
        "new_status": updated_case.status,
        "last_problem_reported": updated_case.last_problem_reported,
        "total_returns": updated_case.total_returns,
        "alert_sent_to": updated_case.supervisor_email
    }

@app.post("/api/cases/{case_id}/resolve")
async def resolve_case_problem(case_id: int, payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Unblocks a case stopped by problem/rejection. Logs resolution and notifies assigned user."""
    resolved_by = payload.get("resolved_by") or settings.SUPERVISOR_EMAIL
    resolution_notes = payload.get("resolution_notes") or "Novedad resuelta por la Coordinación"
    resume_step = payload.get("resume_step", None)

    case = await Repository.resolve_case_problem(
        db, case_id=case_id,
        resolved_by=resolved_by,
        resolution_notes=resolution_notes,
        resume_step_number=resume_step
    )
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Send unblock notice to the operator
    client = get_email_client()
    notice_subject = f"[REANUDADO] Caso {case.case_code} desmarcado - Listo para diligencia: {case.patient_name}"
    notice_body = (
        f"Estimado/a equipo ({case.current_assigned_email}),\n\n"
        f"La novedad reportada para el caso {case.case_code} del paciente {case.patient_name} "
        f"ha sido resuelta por la Coordinación ({resolved_by}).\n\n"
        f"NOTAS DE SUBSANACIÓN / ACCIÓN:\n"
        f"{resolution_notes}\n\n"
        f"El caso se encuentra nuevamente en estado ACTIVO en su bandeja para continuar el flujo de atención domiciliaria."
    )
    try:
        await client.send_email(
            to_email=case.current_assigned_email,
            subject=notice_subject,
            body=notice_body,
            thread_id=case.thread_id
        )
    except Exception as e:
        logger.warning(f"Failed to dispatch resolution email: {e}")

    return {
        "status": "success",
        "message": "Novedad resuelta exitosamente. Flujo reanudado.",
        "case_code": case.case_code,
        "status": case.status,
        "current_step_name": case.current_step_name
    }

@app.get("/api/reports/bottlenecks")
async def get_bottleneck_report(db: AsyncSession = Depends(get_db)):
    """Returns analytics report on delays, bottlenecks, stoppage reasons, and returns."""
    return await Repository.get_bottleneck_report(db)

# ================= AUTHENTICATION & USER MANAGEMENT ENDPOINTS =================

@app.post("/api/auth/login")
async def auth_login(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Authenticates user credentials and issues a secure session token."""
    username = payload.get("username", "").strip().lower()
    password = payload.get("password", "")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Debe ingresar usuario y contraseña")

    user = await Repository.get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos, o cuenta inactiva")

    if not AuthService.verify_password(password, user.password_hash, user.salt):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    user.last_login = datetime.utcnow()
    await db.commit()

    token = AuthService.create_session(user)
    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "assigned_stage": user.assigned_stage,
            "phone": user.phone
        }
    }

@app.get("/api/auth/me")
async def auth_me(token: Optional[str] = Query(None)):
    """Validates the current session token."""
    session = AuthService.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Sesión expirada o no autenticado")
    return {"status": "success", "user": session}

@app.post("/api/auth/logout")
async def auth_logout(payload: Dict[str, Any] = Body(...)):
    """Destroys active session token."""
    token = payload.get("token", "")
    AuthService.destroy_session(token)
    return {"status": "success", "message": "Sesión cerrada correctamente"}

@app.get("/api/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """Lists all registered system users (for Admin/Supervisor)."""
    return await Repository.get_all_users(db)

@app.post("/api/users")
async def create_user(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Creates a new user account with role and assigned stage."""
    username = payload.get("username", "").strip().lower()
    password = payload.get("password", "")
    full_name = payload.get("full_name", "").strip()
    email = payload.get("email", "").strip().lower()
    role = payload.get("role", "OPERADOR").upper()
    assigned_stage = payload.get("assigned_stage", "TODAS")
    phone = payload.get("phone", "")

    if not username or not password or not full_name or not email:
        raise HTTPException(status_code=400, detail="Todos los campos obligatorios deben ser diligenciados")

    existing = await Repository.get_user_by_username(db, username)
    if existing:
        raise HTTPException(status_code=400, detail=f"El nombre de usuario '{username}' ya existe")

    user = await Repository.create_user(
        db,
        username=username,
        password=password,
        full_name=full_name,
        email=email,
        role=role,
        assigned_stage=assigned_stage,
        phone=phone
    )
    return {
        "status": "success",
        "message": "Usuario creado exitosamente",
        "user_id": user.id,
        "username": user.username
    }

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Updates user information or password."""
    updated = await Repository.update_user(db, user_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"status": "success", "message": "Usuario actualizado exitosamente"}

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Deletes a user account."""
    success = await Repository.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"status": "success", "message": "Usuario eliminado exitosamente"}



# Mount Static Frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    app.mount("/correos/static", StaticFiles(directory=frontend_dir), name="correos_static")

    @app.get("/")
    @app.get("/correos")
    @app.get("/correos/")
    async def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
