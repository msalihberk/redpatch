from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, VulnerabilityAnalysis
from app.services.ai.gemini_provider import GeminiProvider


class RedTeamAgent:
    def __init__(self):
        self.provider: BaseLLMProvider = self._get_provider()
    def _get_provider(self) -> BaseLLMProvider:
        provider_name = settings.LLM_PROVIDER.lower()

        if provider_name == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"Unsupported or undefined LLM provider: {provider_name}")

    async def run_attack(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        return await self.provider.analyze_code(code, vulnerability_type, routes, lab_link)
