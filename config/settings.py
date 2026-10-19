import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    OPERATIONAL_MODE: str = "automatic"
    POLL_INTERVAL_MINUTES: int = 2
    
    AI_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"
    
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    EMAIL_PROVIDER: str = "mock"
    
    GMAIL_CREDENTIALS_FILE: str = str(BASE_DIR / "config" / "credentials.json")
    GMAIL_TOKEN_FILE: str = str(BASE_DIR / "config" / "token.json")
    
    IMAP_SERVER: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    
    COMPANY_NAME: str = "IPS Atención Domiciliaria"
    AGENT_NAME: str = "Asistente Virtual IA"
    AGENT_ROLE: str = "Gestor de Atención y Radicación Domiciliaria"
    SUPERVISOR_EMAIL: str = "coordinacion@clinica.com"
    COMPANY_PHONE: str = "+57 300 123 4567"
    COMPANY_HOURS: str = "Lunes a Viernes de 8:00 AM a 5:00 PM"
    COMPANY_WEBSITE: str = "https://ipsdomiciliaria.com"
    
    # Firma digital personalizada para correos salientes
    SIGNATURE_NAME: str = "Coordinación Médica Domiciliaria"
    SIGNATURE_ROLE: str = "Gestión de Pacientes & Admisiones"
    SIGNATURE_INSTITUTION: str = "IPS Atención Domiciliaria"
    SIGNATURE_PHONE: str = "+57 300 123 4567"
    SIGNATURE_REGISTRATION: str = "R.M. No. 54321-Antioquia"
    SIGNATURE_DISCLAIMER: str = "CONFIDENCIALIDAD: La información contenida en este correo está sujeta a reserva médica y secreto profesional (Ley 1581 de Protección de Datos Personales)."
    REPLY_SIGNATURE: str = "Atentamente,\nCoordinación Médica Domiciliaria\nIPS Atención Domiciliaria\nPBX: +57 300 123 4567"
    
    AUTO_REPLY_CONFIDENCE_THRESHOLD: float = 95.0
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD: float = 85.0
    
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/database/email_agent.db"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
