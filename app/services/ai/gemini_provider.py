import json
from abc import ABC

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, VulnerabilityAnalysis


class GeminiProvider(BaseLLMProvider, ABC):
    def __init__(self):
        self.client = genai.Client(api_key=settings.API_KEY)

    async def analyze_code(self, code: str) -> VulnerabilityAnalysis:
        system_prompt = (
            "Sen otonom bir AI Red Team sızma testi uzmanısın. "
            "Verilen koda özel dinamik bir exploit_payload üret. "
            "Yanıtını belirlenen JSON şemasına birebir uygun olarak döndür."
        )

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Aşağıdaki koda sızmayı dene:\n\n{code}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=VulnerabilityAnalysis,
                temperature=0.2
            )
        )

        data = json.loads(response.text)
        return VulnerabilityAnalysis(**data)
