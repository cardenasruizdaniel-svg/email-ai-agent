from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Sender(Base):
    __tablename__ = "senders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, default="")
    company = Column(String, default="", index=True)
    frequent_topics = Column(Text, default="[]")  # JSON string list
    last_interaction = Column(DateTime, default=datetime.utcnow)
    priority = Column(String, default="MEDIA")    # CRITICA, ALTA, MEDIA, BAJA
    status = Column(String, default="Activo")     # Activo, Pendiente, Inactivo
    total_emails = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    emails = relationship("EmailMessage", back_populates="sender_rel")

class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(String, primary_key=True)  # Message ID from Gmail/IMAP/Mock
    thread_id = Column(String, index=True, nullable=False)
    sender_email = Column(String, ForeignKey("senders.email"), index=True, nullable=False)
    sender_name = Column(String, default="")
    company = Column(String, default="", index=True)
    subject = Column(Text, default="")
    body = Column(Text, default="")
    snippet = Column(Text, default="")
    date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Classification & AI Results
    category = Column(String, default="INFORMACION", index=True) 
    # Categories: INFORMACION, RESPUESTA_SIMPLE, SOLICITUD, URGENTE, REVISION_HUMANA, SPAM
    subcategories = Column(Text, default="[]")
    tags = Column(Text, default="[]")              # Standardized tags list JSON
    priority = Column(String, default="MEDIA")    # CRITICA, ALTA, MEDIA, BAJA
    confidence = Column(Float, default=0.0)       # 0.0 to 100.0
    risk_level = Column(String, default="BAJO")    # BAJO, MEDIO, ALTO
    risk_reasons = Column(Text, default="[]")
    
    # Decision flags
    requires_human_review = Column(Boolean, default=False, index=True)
    can_auto_reply = Column(Boolean, default=False)
    status = Column(String, default="PENDIENTE", index=True) 
    # Statuses: PENDIENTE, RESPONDIDO_IA, REVISADO_HUMANO, IGNORADO
    
    # AI Text Output
    intent_summary = Column(Text, default="")
    draft_reply = Column(Text, default="")
    sent_reply = Column(Text, default="")
    attachments_info = Column(Text, default="[]")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sender_rel = relationship("Sender", back_populates="emails")

class CustomRule(Base):
    __tablename__ = "custom_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    condition_type = Column(String, nullable=False) 
    # Types: SENDER_EMAIL, SENDER_DOMAIN, SUBJECT_CONTAINS, BODY_CONTAINS, HAS_ATTACHMENT
    condition_value = Column(Text, nullable=False)
    action_priority = Column(String, default="")
    action_category = Column(String, default="")
    action_label = Column(String, default="")
    action_allow_autoreply = Column(Boolean, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    email_id = Column(String, default="", index=True)
    sender_email = Column(String, default="")
    subject = Column(Text, default="")
    category = Column(String, default="")
    confidence = Column(Float, default=0.0)
    action_taken = Column(String, default="") 
    # e.g., "CLASIFICADO", "ETIQUETADO", "RESPONDIDO_AUTOMATICO", "ENVIADO_REVISION_HUMANA"
    details = Column(Text, default="")
    status = Column(String, default="SUCCESS") # SUCCESS, WARNING, ERROR

class UserCorrection(Base):
    __tablename__ = "user_corrections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, nullable=False)
    original_category = Column(String, default="")
    corrected_category = Column(String, default="")
    original_tags = Column(Text, default="[]")
    corrected_tags = Column(Text, default="[]")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, default="")
    trigger_keywords = Column(Text, default="[]") # JSON list of strings (e.g. ["ingreso", "paciente", "cama"])
    trigger_category = Column(String, default="SOLICITUD")
    target_folder = Column(String, default="General") # e.g. "Ingreso Pacientes", "Autorizaciones"
    supervisor_email = Column(String, default="") # Email to notify on problems & completion
    steps = Column(Text, default="[]") # JSON list of dicts: [{"step_number": 1, "name": "Admisiones", "assigned_email": "adm@clinica.com", "action_required": "Verificar"}, ...]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cases = relationship("CaseTicket", back_populates="workflow_rel")

class CaseTicket(Base):
    __tablename__ = "case_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_code = Column(String, unique=True, index=True, nullable=False) # e.g. "CASO-2026-0001"
    workflow_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=True)
    thread_id = Column(String, index=True, nullable=False)
    initial_email_id = Column(String, ForeignKey("email_messages.id"), nullable=True)
    patient_name = Column(String, default="")
    patient_id_doc = Column(String, default="")
    subject = Column(Text, default="")
    summary = Column(Text, default="")
    target_folder = Column(String, default="General")
    
    # State in workflow
    current_step_number = Column(Integer, default=1)
    current_step_name = Column(String, default="")
    current_assigned_email = Column(String, default="", index=True)
    supervisor_email = Column(String, default="")
    status = Column(String, default="EN_PROCESO", index=True) 
    # EN_PROCESO, EN_APROBACION, DETENIDO_PROBLEMA, DEVUELTO, COMPLETADO
    
    # Metrics
    total_transitions = Column(Integer, default=1) # Times advanced across steps
    total_returns = Column(Integer, default=0)     # Times rejected/returned with problems
    last_problem_reported = Column(Text, default="")
    bottleneck_reason = Column(Text, default="")   # Categorized reason (e.g. "Falta de documento", "Sin disponibilidad")
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    workflow_rel = relationship("WorkflowDefinition", back_populates="cases")
    history_logs = relationship("CaseHistoryLog", back_populates="case_rel", cascade="all, delete-orphan")

class CaseHistoryLog(Base):
    __tablename__ = "case_history_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("case_tickets.id"), nullable=False, index=True)
    step_number = Column(Integer, default=1)
    step_name = Column(String, default="")
    actor_email = Column(String, default="")
    action = Column(String, nullable=False) 
    # INICIADO, REENVIADO_ETAPA, GESTION_APROBADA, PROBLEMA_REPORTADO, ALERTA_SUPERVISOR_ENVIADA, COMPLETADO_FINAL
    comments = Column(Text, default="")
    problem_details = Column(Text, default="")
    duration_hours = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    case_rel = relationship("CaseTicket", back_populates="history_logs")
