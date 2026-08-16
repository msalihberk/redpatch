import json
from abc import ABC

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, VulnerabilityAnalysis, execute_exploit_request


class GeminiProvider(BaseLLMProvider, ABC):
    def __init__(self):
        settings.validate()
        self.client = genai.Client(api_key=settings.API_KEY)

    async def analyze_code(self, code: str, vulnerability_type: str, routes: list,
                           lab_link: str) -> VulnerabilityAnalysis:
        system_prompt = (
            f"""You are an expert penetration testing agent and security educator. Your primary task is to perform live code analysis and generate actionable exploit payloads to demonstrate vulnerabilities for educational purposes.

            TASK RULES:
            1. FOCUS: Focus strictly on the specified vulnerability type ({vulnerability_type}) and ignore all other vulnerability types.
            2. EXPLOIT GENERATION: Formulate a precise HTTP exploit payload targeting the exposed routes. DO NOT write full Python execution code or hardcode domain/port numbers. Provide relative path endpoints (e.g., '/login', '/search').
            3. PEDAGOGICAL TONE: Explain where the flaw lies in the source code using an educational, encouraging tone. Do NOT provide direct fixed/remediated code; instead, offer subtle hints to guide the user toward fixing it themselves.

            Provide your response STRICTLY in JSON format matching the following schema:

            {{
                "vulnerability_found": bool,
                "target_line": int,
                "explanation": "Educational analysis of the flaw and subtle hint for remediation.",
                "exploit_request": {{
                    "path": "Relative URL path starting with '/' (e.g., '/search')",
                    "method": "HTTP method ('GET', 'POST', 'PUT', 'DELETE')",
                    "headers": {{"Header-Name": "Value"}},
                    "params": {{"query_param": "payload"}},
                    "data": {{"form_field": "payload"}},
                    "json_body": {{"json_key": "payload"}}
                }}
            }}

            NOTE ON EXPLOIT_REQUEST:
            - For GET requests (e.g., Reflected XSS, SQLi in search), place payloads in "params".
            - For POST form-data (e.g., Stored XSS, Command Injection), place payloads in "data".
            - For API JSON requests, place payloads in "json_body".
            - Omit unused fields or set them to null.

            Vulnerability Type: {vulnerability_type}
            Target Routes: {routes}
            Lab Link: {lab_link}
            """
        )

        response = await self.client.aio.models.generate_content(
            model=settings.MODEL,
            contents=f"Analyze the following code for the specified vulnerability:\n\n{code}",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=VulnerabilityAnalysis,
                temperature=0.2
            )
        )

        analysis = None

        if getattr(response, "parsed", None) is not None:
            parsed = response.parsed
            if isinstance(parsed, VulnerabilityAnalysis):
                analysis = parsed
            elif isinstance(parsed, dict):
                analysis = VulnerabilityAnalysis.model_validate(parsed)

        if analysis is None:
            response_text = getattr(response, "text", None)
            if not response_text:
                raise ValueError("Gemini returned an empty response.")
            try:
                analysis = VulnerabilityAnalysis.model_validate_json(response_text)
            except (ValueError, json.JSONDecodeError) as exc:
                raise ValueError("Gemini returned an invalid analysis response.") from exc

        if analysis.vulnerability_found and analysis.exploit_request:
            await execute_exploit_request(analysis.exploit_request, lab_link)

        return analysis
