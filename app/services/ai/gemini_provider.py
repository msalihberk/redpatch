import json
import asyncio
from abc import ABC

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, VulnerabilityAnalysis


class GeminiProvider(BaseLLMProvider, ABC):
    def __init__(self):
        settings.validate()
        self.client = genai.Client(api_key=settings.API_KEY)

    async def analyze_code(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        system_prompt = (
            f"""You are a penetration testing expert whose goal is to perform code analysis to teach secure coding practices.
                Your task is to analyze the provided code and identify security vulnerabilities. However, to stay aligned with the concept of the specific lab, you must focus only on the specified vulnerability type and ignore all other types of vulnerabilities.
                Attempt to exploit the target based on the provided routes, and explain in an educational tone where you found the vulnerability in the code. Additionally, do not give direct solutions or fixed code immediately; instead, guide the user by providing subtle hints.          
                Provide all your responses strictly in JSON format matching the following schema (As we’re talking about websites, the payload will usually be an HTTP request):

                {
                    "vulnerability_found": bool,
                    "target_line": int,
                    "exploit_payload": str,
                    "explanation": str
                }
                
                Vulnerability Type: {vulnerability_type}
                Routes: {routes}
                Lab Link: {lab_link}
            """
        )

        # The Gemini SDK method is synchronous. Run it in a worker thread so an
        # analysis request does not block FastAPI's event loop.
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=f"Analyze the following code for the specified vulnerability:\n\n{code}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=VulnerabilityAnalysis,
                temperature=0.2
            )
        )

        if getattr(response, "parsed", None) is not None:
            parsed = response.parsed
            if isinstance(parsed, VulnerabilityAnalysis):
                return parsed
            if isinstance(parsed, dict):
                return VulnerabilityAnalysis.model_validate(parsed)

        response_text = getattr(response, "text", None)
        if not response_text:
            raise ValueError("Gemini returned an empty response.")

        try:
            return VulnerabilityAnalysis.model_validate_json(response_text)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Gemini returned an invalid analysis response.") from exc
