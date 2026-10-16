import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from .models import (
    Sender, EmailMessage, CustomRule, ActivityLog, UserCorrection,
    WorkflowDefinition, CaseTicket, CaseHistoryLog, UserAccount
)

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

    @staticmethod
    async def get_or_create_default_workflows(db: AsyncSession) -> List[WorkflowDefinition]:
        """Ensures default workflows exist (e.g., Ingreso de Pacientes, Autorizaciones)."""
        stmt = select(WorkflowDefinition)
        result = await db.execute(stmt)
        existing = list(result.scalars().all())
        if existing:
            return existing

        default_supervisor = getattr(settings, "SUPERVISOR_EMAIL", "coordinacion@clinica.com")
        
        # 1. Ingreso de Pacientes
        wf_ingreso = WorkflowDefinition(
            name="Ingreso de Pacientes",
            description="Flujo secuencial de admisión: Admisiones -> Auditoría Médica -> Asignación de Camas",
            trigger_keywords=json.dumps(["ingreso", "paciente", "cama", "admision", "admisión", "hospitalizacion", "hospitalización"]),
            trigger_category="SOLICITUD",
            target_folder="Ingreso Pacientes",
            supervisor_email=default_supervisor,
            steps=json.dumps([
                {
                    "step_number": 1,
                    "name": "Admisiones",
                    "assigned_email": "admisiones@clinica.com",
                    "action_required": "Verificar orden de hospitalización y documento del paciente"
                },
                {
                    "step_number": 2,
                    "name": "Auditoría Médica",
                    "assigned_email": "auditoria@clinica.com",
                    "action_required": "Validar pertinencia clínica, cobertura y autorizaciones"
                },
                {
                    "step_number": 3,
                    "name": "Asignación de Camas",
                    "assigned_email": "camas@clinica.com",
                    "action_required": "Asignar pabellón, habitación y cama disponible"
                }
            ]),
            is_active=True
        )

        # 2. Autorizaciones Médicas
        wf_autorizaciones = WorkflowDefinition(
            name="Autorizaciones Médicas",
            description="Flujo de gestión y radicación de autorizaciones médicas con EPS",
            trigger_keywords=json.dumps(["autorizacion", "autorización", "orden medica", "orden médica", "eps", "cobertura"]),
            trigger_category="SOLICITUD",
            target_folder="Autorizaciones",
            supervisor_email=default_supervisor,
            steps=json.dumps([
                {
                    "step_number": 1,
                    "name": "Radicación EPS",
                    "assigned_email": "radicacion@clinica.com",
                    "action_required": "Radicar orden ante la EPS y solicitar número de autorización"
                },
                {
                    "step_number": 2,
                    "name": "Facturación y Convenios",
                    "assigned_email": "facturacion@clinica.com",
                    "action_required": "Verificar tarifa contratada y confirmar aval de atención"
                }
            ]),
            is_active=True
        )

        db.add(wf_ingreso)
        db.add(wf_autorizaciones)
        await db.commit()
        await db.refresh(wf_ingreso)
        await db.refresh(wf_autorizaciones)
        return [wf_ingreso, wf_autorizaciones]

    @staticmethod
    async def match_workflow(db: AsyncSession, topic: str = "", text: str = "") -> Optional[WorkflowDefinition]:
        """Matches an incoming email to a workflow definition by topic or trigger keywords."""
        workflows = await Repository.get_or_create_default_workflows(db)
        topic_lower = topic.strip().lower()
        text_lower = text.lower()

        # Direct name/topic match
        for wf in workflows:
            if not wf.is_active:
                continue
            if topic_lower and (topic_lower in wf.name.lower() or wf.name.lower() in topic_lower):
                return wf

        # Keyword match
        for wf in workflows:
            if not wf.is_active:
                continue
            keywords = json.loads(wf.trigger_keywords or "[]")
            if any(kw.lower() in text_lower for kw in keywords):
                return wf

        return None

    @staticmethod
    async def get_case_by_thread_or_code(db: AsyncSession, thread_id: str = "", case_code: str = "") -> Optional[CaseTicket]:
        """Finds an existing case by thread ID or case code."""
        if case_code:
            stmt = select(CaseTicket).options(selectinload(CaseTicket.workflow_rel)).where(CaseTicket.case_code == case_code)
            res = await db.execute(stmt)
            case = res.scalar_one_or_none()
            if case:
                return case

        if thread_id:
            stmt = select(CaseTicket).options(selectinload(CaseTicket.workflow_rel)).where(CaseTicket.thread_id == thread_id)
            res = await db.execute(stmt)
            return res.scalar_one_or_none()
        return None

    @staticmethod
    async def create_case(db: AsyncSession, case_data: Dict[str, Any]) -> CaseTicket:
        """Creates a new case ticket and logs the initial event."""
        year = datetime.utcnow().year
        stmt_count = select(func.count(CaseTicket.id))
        total_cases = (await db.execute(stmt_count)).scalar() or 0
        case_code = f"CASO-{year}-{total_cases + 1:04d}"

        case = CaseTicket(
            case_code=case_code,
            workflow_id=case_data.get("workflow_id"),
            thread_id=case_data.get("thread_id", ""),
            initial_email_id=case_data.get("initial_email_id"),
            patient_name=case_data.get("patient_name", ""),
            patient_id_doc=case_data.get("patient_id_doc", ""),
            patient_address=case_data.get("patient_address", ""),
            city_zone=case_data.get("city_zone", ""),
            eps_name=case_data.get("eps_name", ""),
            service_requested=case_data.get("service_requested", ""),
            subject=case_data.get("subject", ""),
            summary=case_data.get("summary", ""),
            target_folder=case_data.get("target_folder", "General"),
            current_step_number=case_data.get("current_step_number", 1),
            current_step_name=case_data.get("current_step_name", ""),
            current_assigned_email=case_data.get("current_assigned_email", ""),
            supervisor_email=case_data.get("supervisor_email", ""),
            status="EN_PROCESO",
            total_transitions=1,
            total_returns=0
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)

        # Add initial history log
        log = CaseHistoryLog(
            case_id=case.id,
            step_number=case.current_step_number,
            step_name=case.current_step_name,
            actor_email=case.current_assigned_email,
            action="INICIADO",
            comments=f"Caso {case.case_code} iniciado y remitido a {case.current_step_name} ({case.current_assigned_email})"
        )
        db.add(log)
        await db.commit()
        return case

    @staticmethod
    async def log_case_event(
        db: AsyncSession,
        case_id: int,
        step_number: int,
        step_name: str,
        actor_email: str,
        action: str,
        comments: str = "",
        problem_details: str = "",
        duration_hours: float = 0.0
    ) -> CaseHistoryLog:
        """Adds a milestone or status log to a case."""
        log = CaseHistoryLog(
            case_id=case_id,
            step_number=step_number,
            step_name=step_name,
            actor_email=actor_email,
            action=action,
            comments=comments,
            problem_details=problem_details,
            duration_hours=duration_hours,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        await db.commit()
        return log

    @staticmethod
    async def get_cases(
        db: AsyncSession,
        status: Optional[str] = None,
        folder: Optional[str] = None,
        assigned_email: Optional[str] = None,
        stage: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lists cases with metadata and summary of logs, supporting operator filters."""
        stmt = select(CaseTicket).order_by(CaseTicket.updated_at.desc())
        if status:
            stmt = stmt.where(CaseTicket.status == status)
        if folder:
            stmt = stmt.where(CaseTicket.target_folder == folder)
        if assigned_email:
            stmt = stmt.where(CaseTicket.current_assigned_email == assigned_email)
        if stage and stage != "TODAS":
            stmt = stmt.where(CaseTicket.current_step_name.ilike(f"%{stage}%"))
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        cases = list(result.scalars().all())

        case_list = []
        for c in cases:
            case_list.append({
                "id": c.id,
                "case_code": c.case_code,
                "workflow_id": c.workflow_id,
                "thread_id": c.thread_id,
                "patient_name": c.patient_name,
                "patient_id_doc": c.patient_id_doc,
                "patient_address": c.patient_address or "",
                "city_zone": c.city_zone or "",
                "eps_name": c.eps_name or "",
                "service_requested": c.service_requested or "",
                "subject": c.subject,
                "summary": c.summary,
                "target_folder": c.target_folder,
                "current_step_number": c.current_step_number,
                "current_step_name": c.current_step_name,
                "current_assigned_email": c.current_assigned_email,
                "supervisor_email": c.supervisor_email,
                "status": c.status,
                "total_transitions": c.total_transitions,
                "total_returns": c.total_returns,
                "last_problem_reported": c.last_problem_reported,
                "bottleneck_reason": c.bottleneck_reason,
                "resolution_notes": c.resolution_notes or "",
                "resolved_by": c.resolved_by or "",
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            })
        return case_list

    @staticmethod
    async def get_case_details(db: AsyncSession, case_id: int) -> Optional[Dict[str, Any]]:
        """Gets full case details including chronological history logs."""
        stmt = select(CaseTicket).where(CaseTicket.id == case_id)
        res = await db.execute(stmt)
        case = res.scalar_one_or_none()
        if not case:
            return None

        stmt_logs = select(CaseHistoryLog).where(CaseHistoryLog.case_id == case_id).order_by(CaseHistoryLog.timestamp.asc())
        logs_res = await db.execute(stmt_logs)
        logs = list(logs_res.scalars().all())

        return {
            "id": case.id,
            "case_code": case.case_code,
            "workflow_id": case.workflow_id,
            "thread_id": case.thread_id,
            "patient_name": case.patient_name,
            "patient_id_doc": case.patient_id_doc,
            "patient_address": case.patient_address or "",
            "city_zone": case.city_zone or "",
            "eps_name": case.eps_name or "",
            "service_requested": case.service_requested or "",
            "subject": case.subject,
            "summary": case.summary,
            "target_folder": case.target_folder,
            "current_step_number": case.current_step_number,
            "current_step_name": case.current_step_name,
            "current_assigned_email": case.current_assigned_email,
            "supervisor_email": case.supervisor_email,
            "status": case.status,
            "total_transitions": case.total_transitions,
            "total_returns": case.total_returns,
            "last_problem_reported": case.last_problem_reported,
            "bottleneck_reason": case.bottleneck_reason,
            "resolution_notes": case.resolution_notes or "",
            "resolved_by": case.resolved_by or "",
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "updated_at": case.updated_at.isoformat() if case.updated_at else None,
            "completed_at": case.completed_at.isoformat() if case.completed_at else None,
            "logs": [
                {
                    "id": l.id,
                    "step_number": l.step_number,
                    "step_name": l.step_name,
                    "actor_email": l.actor_email,
                    "action": l.action,
                    "comments": l.comments,
                    "problem_details": l.problem_details,
                    "duration_hours": l.duration_hours,
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None
                }
                for l in logs
            ]
        }

    @staticmethod
    async def get_bottleneck_report(db: AsyncSession) -> Dict[str, Any]:
        """Generates comprehensive bottleneck metrics, stoppages, and return statistics."""
        total_stmt = select(func.count(CaseTicket.id))
        total_cases = (await db.execute(total_stmt)).scalar() or 0

        stopped_stmt = select(func.count(CaseTicket.id)).where(CaseTicket.status == "DETENIDO_PROBLEMA")
        stopped_cases = (await db.execute(stopped_stmt)).scalar() or 0

        completed_stmt = select(func.count(CaseTicket.id)).where(CaseTicket.status == "COMPLETADO")
        completed_cases = (await db.execute(completed_stmt)).scalar() or 0

        returns_stmt = select(func.sum(CaseTicket.total_returns))
        total_returns = (await db.execute(returns_stmt)).scalar() or 0

        transitions_stmt = select(func.sum(CaseTicket.total_transitions))
        total_transitions = (await db.execute(transitions_stmt)).scalar() or 0

        group_stmt = select(CaseTicket.bottleneck_reason, func.count(CaseTicket.id))\
            .where(CaseTicket.bottleneck_reason != "")\
            .group_by(CaseTicket.bottleneck_reason)
        group_res = await db.execute(group_stmt)
        bottlenecks_by_reason = [{"reason": row[0], "count": row[1]} for row in group_res.all()]

        problem_cases_stmt = select(CaseTicket)\
            .where((CaseTicket.status == "DETENIDO_PROBLEMA") | (CaseTicket.total_returns > 0))\
            .order_by(CaseTicket.updated_at.desc()).limit(20)
        p_cases = (await db.execute(problem_cases_stmt)).scalars().all()

        delayed_cases = [
            {
                "case_code": c.case_code,
                "patient_name": c.patient_name,
                "current_step_name": c.current_step_name,
                "current_assigned_email": c.current_assigned_email,
                "status": c.status,
                "total_returns": c.total_returns,
                "bottleneck_reason": c.bottleneck_reason,
                "last_problem_reported": c.last_problem_reported,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in p_cases
        ]

        return {
            "total_cases": total_cases,
            "stopped_cases": stopped_cases,
            "completed_cases": completed_cases,
            "in_progress_cases": max(0, total_cases - completed_cases - stopped_cases),
            "total_returns": total_returns,
            "total_transitions": total_transitions,
            "bottlenecks_by_reason": bottlenecks_by_reason,
            "delayed_cases": delayed_cases
        }

    # ================= USER ACCOUNT & RESOLUTION MANAGEMENT =================
    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[UserAccount]:
        stmt = select(UserAccount).where(UserAccount.username == username.strip().lower())
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserAccount]:
        stmt = select(UserAccount).where(UserAccount.id == user_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_all_users(db: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(UserAccount).order_by(UserAccount.id.asc())
        res = await db.execute(stmt)
        users = list(res.scalars().all())
        return [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "assigned_stage": u.assigned_stage,
                "phone": u.phone,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None
            }
            for u in users
        ]

    @staticmethod
    async def create_user(
        db: AsyncSession,
        username: str,
        password: str,
        full_name: str,
        email: str,
        role: str = "OPERADOR",
        assigned_stage: str = "TODAS",
        phone: str = ""
    ) -> UserAccount:
        from backend.services.auth import AuthService
        pwd_hash, salt = AuthService.hash_password(password)
        user = UserAccount(
            username=username.strip().lower(),
            password_hash=pwd_hash,
            salt=salt,
            full_name=full_name.strip(),
            email=email.strip().lower(),
            role=role.upper(),
            assigned_stage=assigned_stage,
            phone=phone,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        user_data: Dict[str, Any]
    ) -> Optional[UserAccount]:
        from backend.services.auth import AuthService
        user = await Repository.get_user_by_id(db, user_id)
        if not user:
            return None
        if "full_name" in user_data:
            user.full_name = user_data["full_name"]
        if "email" in user_data:
            user.email = user_data["email"].strip().lower()
        if "role" in user_data:
            user.role = user_data["role"].upper()
        if "assigned_stage" in user_data:
            user.assigned_stage = user_data["assigned_stage"]
        if "phone" in user_data:
            user.phone = user_data["phone"]
        if "is_active" in user_data:
            user.is_active = bool(user_data["is_active"])
        if "password" in user_data and user_data["password"]:
            pwd_hash, salt = AuthService.hash_password(user_data["password"])
            user.password_hash = pwd_hash
            user.salt = salt
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        user = await Repository.get_user_by_id(db, user_id)
        if not user:
            return False
        await db.delete(user)
        await db.commit()
        return True

    @staticmethod
    async def seed_default_users(db: AsyncSession) -> None:
        """Seeds default clinical and operational users for the Home Care IPS."""
        from backend.services.auth import AuthService
        stmt = select(func.count(UserAccount.id))
        count = (await db.execute(stmt)).scalar() or 0
        if count > 0:
            return

        default_users = [
            ("admin", "admin123", "Dr. Coordinador General IPS", "coordinacion@ipsdomiciliaria.com", "ADMIN", "TODAS", "3001234567"),
            ("admisiones", "adm123", "Lic. Carlos Ruiz (Admisiones Domiciliarias)", "admisiones@ipsdomiciliaria.com", "OPERADOR", "Admisiones", "3109876543"),
            ("auditoria", "aud123", "Dra. Elena Ramos (Auditoría Médica)", "auditoria@ipsdomiciliaria.com", "OPERADOR", "Auditoría Médica", "3154567890"),
            ("logistica", "log123", "Ing. Mario Restrepo (Logística, Rutas y Equipos)", "logistica@ipsdomiciliaria.com", "OPERADOR", "Logística y Asignación de Rutas", "3206543210"),
            ("camas", "camas123", "Gestor de Asignación y Equipos Clínicos", "camas@clinica.com", "OPERADOR", "Asignación de Camas", "3112223344"),
        ]
        for uname, pwd, name, mail, role, stage, phone in default_users:
            pwd_hash, salt = AuthService.hash_password(pwd)
            u = UserAccount(
                username=uname,
                password_hash=pwd_hash,
                salt=salt,
                full_name=name,
                email=mail,
                role=role,
                assigned_stage=stage,
                phone=phone,
                is_active=True
            )
            db.add(u)
        await db.commit()
        logger.info("[Repository] Seeded default IPS Domiciliaria user accounts.")

    @staticmethod
    async def resolve_case_problem(
        db: AsyncSession,
        case_id: int,
        resolved_by: str,
        resolution_notes: str,
        resume_step_number: Optional[int] = None
    ) -> Optional[CaseTicket]:
        """
        Unblocks a stopped case.
        Administrator inputs the corrective resolution and resumes the case.
        """
        stmt = select(CaseTicket).options(selectinload(CaseTicket.workflow_rel)).where(CaseTicket.id == case_id)
        res = await db.execute(stmt)
        case = res.scalar_one_or_none()
        if not case:
            return None

        case.status = "EN_PROCESO"
        case.resolution_notes = resolution_notes
        case.resolved_by = resolved_by
        case.resolved_at = datetime.utcnow()
        case.updated_at = datetime.utcnow()
        if resume_step_number and resume_step_number > 0:
            case.current_step_number = resume_step_number

        await Repository.log_case_event(
            db,
            case_id=case.id,
            step_number=case.current_step_number,
            step_name=case.current_step_name,
            actor_email=resolved_by,
            action="NOVEDAD_RESUELTA",
            comments=f"Novedad resuelta por Supervisor ({resolved_by}): {resolution_notes}. Caso reanudado para continuar el flujo."
        )
        await db.commit()
        await db.refresh(case)
        return case

