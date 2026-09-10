import logging
from typing import Dict, Any, List
from config.settings import settings
from database.models import CustomRule
from .rule_engine import RuleEngine

logger = logging.getLogger(__name__)

class DecisionEngine:
    @staticmethod
    def evaluate(ai_analysis: Dict[str, Any], rules: List[CustomRule] = None) -> Dict[str, Any]:
        """
        Evaluates AI analysis, confidence scores, risk matrix, operational mode,
        and custom rules to determine final category, labels, priority, and auto-reply permissions.
        """
        result = dict(ai_analysis)

        # 1. Apply Custom Rule overrides
        if rules:
            rule_overrides = RuleEngine.evaluate_rules(result, rules)
            result.update(rule_overrides)

        confidence = float(result.get("confidence", 0.0))
        risk_level = result.get("risk_level", "BAJO").upper()
        category = result.get("category", "INFORMACION").upper()
        
        # 2. Strict Risk Evaluation Matrix
        if risk_level == "ALTO" or category in ["URGENTE", "SPAM"]:
            result["can_auto_reply"] = False
            if category != "SPAM":
                result["requires_human_review"] = True
                if "Revisión humana" not in result["tags"]:
                    result["tags"].append("Revisión humana")

        # 3. Confidence Threshold Matrix
        if confidence < 70.0:
            result["requires_human_review"] = True
            result["can_auto_reply"] = False
            result["category"] = "REVISION_HUMANA"
            if "Revisión humana" not in result["tags"]:
                result["tags"].append("Revisión humana")
        elif 70.0 <= confidence < 85.0:
            result["can_auto_reply"] = False
            result["requires_human_review"] = True
            if "Revisión humana" not in result["tags"]:
                result["tags"].append("Revisión humana")
        elif 85.0 <= confidence < 95.0:
            # Low risk simple confirmations are allowed auto reply if category is RESPUESTA_SIMPLE
            if category == "RESPUESTA_SIMPLE" and risk_level == "BAJO":
                result["can_auto_reply"] = True
                result["requires_human_review"] = False
            else:
                result["can_auto_reply"] = False
                result["requires_human_review"] = True

        # 4. Supervised Mode Enforcement
        if settings.OPERATIONAL_MODE.lower() == "supervised":
            logger.info("[DecisionEngine] Operational mode is SUPERVISED. Routing email to human review.")
            if result.get("can_auto_reply"):
                result["requires_human_review"] = True
                result["can_auto_reply"] = False
                if "Revisión humana" not in result["tags"]:
                    result["tags"].append("Revisión humana")

        # 5. Ensure "Respondido por IA" tag is added when auto-replying
        if result.get("can_auto_reply"):
            if "Respondido por IA" not in result["tags"]:
                result["tags"].append("Respondido por IA")
            result["status"] = "PENDIENTE" # Will transition to RESPONDIDO_IA once sent
        elif result.get("requires_human_review"):
            result["status"] = "PENDIENTE"
        elif category == "SPAM":
            result["status"] = "IGNORADO"

        return result
