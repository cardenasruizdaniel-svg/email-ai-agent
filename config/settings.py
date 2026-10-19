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
    
    COMPANY_NAME: str = "HomeCare del Quindío I.P.S."
    AGENT_NAME: str = "Agente IA PADO Agudo"
    AGENT_ROLE: str = "Gestor Inteligente de Flujo Asistencial PADO"
    SUPERVISOR_EMAIL: str = "federico.cortes@homecaredelquindio.com"
    COMPANY_PHONE: str = "+57 (606) 745-0000 / 300 123 4567"
    COMPANY_HOURS: str = "Lunes a Domingo - Operación Asistencial 24/7"
    COMPANY_WEBSITE: str = "https://homecaredelquindio.com"
    
    # Firma digital personalizada para correos salientes
    SIGNATURE_NAME: str = "Dr. Federico Cortes"
    SIGNATURE_ROLE: str = "Coordinación Asistencial PADO Agudo"
    SIGNATURE_INSTITUTION: str = "HomeCare del Quindío I.P.S."
    SIGNATURE_PHONE: str = "+57 (606) 745-0000 / 300 123 4567"
    SIGNATURE_REGISTRATION: str = "R.M. No. 63001-Quindío"
    SIGNATURE_DISCLAIMER: str = "CONFIDENCIALIDAD MÉDICA: La información contenida en este correo está protegida por reserva clínica y secreto profesional (Ley 1581 de Protección de Datos Personales). Su contenido es exclusivo para la atención asistencial del paciente en HomeCare del Quindío I.P.S."
    REPLY_SIGNATURE: str = "Atentamente,\nDr. Federico Cortes\nCoordinación Asistencial PADO Agudo\nHomeCare del Quindío I.P.S.\nPBX: +57 (606) 745-0000"
    
    # Directrices de Entrenamiento y Asignación de Usuarios para la IA
    AI_TRAINING_INSTRUCTIONS: str = """DIRECTRICES INSTITUCIONALES HOMECARE DEL QUINDÍO I.P.S. - FLUJO PADO AGUDO:
1. DEPARTAMENTOS Y USUARIOS ASIGNADOS:
   - ATENCIÓN AL USUARIO (Púrpura):
     * Carolina Venencia (carolina): Recepción de solicitudes iniciales al correo principal. Da apertura al ciclo PADO. Notifica aceptación o rechazo al remitente (EPS/Clínica).
     * Franchesca Triviño (franchesca): Contacto directo con paciente/familiares, creación en software Medifolios, asignación a cuadros de aplicadores asistenciales y monitoreo de visitas.
     * Yurli (yurli): Monitoreo de aplicaciones junto con Franchesca, registro de salida del paciente en módulo de hospitalización domiciliaria.
   - DEPARTAMENTO INVENTARIOS (Verde):
     * German Giraldo (german): Verificación de medicamentos e insumos formulados (¿está contratado?). Si no, alerta a Federico Cortes. Alistamiento de insumos:
       - Si duración < 3 días: 1 catéter 22, 1 catéter 24, 2 tapones, 1 macrogotero, 1 jeringa x aplicación, 1 solución 100cc x aplicación, guantes x aplicación, isopañiles.
       - Si duración >= 3 días: alistamiento proporcional a la cantidad de días formulados. Entrega de insumos y solicitud de reintegro de sobrantes al egreso.
   - DEPARTAMENTO FACTURACIÓN (Rojo/Salmón):
     * Esteban Gacha (esteban): Verificación de afiliación a EPS y cobro/recaudo de copagos. Si no cancela copago, alerta de detención. Registro de paciente en el censo diario ante Secretaría de Salud y EPS. Verificación de autorización y facturación final.
   - DEPARTAMENTO ASISTENCIAL (Azul):
     * Dr. Hernando Vence (hernando): Valoración médica integral presencial en sitio (si el paciente es egreso de clínica/hospital) o telefónica (si es ambulatorio). Diligenciamiento de historia médica de ingreso y consentimiento informado. Emisión de nota de egreso médica (por terminación de tratamiento, abandono o reintegro a clínica).
     * Dr. Federico Cortes (federico): Coordinador asistencial PADO. Confirmación de horarios de aplicación, emisión de aceptación o rechazo técnico, y cobro de copagos en caso de extensiones de tratamiento.

2. REGLAS DE DETECCIÓN Y ASIGNACIÓN INICIAL:
   - Todo correo entrante con solicitud de ingreso domiciliario, antibiótico intravenoso o PADO debe asignarse inicialmente a Carolina Venencia en la etapa 'Atención al Usuario - Radicación Principal'.
   - Extraer con precisión: Nombre del paciente, Cédula/TI, EPS de origen, Medicamentos e Insumos formulados, Días de tratamiento y Procedencia (Egreso de clínica vs Ambulatorio).
   - Si un operador reporta novedad (falta de copago, insumo no contratado, paciente no contactado), clasificar la novedad y alertar a la Coordinación (Dr. Federico Cortes)."""
    
    AUTO_REPLY_CONFIDENCE_THRESHOLD: float = 95.0
    HUMAN_REVIEW_CONFIDENCE_THRESHOLD: float = 85.0
    
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/database/email_agent.db"
    
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
