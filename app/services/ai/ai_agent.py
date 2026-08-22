# Copyright (C) 2026  Mustafa Salih Berk
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
