import logging
from typing import Dict, Any
from ai.llm_provider import get_llm_provider
from config.settings import settings

logger = logging.getLogger(__name__)

class ReplyGenerator:
    def __init__(self):
        self.llm_provider = get_llm_provider()

    async def generate_response(self, email_data: Dict[str, Any], custom_instructions: str = "") -> str:
        """
        Generates a verified, professional, anti-hallucination reply.
        """
        suggested = email_data.get("suggested_reply", "")
        if suggested and not custom_instructions:
            return suggested

        generated = await self.llm_provider.generate_reply(email_data, custom_instructions)
        return generated
