import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .base import BaseEmailClient

logger = logging.getLogger(__name__)

MOCK_SEED_EMAILS: List[Dict[str, Any]] = [
    {
        "id": "msg_001",
        "thread_id": "thread_001",
        "sender_email": "informacion@empresa-cliente.com",
        "sender_name": "Carlos Mendoza",
        "subject": "Consulta de Horarios y Servicios",
        "body": "Buenos días, quisiera conocer el horario de atención al cliente y los servicios que prestan actualmente en su sede principal. Muchas gracias.",
        "snippet": "Buenos días, quisiera conocer el horario de atención...",
        "date": datetime.utcnow() - timedelta(minutes=45),
        "attachments": []
    },
    {
        "id": "msg_002",
        "thread_id": "thread_002",
        "sender_email": "ana.gomez@techcorp.io",
        "sender_name": "Ana Gómez",
        "subject": "Confirmación de Recepción de Documentos",
        "body": "Por favor confirmar si recibieron los documentos de la propuesta firmada que enviamos ayer por la tarde.",
        "snippet": "Por favor confirmar si recibieron los documentos...",
        "date": datetime.utcnow() - timedelta(minutes=30),
        "attachments": []
    },
    {
        "id": "msg_003",
        "thread_id": "thread_003",
        "sender_email": "luis.martinez@logistica-global.com",
        "sender_name": "Luis Martínez",
        "subject": "Disponibilidad Capacitación Martes",
        "body": "Hola equipo, ¿podrían confirmar si están disponibles para realizar la sesión de capacitación el próximo martes a las 10:00 AM?",
        "snippet": "¿podrían confirmar si están disponibles...",
        "date": datetime.utcnow() - timedelta(minutes=25),
        "attachments": []
    },
    {
        "id": "msg_004",
        "thread_id": "thread_004",
        "sender_email": "soporte@servicios-abc.com",
        "sender_name": "Oficina Servicios ABC",
        "subject": "Estado de Solicitud #4829",
        "body": "Estimados, ¿la solicitud #4829 fue recibida correctamente por su departamento de soporte?",
        "snippet": "¿la solicitud #4829 fue recibida correctamente...",
        "date": datetime.utcnow() - timedelta(minutes=20),
        "attachments": []
    },
    {
        "id": "msg_005",
        "thread_id": "thread_005",
        "sender_email": "mario.vargas@construcciones.co",
        "sender_name": "Mario Vargas",
        "subject": "Reenvío de Cotización de Insumos",
        "body": "Buenos días. ¿Podrían enviarme nuevamente la cotización de insumos de oficina que nos remitieron el mes pasado? No logro ubicar el archivo.",
        "snippet": "¿Podrían enviarme nuevamente la cotización...",
        "date": datetime.utcnow() - timedelta(minutes=15),
        "attachments": []
    },
    {
        "id": "msg_006",
        "thread_id": "thread_006",
        "sender_email": "compras@multinacional.es",
        "sender_name": "Elena Rostova",
        "subject": "Solicitud de Cotización Formal - 500 Servidores",
        "body": "Estimados, necesitamos una cotización formal y desglose de precios para la adquisición de 500 servidores de rack con garantía extendida a 3 años. Adjuntamos pliego técnico.",
        "snippet": "necesitamos una cotización formal y desglose de precios...",
        "date": datetime.utcnow() - timedelta(minutes=12),
        "attachments": [{"filename": "pliego_tecnico.pdf", "mime_type": "application/pdf", "content_text": "Especificación técnica para 500 servidores Xeon..."}]
    },
    {
        "id": "msg_007",
        "thread_id": "thread_007",
        "sender_email": "pedro.sanchez@banca-capital.com",
        "sender_name": "Pedro Sánchez",
        "subject": "RECLAMO GRAVE - Falla de Producción",
        "body": "URGENTE: El servicio contratado presentó una falla crítica en nuestro servidor de producción esta madrugada y hemos experimentado pérdida de datos. Requerimos intervención inmediata de la gerencia.",
        "snippet": "URGENTE: El servicio contratado presentó una falla crítica...",
        "date": datetime.utcnow() - timedelta(minutes=10),
        "attachments": []
    },
    {
        "id": "msg_008",
        "thread_id": "thread_008",
        "sender_email": "finanzas@sociedad-inversion.com",
        "sender_name": "Roberto Blanco",
        "subject": "URGENTE: Cambio de Cuenta Bancaria para Transferencia",
        "body": "Por favor enviar los datos bancarios actualizados y la certificación de la cuenta para realizar la transferencia de $10,000 USD antes de las 5:00 PM de hoy.",
        "snippet": "Por favor enviar los datos bancarios actualizados...",
        "date": datetime.utcnow() - timedelta(minutes=8),
        "attachments": []
    },
    {
        "id": "msg_009",
        "thread_id": "thread_009",
        "sender_email": "promocion@ofertas-increibles-xyz.com",
        "sender_name": "Ofertas VIP",
        "subject": "¡Gana un viaje gratis a Cancún y 50% DCTO en Marketing!",
        "body": "¡Felicidades! Ha sido seleccionado para recibir una consultoría SEO gratuita y un viaje todo incluido. Haga clic en el siguiente enlace para reclamar su premio.",
        "snippet": "¡Felicidades! Ha sido seleccionado para recibir...",
        "date": datetime.utcnow() - timedelta(minutes=6),
        "attachments": []
    },
    {
        "id": "msg_010",
        "thread_id": "thread_010",
        "sender_email": "contacto@desconocido-empresa.net",
        "sender_name": "Usuario Anon",
        "subject": "Sobre lo conversado",
        "body": "Hola, respecto a lo que se habló el otro día, por favor avísenme si procede o no para gestionar los temas correspondientes.",
        "snippet": "Hola, respecto a lo que se habló el otro día...",
        "date": datetime.utcnow() - timedelta(minutes=4),
        "attachments": []
    },
    {
        "id": "msg_011",
        "thread_id": "thread_011",
        "sender_email": "licitaciones@gobierno-local.gov",
        "sender_name": "Dirección de Compras",
        "subject": "Apertura de Licitación Pública #2026-89",
        "body": "Se adjunta el pliego de condiciones de la Licitación Pública #2026-89 para la renovación de infraestructura de correo y telecomunicaciones. Favor revisar los anexos.",
        "snippet": "Se adjunta el pliego de condiciones de la Licitación...",
        "date": datetime.utcnow() - timedelta(minutes=2),
        "attachments": [{"filename": "licitacion_2026.pdf", "mime_type": "application/pdf", "content_text": "Pliego de condiciones licitación pública renovación infraestructura de correo."}]
    },
    {
        "id": "msg_012",
        "thread_id": "thread_005",  # Same thread as msg_005 (Mario Vargas)!
        "sender_email": "mario.vargas@construcciones.co",
        "sender_name": "Mario Vargas",
        "subject": "Re: Reenvío de Cotización de Insumos",
        "body": "Hola equipo, ¿tienen alguna novedad sobre el reenvío de la cotización que les pedí hace un momento? Quedo atento.",
        "snippet": "Hola equipo, ¿tienen alguna novedad sobre el reenvío...",
        "date": datetime.utcnow() - timedelta(minutes=1),
        "attachments": []
    }
]

class MockEmailClient(BaseEmailClient):
    def __init__(self):
        self.unread_emails: List[Dict[str, Any]] = list(MOCK_SEED_EMAILS)
        self.processed_emails: List[Dict[str, Any]] = []
        self.sent_emails: List[Dict[str, Any]] = []
        self.labels_applied: Dict[str, List[str]] = {}

    async def fetch_unprocessed_emails(self, max_results: int = 20) -> List[Dict[str, Any]]:
        logger.info(f"[MockEmailClient] Fetching unprocessed emails ({len(self.unread_emails)} available)")
        result = self.unread_emails[:max_results]
        return result

    async def send_email(self, to_email: str, subject: str, body: str, thread_id: Optional[str] = None) -> bool:
        sent_record = {
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "thread_id": thread_id,
            "sent_at": datetime.utcnow()
        }
        self.sent_emails.append(sent_record)
        logger.info(f"[MockEmailClient] SENT EMAIL to {to_email} | Subject: {subject}")
        return True

    async def apply_labels(self, message_id: str, label_names: List[str]) -> bool:
        if message_id not in self.labels_applied:
            self.labels_applied[message_id] = []
        self.labels_applied[message_id].extend(label_names)
        logger.info(f"[MockEmailClient] Applied labels {label_names} to message {message_id}")
        return True

    async def mark_as_read(self, message_id: str) -> bool:
        for idx, email in enumerate(self.unread_emails):
            if email["id"] == message_id:
                processed = self.unread_emails.pop(idx)
                self.processed_emails.append(processed)
                logger.info(f"[MockEmailClient] Marked message {message_id} as processed")
                return True
        return False
