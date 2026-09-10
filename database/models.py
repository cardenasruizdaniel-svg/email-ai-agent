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
