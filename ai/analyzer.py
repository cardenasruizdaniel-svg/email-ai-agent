import logging
from typing import Dict, Any, List
from .llm_provider import get_llm_provider
from .attachment_parser import AttachmentParser

logger = logging.getLogger(__name__)

class EmailAnalyzer:
    def __init__(self):
        self.llm_provider = get_llm_provider()

    async def process_email(
        self,
        sender_name: str,
        sender_email: str,
        subject: str,
        body: str,
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes an incoming email and returns structured classification results.
        """
        attachments_summary = ""
        if attachments:
            attachments_summary = AttachmentParser.process_attachments(attachments)

        analysis = await self.llm_provider.analyze_email(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            body=body,
            attachments_summary=attachments_summary
        )

        # Sanitize & Validate fields
        analysis["category"] = analysis.get("category", "INFORMACION").upper()
        analysis["priority"] = analysis.get("priority", "MEDIA").upper()
        analysis["confidence"] = float(analysis.get("confidence", 90.0))
        analysis["risk_level"] = analysis.get("risk_level", "BAJO").upper()
        analysis["tags"] = analysis.get("tags", [])
        analysis["subcategories"] = analysis.get("subcategories", [])
        analysis["risk_reasons"] = analysis.get("risk_reasons", [])
        analysis["requires_human_review"] = bool(analysis.get("requires_human_review", False))
        analysis["can_auto_reply"] = bool(analysis.get("can_auto_reply", False))

        # Workflow & Tracking fields
        analysis["target_folder"] = analysis.get("target_folder") or "General"
        analysis["workflow_topic"] = analysis.get("workflow_topic") or ""
        analysis["patient_name"] = analysis.get("patient_name") or ""
        analysis["patient_id_doc"] = analysis.get("patient_id_doc") or ""
        analysis["workflow_action"] = analysis.get("workflow_action") or "NINGUNA"
        analysis["problem_reason"] = analysis.get("problem_reason") or ""
        analysis["bottleneck_category"] = analysis.get("bottleneck_category") or ""

        logger.info(
            f"[EmailAnalyzer] Analysis completed for '{subject}' | Category: {analysis['category']} | "
            f"Priority: {analysis['priority']} | Confidence: {analysis['confidence']}% | Risk: {analysis['risk_level']}"
        )
        return analysis
