import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.models import CaseTicket, WorkflowDefinition, EmailMessage
from database.repository import Repository
from backend.email_client.base import BaseEmailClient

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Multi-stage sequential routing & case tracking engine.
    Orchestrates:
    - Central inbox analysis and folder categorization.
    - Dispatching to sequential actors (Step 1 -> Step 2 -> ... -> Step N).
    - Immediate problem detection and alerting to Supervisor (Principal User).
    - Final completion notification back to Supervisor.
    - Complete traceability and bottleneck tracking.
    """

    def __init__(self, email_client: BaseEmailClient):
        self.email_client = email_client

    async def handle_incoming_email(
        self,
        db: AsyncSession,
        email_record: EmailMessage,
        analysis: Dict[str, Any]
    ) -> Optional[CaseTicket]:
        """
        Evaluates whether an incoming email should advance an existing case
        or trigger a new multi-stage workflow.
        """
        subject = email_record.subject or ""
        body = email_record.body or ""
        thread_id = email_record.thread_id or email_record.id

        # 1. Check if email belongs to an existing case
        case_code_match = re.search(r'\[(CASO-\d{4}-\d+)\]', f"{subject} {body}", re.IGNORECASE)
        case_code = case_code_match.group(1).upper() if case_code_match else ""

        existing_case = await Repository.get_case_by_thread_or_code(db, thread_id=thread_id, case_code=case_code)

        if existing_case:
            logger.info(f"[WorkflowEngine] Email matched existing case {existing_case.case_code} (Status: {existing_case.status})")
            return await self._process_case_transition(db, existing_case, email_record, analysis)

        # 2. Check if email initiates a new workflow
        wf_topic = analysis.get("workflow_topic", "")
        wf_match = await Repository.match_workflow(db, topic=wf_topic, text=f"{subject} {body}")

        if wf_match:
            logger.info(f"[WorkflowEngine] Email initiates new workflow: '{wf_match.name}'")
            return await self._create_and_dispatch_new_case(db, wf_match, email_record, analysis)

        # No workflow matched
        return None

    async def _create_and_dispatch_new_case(
        self,
        db: AsyncSession,
        workflow: WorkflowDefinition,
        email_record: EmailMessage,
        analysis: Dict[str, Any]
    ) -> CaseTicket:
        """Creates a new case, moves email to target folder, and forwards to User 1."""
        steps = json.loads(workflow.steps or "[]")
        step1 = steps[0] if steps else {
            "step_number": 1,
            "name": "Gestor Inicial",
            "assigned_email": workflow.supervisor_email or settings.SUPERVISOR_EMAIL,
            "action_required": "Revisión inicial del caso"
        }

        patient_name = analysis.get("patient_name") or "Paciente"
        patient_id_doc = analysis.get("patient_id_doc") or ""

        target_folder = workflow.target_folder or analysis.get("target_folder", "General")
        supervisor_email = workflow.supervisor_email or settings.SUPERVISOR_EMAIL

        # Organize into folder at email server level
        try:
            await self.email_client.move_to_folder(email_record.id, target_folder)
            logger.info(f"[WorkflowEngine] Email {email_record.id} moved to folder '{target_folder}'")
        except Exception as e:
            logger.warning(f"[WorkflowEngine] Could not move email to folder '{target_folder}': {e}")

        # Create ticket in DB
        case = await Repository.create_case(db, {
            "workflow_id": workflow.id,
            "thread_id": email_record.thread_id,
            "initial_email_id": email_record.id,
            "patient_name": patient_name,
            "patient_id_doc": patient_id_doc,
            "subject": email_record.subject,
            "summary": analysis.get("intent_summary") or email_record.snippet,
            "target_folder": target_folder,
            "current_step_number": step1["step_number"],
            "current_step_name": step1["name"],
            "current_assigned_email": step1["assigned_email"],
            "supervisor_email": supervisor_email
        })

        # Forward email to User 1
        forward_subject = f"[{case.case_code}] Paso 1: {step1['name']} - Paciente: {patient_name}"
        forward_body = (
            f"Estimado/a equipo de {step1['name']},\n\n"
            f"Se ha recibido una nueva solicitud para el flujo '{workflow.name}'.\n\n"
            f"DETALLES DEL CASO:\n"
            f"- Código de Caso: {case.case_code}\n"
            f"- Paciente: {patient_name}\n"
            f"- Documento: {patient_id_doc or 'Ver adjuntos'}\n"
            f"- Carpeta asignada: 📁 {target_folder}\n"
            f"- Acción requerida: {step1.get('action_required', 'Gestión del caso')}\n\n"
            f"--- MENSAJE ORIGINAL ---\n"
            f"De: {email_record.sender_name} <{email_record.sender_email}>\n"
            f"Asunto: {email_record.subject}\n\n"
            f"{email_record.body}\n\n"
            f"Para aprobar o avanzar responda a este correo indicando 'Aprobado'. "
            f"Si detecta algún problema, responda detallando la novedad para alertar a la coordinación ({supervisor_email})."
        )

        try:
            await self.email_client.forward_email(
                original_email_id=email_record.id,
                to_email=step1["assigned_email"],
                subject=forward_subject,
                body=forward_body
            )
            await Repository.log_case_event(
                db,
                case_id=case.id,
                step_number=1,
                step_name=step1["name"],
                actor_email=step1["assigned_email"],
                action="REENVIADO_ETAPA",
                comments=f"Reenviado al usuario del Paso 1: {step1['assigned_email']}"
            )
        except Exception as e:
            logger.error(f"[WorkflowEngine] Failed to forward case {case.case_code} to {step1['assigned_email']}: {e}")

        return case

    async def _process_case_transition(
        self,
        db: AsyncSession,
        case: CaseTicket,
        email_record: EmailMessage,
        analysis: Dict[str, Any]
    ) -> CaseTicket:
        """Processes response from an actor: either reporting a problem or advancing the step."""
        workflow_action = analysis.get("workflow_action", "APROBADO_AVANZAR")
        sender_email = email_record.sender_email

        if workflow_action == "PROBLEMA_REPORTADO":
            reason = analysis.get("problem_reason") or "Problema o retraso reportado por el gestor"
            bottleneck_category = analysis.get("bottleneck_category") or "Rechazo / Documentación"
            return await self.report_problem(db, case, sender_email, reason, bottleneck_category)
        else:
            comments = analysis.get("intent_summary") or "Paso completado conforme"
            return await self.advance_step(db, case, sender_email, comments)

    async def advance_step(
        self,
        db: AsyncSession,
        case: CaseTicket,
        actor_email: str,
        comments: str = ""
    ) -> CaseTicket:
        """
        Advances the case to the next user in the chain.
        If last step, marks as COMPLETADO and returns final dossier to the Principal User.
        """
        workflow = case.workflow_rel
        steps = json.loads(workflow.steps or "[]") if workflow else []

        current_idx = -1
        for i, s in enumerate(steps):
            if s.get("step_number") == case.current_step_number:
                current_idx = i
                break

        has_next = (current_idx != -1 and current_idx + 1 < len(steps))

        if has_next:
            next_step = steps[current_idx + 1]
            old_step_name = case.current_step_name

            case.current_step_number = next_step["step_number"]
            case.current_step_name = next_step["name"]
            case.current_assigned_email = next_step["assigned_email"]
            case.status = "EN_PROCESO"
            case.total_transitions += 1
            case.updated_at = datetime.utcnow()

            await Repository.log_case_event(
                db,
                case_id=case.id,
                step_number=case.current_step_number - 1,
                step_name=old_step_name,
                actor_email=actor_email,
                action="GESTION_APROBADA",
                comments=comments or f"Aprobado por {actor_email}. Avanza a {next_step['name']}"
            )

            # Forward to next actor
            forward_subject = f"[{case.case_code}] Paso {case.current_step_number}: {next_step['name']} - Paciente: {case.patient_name}"
            forward_body = (
                f"Estimado/a equipo de {next_step['name']},\n\n"
                f"El caso {case.case_code} del paciente {case.patient_name} ha sido aprobado en la etapa anterior ({old_step_name}) "
                f"y requiere ahora su diligencia.\n\n"
                f"DETALLES:\n"
                f"- Código de Caso: {case.case_code}\n"
                f"- Paciente: {case.patient_name} ({case.patient_id_doc})\n"
                f"- Carpeta: 📁 {case.target_folder}\n"
                f"- Acción requerida: {next_step.get('action_required', 'Gestión')}\n"
                f"- Observaciones previas: {comments}\n\n"
                f"Por favor responder confirmando el resultado o indicando novedades para soporte."
            )

            try:
                await self.email_client.send_email(
                    to_email=next_step["assigned_email"],
                    subject=forward_subject,
                    body=forward_body,
                    thread_id=case.thread_id
                )
                await Repository.log_case_event(
                    db,
                    case_id=case.id,
                    step_number=case.current_step_number,
                    step_name=next_step["name"],
                    actor_email=next_step["assigned_email"],
                    action="REENVIADO_ETAPA",
                    comments=f"Notificación enviada a {next_step['assigned_email']}"
                )
            except Exception as e:
                logger.error(f"[WorkflowEngine] Error dispatching to next step for {case.case_code}: {e}")

        else:
            # Final Step Reached -> Returns to Principal User (Supervisor)
            case.status = "COMPLETADO"
            case.completed_at = datetime.utcnow()
            case.total_transitions += 1
            case.updated_at = datetime.utcnow()

            await Repository.log_case_event(
                db,
                case_id=case.id,
                step_number=case.current_step_number,
                step_name=case.current_step_name,
                actor_email=actor_email,
                action="COMPLETADO_FINAL",
                comments=f"Flujo concluido exitosamente por {actor_email}. Dossier devuelto al Usuario Principal."
            )

            # Send final completion dossier to Principal User (Supervisor)
            sup_subject = f"[PROCESO COMPLETADO] {case.case_code}: Finalizado Exitosamente - Paciente: {case.patient_name}"
            sup_body = (
                f"Estimado/a Coordinador/a Principal ({case.supervisor_email}),\n\n"
                f"Le informamos que el proceso para el paciente {case.patient_name} ({case.patient_id_doc}) "
                f"ha concluido TODAS sus etapas satisfactoriamente.\n\n"
                f"RESUMEN DE TRAZABILIDAD:\n"
                f"- Código de Caso: {case.case_code}\n"
                f"- Paciente: {case.patient_name}\n"
                f"- Carpeta: 📁 {case.target_folder}\n"
                f"- Transiciones realizadas: {case.total_transitions}\n"
                f"- Retornos/Rechazos superados: {case.total_returns}\n"
                f"- Estado final: ✅ COMPLETADO\n"
                f"- Fecha de cierre: {case.completed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"El caso queda archivado en el sistema para auditoría y estadísticas."
            )

            try:
                await self.email_client.send_email(
                    to_email=case.supervisor_email or settings.SUPERVISOR_EMAIL,
                    subject=sup_subject,
                    body=sup_body,
                    thread_id=case.thread_id
                )
            except Exception as e:
                logger.error(f"[WorkflowEngine] Error sending final dossier to supervisor for {case.case_code}: {e}")

        await db.commit()
        await db.refresh(case)
        return case

    async def report_problem(
        self,
        db: AsyncSession,
        case: CaseTicket,
        actor_email: str,
        reason: str,
        bottleneck_category: str = ""
    ) -> CaseTicket:
        """
        Handles problem or rejection reported by an actor.
        Immediately alerts the Principal User (Supervisor) with the exact issue.
        Increments return and bottleneck counters.
        """
        case.status = "DETENIDO_PROBLEMA"
        case.total_returns += 1
        case.last_problem_reported = reason
        case.bottleneck_reason = bottleneck_category or "Rechazo de solicitud"
        case.updated_at = datetime.utcnow()

        # Log problem event
        await Repository.log_case_event(
            db,
            case_id=case.id,
            step_number=case.current_step_number,
            step_name=case.current_step_name,
            actor_email=actor_email,
            action="PROBLEMA_REPORTADO",
            comments=f"Novedad reportada en {case.current_step_name}: {reason}",
            problem_details=reason
        )

        # Send immediate alert to Supervisor (Principal User)
        supervisor_email = case.supervisor_email or settings.SUPERVISOR_EMAIL
        alert_subject = f"[ALERTA DETENCIÓN - REQUERIDO CORRECTIVO] {case.case_code}: Novedad en {case.current_step_name} - Paciente: {case.patient_name}"
        alert_body = (
            f"URGENTE: Notificación de Detención para el Usuario Principal ({supervisor_email})\n\n"
            f"El avance del paciente {case.patient_name} ({case.patient_id_doc}) se encuentra DETENIDO debido a una novedad.\n\n"
            f"DETALLE DE LA NOVEDAD:\n"
            f"- Código de Caso: {case.case_code}\n"
            f"- Etapa actual: {case.current_step_name} (Responsable: {actor_email})\n"
            f"- Tipo de Cuello de Botella: {case.bottleneck_reason}\n"
            f"- Causa exacta reportada: {reason}\n"
            f"- Total de devoluciones/retrasos acumulados en este caso: {case.total_returns}\n\n"
            f"ACCIÓN REQUERIDA:\n"
            f"Por favor tomar el correctivo correspondiente o gestionar la subsanación para destrabar el ingreso del paciente.\n\n"
            f"Puede gestionar el desbloqueo o reasignación desde el panel de control de la plataforma."
        )

        try:
            await self.email_client.send_email(
                to_email=supervisor_email,
                subject=alert_subject,
                body=alert_body,
                thread_id=case.thread_id
            )
            await Repository.log_case_event(
                db,
                case_id=case.id,
                step_number=case.current_step_number,
                step_name=case.current_step_name,
                actor_email=supervisor_email,
                action="ALERTA_SUPERVISOR_ENVIADA",
                comments=f"Alerta inmediata enviada al supervisor principal ({supervisor_email})"
            )
        except Exception as e:
            logger.error(f"[WorkflowEngine] Failed to send supervisor alert for {case.case_code}: {e}")

        await db.commit()
        await db.refresh(case)
        return case
