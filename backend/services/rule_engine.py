import logging
from typing import Dict, Any, List
from database.models import CustomRule

logger = logging.getLogger(__name__)

class RuleEngine:
    @staticmethod
    def evaluate_rules(email_data: Dict[str, Any], rules: List[CustomRule]) -> Dict[str, Any]:
        """
        Applies active user-defined rules to override or augment classification decisions.
        """
        sender = email_data.get("sender_email", "").lower()
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "").lower()
        has_attachment = bool(email_data.get("attachments", []))

        overrides = {}

        for rule in rules:
            if not rule.is_active:
                continue

            matched = False
            cond_type = rule.condition_type.upper()
            val = rule.condition_value.lower()

            if cond_type == "SENDER_EMAIL" and val in sender:
                matched = True
            elif cond_type == "SENDER_DOMAIN" and val in sender:
                matched = True
            elif cond_type == "SUBJECT_CONTAINS" and val in subject:
                matched = True
            elif cond_type == "BODY_CONTAINS" and val in body:
                matched = True
            elif cond_type == "HAS_ATTACHMENT" and has_attachment:
                matched = True

            if matched:
                logger.info(f"[RuleEngine] Matched Rule '{rule.name}' for message {email_data.get('id')}")
                if rule.action_priority:
                    overrides["priority"] = rule.action_priority
                if rule.action_category:
                    overrides["category"] = rule.action_category
                if rule.action_label:
                    current_tags = overrides.get("tags", list(email_data.get("tags", [])))
                    if rule.action_label not in current_tags:
                        current_tags.append(rule.action_label)
                    overrides["tags"] = current_tags
                if rule.action_allow_autoreply is not None:
                    overrides["can_auto_reply"] = rule.action_allow_autoreply
                    if not rule.action_allow_autoreply:
                        overrides["requires_human_review"] = True

        return overrides
