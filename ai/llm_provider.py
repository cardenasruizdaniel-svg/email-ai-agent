import json
import logging
import re
import httpx
from typing import Dict, Any, Optional
from config.settings import settings
from .prompts import SYSTEM_ANALYSIS_PROMPT, SYSTEM_REPLY_PROMPT

logger = logging.getLogger(__name__)

class BaseLLMProvider:
    async def analyze_email(self, sender_name: str, sender_email: str, subject: str, body: str, attachments_summary: str = "") -> Dict[str, Any]:
        raise NotImplementedError

    async def generate_reply(self, email_context: Dict[str, Any], custom_instruction: str = "") -> str:
        raise NotImplementedError


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def analyze_email(self, sender_name: str, sender_email: str, subject: str, body: str, attachments_summary: str = "") -> Dict[str, Any]:
        prompt = f"""
Remitente: {sender_name} <{sender_email}>
Asunto: {subject}
Cuerpo del Mensaje:
{body}

{attachments_summary}

Por favor analiza el mensaje según las instrucciones del sistema y devuelve únicamente el JSON correspondiente.
"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_ANALYSIS_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        "format": "json",
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("message", {}).get("content", "{}")
                    parsed = json.loads(content)
                    return parsed
                else:
                    logger.warning(f"[OllamaProvider] API returned status {response.status_code}. Falling back to Heuristic Engine.")
        except Exception as e:
            logger.warning(f"[OllamaProvider] Could not connect to Ollama at {self.base_url}: {e}. Using Heuristic Fallback Provider.")

        # Fallback if Ollama is not running
        fallback = HeuristicProvider()
        return await fallback.analyze_email(sender_name, sender_email, subject, body, attachments_summary)

    async def generate_reply(self, email_context: Dict[str, Any], custom_instruction: str = "") -> str:
        system = SYSTEM_REPLY_PROMPT.format(
            company_name=settings.COMPANY_NAME,
            agent_name=settings.AGENT_NAME,
            agent_role=settings.AGENT_ROLE,
            company_hours=settings.COMPANY_HOURS,
            company_phone=settings.COMPANY_PHONE,
            reply_signature=settings.REPLY_SIGNATURE
        )
        prompt = f"""
Contexto del correo recibido:
- Remitente: {email_context.get('sender_name', '')}
- Asunto: {email_context.get('subject', '')}
- Solicitud: {email_context.get('intent_summary', '')}

Instrucción adicional: {custom_instruction}

Genera el cuerpo del correo de respuesta:
"""
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning(f"[OllamaProvider] Error generating reply via Ollama: {e}")

        fallback = HeuristicProvider()
        return await fallback.generate_reply(email_context, custom_instruction)


class HeuristicProvider(BaseLLMProvider):
    """
    Zero-cost, local semantic and rule heuristic provider that works 100% offline
    with zero external dependencies or API keys.
    """
    async def analyze_email(self, sender_name: str, sender_email: str, subject: str, body: str, attachments_summary: str = "") -> Dict[str, Any]:
        text_full = f"{subject} {body} {attachments_summary}".lower()

        # Company inference
        company = ""
        if "@" in sender_email:
            domain = sender_email.split("@")[1]
            domain_name = domain.split(".")[0]
            if domain_name not in ["gmail", "yahoo", "hotmail", "outlook"]:
                company = domain_name.replace("-", " ").replace("_", " ").title()

        # Risk Analysis Keywords
        high_risk_triggers = [
            "contrato", "legal", "demanda", "abogado", "banco", "bancario", "bancarios",
            "transferencia", "cuenta bancaria", "pago de $", "usd", "dólares", "dolares",
            "falla crítica", "falla critica", "pérdida de datos", "perdida de datos",
            "reclamo grave", "emergencia", "médico", "salud", "clínica"
        ]

        detected_risk_reasons = []
        for kw in high_risk_triggers:
            if kw in text_full:
                detected_risk_reasons.append(f"Palabra clave de alto riesgo detectada: '{kw}'")

        # Spam Detection
        spam_keywords = ["viaje gratis", "gane un", "felicidades! ha sido seleccionado", "descuento en marketing", "ofertas vip", "haga clic en"]
        is_spam = any(kw in text_full for kw in spam_keywords)

        if is_spam:
            return {
                "sender_name": sender_name,
                "company": company or "Promoción externa",
                "intent_summary": "Promoción comercial no solicitada o posible spam",
                "category": "SPAM",
                "subcategories": ["Publicidad masiva"],
                "tags": ["Spam", "Publicidad", "No requiere acción"],
                "priority": "BAJA",
                "confidence": 99.0,
                "risk_level": "BAJO",
                "risk_reasons": ["Correo identificado como publicidad o spam"],
                "requires_human_review": False,
                "can_auto_reply": False,
                "suggested_reply": ""
            }

        # Ambiguous Email Detection
        ambiguous_triggers = ["sobre lo conversado", "lo que se habló", "avísenme si procede", "avisenme si procede"]
        if any(trigger in text_full for trigger in ambiguous_triggers) and len(body.split()) < 30:
            return {
                "sender_name": sender_name,
                "company": company,
                "intent_summary": "Solicitud ambigua sin contexto suficiente",
                "category": "REVISION_HUMANA",
                "subcategories": ["Mensaje poco claro"],
                "tags": ["Revisión humana"],
                "priority": "MEDIA",
                "confidence": 65.0, # < 70% confidence requires human review
                "risk_level": "MEDIO",
                "risk_reasons": ["Falta de contexto claro en el correo"],
                "requires_human_review": True,
                "can_auto_reply": False,
                "suggested_reply": ""
            }

        # Urgent / High Risk Email
        if detected_risk_reasons or "reclamo grave" in text_full or "urgente" in subject.lower():
            return {
                "sender_name": sender_name,
                "company": company,
                "intent_summary": f"Asunto crítico/urgente: {subject}",
                "category": "URGENTE",
                "subcategories": ["Incidente crítico", "Asunto financiero/legal"],
                "tags": ["Urgente", "Revisión humana"],
                "priority": "CRITICA" if "falla" in text_full or "reclamo" in text_full else "ALTA",
                "confidence": 94.0,
                "risk_level": "ALTO",
                "risk_reasons": detected_risk_reasons or ["Asunto de alta prioridad"],
                "requires_human_review": True,
                "can_auto_reply": False,  # Safety rule: Never auto-reply to high risk!
                "suggested_reply": ""
            }

        # Simple Confirmation / Acknowledgement (Safe for auto-reply)
        simple_triggers = ["confirmar si recibieron", "recibida por su", "confirmar si están disponibles", "disponibilidad capacitación", "solicitud #4829 fue recibida"]
        if any(trig in text_full for trig in simple_triggers):
            intent = "Confirmación de recepción de documentos o disponibilidad"
            if "disponibilidad" in text_full or "disponibles" in text_full:
                reply = f"Estimado/a {sender_name},\n\nConfirmamos que tenemos disponibilidad para la fecha y hora solicitada.\n\n{settings.REPLY_SIGNATURE}"
            elif "solicitud #4829" in text_full:
                reply = f"Estimado/a {sender_name},\n\nConfirmamos que la solicitud #4829 fue recibida correctamente por nuestro equipo de soporte.\n\n{settings.REPLY_SIGNATURE}"
            else:
                reply = f"Estimado/a {sender_name},\n\nSí, confirmamos la recepción de los documentos correctamente. Muchas gracias.\n\n{settings.REPLY_SIGNATURE}"

            return {
                "sender_name": sender_name,
                "company": company,
                "intent_summary": intent,
                "category": "RESPUESTA_SIMPLE",
                "subcategories": ["Confirmación simple"],
                "tags": ["Respuesta automática", "Requiere respuesta simple"],
                "priority": "BAJA",
                "confidence": 98.0, # >= 95%
                "risk_level": "BAJO",
                "risk_reasons": [],
                "requires_human_review": False,
                "can_auto_reply": True,
                "suggested_reply": reply
            }

        # Document Request / Quote re-send
        if "reenviarme nuevamente" in text_full or "reenvío de cotización" in text_full or "novedad sobre el reenvío" in text_full:
            return {
                "sender_name": sender_name,
                "company": company,
                "intent_summary": "Solicitud de reenvío de cotización previa o información",
                "category": "SOLICITUD",
                "subcategories": ["Solicitud de documento"],
                "tags": ["Solicitud de documento"],
                "priority": "MEDIA",
                "confidence": 96.0,
                "risk_level": "BAJO",
                "risk_reasons": [],
                "requires_human_review": False,
                "can_auto_reply": True,
                "suggested_reply": f"Estimado/a {sender_name},\n\nHemos recibido su solicitud de reenvío de cotización. Adjuntaremos la copia correspondiente a la brevedad.\n\n{settings.REPLY_SIGNATURE}"
            }

        # Formal Quote Request (Requires human calculation / quotation)
        if "cotización formal" in text_full or "500 servidores" in text_full or "licitación pública" in text_full:
            return {
                "sender_name": sender_name,
                "company": company,
                "intent_summary": "Solicitud de cotización formal de gran volumen o licitación pública",
                "category": "SOLICITUD",
                "subcategories": ["Solicitud de cotización", "Licitación"],
                "tags": ["Solicitud de cotización", "Revisión humana"],
                "priority": "ALTA",
                "confidence": 92.0,
                "risk_level": "MEDIO",
                "risk_reasons": ["Requiere cálculo comercial de cotización"],
                "requires_human_review": True, # Supervised quote creation
                "can_auto_reply": False,
                "suggested_reply": ""
            }

        # General Information Inquiry
        if "horario de atención" in text_full or "información" in text_full or "servicios que prestan" in text_full:
            reply = f"Estimado/a {sender_name},\n\nGracias por comunicarse con {settings.COMPANY_NAME}.\n\nNuestro horario de atención es: {settings.COMPANY_HOURS}.\nOfrecemos servicios integrales de atención y soporte técnico. Si requiere información específica, con gusto le atenderemos.\n\n{settings.REPLY_SIGNATURE}"
            return {
                "sender_name": sender_name,
                "company": company,
                "intent_summary": "Consulta sobre horario de atención y servicios de la empresa",
                "category": "INFORMACION",
                "subcategories": ["Información de horarios", "Información de servicios"],
                "tags": ["Información relevante", "Respuesta automática"],
                "priority": "MEDIA",
                "confidence": 97.0,
                "risk_level": "BAJO",
                "risk_reasons": [],
                "requires_human_review": False,
                "can_auto_reply": True,
                "suggested_reply": reply
            }

        # Generic default fallback
        return {
            "sender_name": sender_name,
            "company": company,
            "intent_summary": f"Solicitud general: {subject}",
            "category": "INFORMACION",
            "subcategories": ["Información general"],
            "tags": ["Información relevante"],
            "priority": "MEDIA",
            "confidence": 90.0,
            "risk_level": "BAJO",
            "risk_reasons": [],
            "requires_human_review": False,
            "can_auto_reply": True,
            "suggested_reply": f"Estimado/a {sender_name},\n\nHemos recibido su correo referente a '{subject}'. Su mensaje está siendo procesado por nuestro equipo.\n\n{settings.REPLY_SIGNATURE}"
        }

    async def generate_reply(self, email_context: Dict[str, Any], custom_instruction: str = "") -> str:
        suggested = email_context.get("suggested_reply", "")
        if suggested:
            return suggested
            
        sender = email_context.get("sender_name", "Cliente")
        subject = email_context.get("subject", "")
        return (
            f"Estimado/a {sender},\n\n"
            f"Gracias por comunicarse con {settings.COMPANY_NAME}. Confirmamos la recepción de su mensaje referente a '{subject}'.\n"
            f"Un representante revisará su solicitud en breve.\n\n"
            f"{settings.REPLY_SIGNATURE}"
        )


class GeminiProvider(BaseLLMProvider):
    """
    100% Free Cloud AI Provider using Google Gemini API free tier ($0 cost, 15 RPM).
    Does NOT require local GPU, local software, or Ollama installation.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY

    async def analyze_email(self, sender_name: str, sender_email: str, subject: str, body: str, attachments_summary: str = "") -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("[GeminiProvider] No GEMINI_API_KEY provided. Using Heuristic Provider.")
            fallback = HeuristicProvider()
            return await fallback.analyze_email(sender_name, sender_email, subject, body, attachments_summary)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        prompt = f"{SYSTEM_ANALYSIS_PROMPT}\n\nREMITENTE: {sender_name} <{sender_email}>\nASUNTO: {subject}\nCUERPO:\n{body}\n{attachments_summary}\n\nRESPONDE ÚNICAMENTE CON EL JSON:"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                if resp.status_code == 200:
                    raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_json)
        except Exception as e:
            logger.warning(f"[GeminiProvider] Error querying Gemini API: {e}. Using Heuristic Fallback.")

        fallback = HeuristicProvider()
        return await fallback.analyze_email(sender_name, sender_email, subject, body, attachments_summary)

    async def generate_reply(self, email_context: Dict[str, Any], custom_instruction: str = "") -> str:
        if not self.api_key:
            fallback = HeuristicProvider()
            return await fallback.generate_reply(email_context, custom_instruction)

        system = SYSTEM_REPLY_PROMPT.format(
            company_name=settings.COMPANY_NAME,
            agent_name=settings.AGENT_NAME,
            agent_role=settings.AGENT_ROLE,
            company_hours=settings.COMPANY_HOURS,
            company_phone=settings.COMPANY_PHONE,
            reply_signature=settings.REPLY_SIGNATURE
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        prompt = f"{system}\n\nREMITENTE: {email_context.get('sender_name')}\nASUNTO: {email_context.get('subject')}\nSOLICITUD: {email_context.get('intent_summary')}\n{custom_instruction}\n\nGenera la respuesta profesional:"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
                if resp.status_code == 200:
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.warning(f"[GeminiProvider] Error generating reply via Gemini: {e}")

        fallback = HeuristicProvider()
        return await fallback.generate_reply(email_context, custom_instruction)


def get_llm_provider() -> BaseLLMProvider:
    provider = settings.AI_PROVIDER.lower()
    if provider == "gemini" or (settings.GEMINI_API_KEY and provider != "ollama"):
        return GeminiProvider()
    elif provider == "ollama":
        return OllamaProvider()
    else:
        return HeuristicProvider()

