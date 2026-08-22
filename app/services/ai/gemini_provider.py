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

from abc import ABC

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, VulnerabilityAnalysis
from app.services.ai.common_configurations import AIConfigurations


class GeminiProvider(BaseLLMProvider, ABC):
    def __init__(self):
        settings.validate()
        self.client = genai.Client(api_key=settings.API_KEY)

    async def analyze_code(self, code: str, vulnerability_type: str, routes: list,
                           lab_link: str):

        system_prompt = AIConfigurations.get_system_prompt(vulnerability_type, routes, lab_link)

        response = await self.client.aio.models.generate_content(
            model=settings.MODEL,
            contents=f"Analyze the following code for vulnerabilities and generate a working exploit payload:\n\n{code}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=AIConfigurations.schema(),
                temperature=0.1,
            )
        )
        print(response.text)

        return AIConfigurations.get_analysis(response)
