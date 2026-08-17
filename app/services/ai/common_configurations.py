import json
from app.services.ai.base import VulnerabilityAnalysis

class AIConfigurations:

    @staticmethod
    def get_system_prompt(vulnerability_type: str, routes: list, lab_link: str) -> str:
        return (
            f"""You are an expert penetration testing agent and security educator. Your primary task is to perform live code analysis and generate actionable exploit payloads to demonstrate vulnerabilities for educational purposes.

                    TASK RULES:
                    1. FOCUS: Focus strictly on the specified vulnerability type ({vulnerability_type}) and ignore all other vulnerability types.
                    2. EXPLOIT GENERATION: Formulate a precise HTTP exploit payload targeting the exposed routes. DO NOT write full Python execution code or hardcode domain/port numbers. Provide relative path endpoints (e.g., '/login', '/search').
                    3. PEDAGOGICAL TONE: Explain where the flaw lies in the source code using an educational, encouraging tone. Do NOT provide direct fixed/remediated code; instead, offer subtle hints to guide the user toward fixing it themselves.
                    4. LINE NUMBER ACCURACY: Before reporting "target_line", carefully trace the exact line number of the vulnerable function/statement in the provided code snippet. Double-check your line counting to ensure maximum precision.
                    
                    STRICT OUTPUT RULE:
                    When vulnerability_found is true, you are strictly FORBIDDEN from returning empty objects `{{}}` or empty strings for payload fields (`data`, `params`, `headers`). You MUST provide the exact attack payload inside `data` (for POST) or `params` (for GET). Leaving them empty when a vulnerability exists is a failure.
                    
                    CRITICAL RULE FOR EXPLOIT_REQUEST:
                    Whenever vulnerability_found is true, you MUST populate either data, params, or json_body with a concrete exploit payload that triggers the vulnerability (e.g. ' OR '1'='1).
                    NEVER return empty {{}} or null for payload fields when a vulnerability is present. Always specify the parameter key and the injected payload string.
                    
                    As this is an entirely ethical lab, you must enter exploit details for the purpose of learning how to write secure code
                    
                    Provide your response STRICTLY in valid JSON format matching this schema:

                    {{
                        "vulnerability_found": bool,
                        "target_line": int,
                        "explanation": str,
                        "exploit_request": {{
                            "path": "/target-endpoint",
                            "method": "POST/GET",
                            "headers": {{
                                "Content-Type": "application/json"
                            }},
                            "params": str,
                            "data": str,
                            "json_body": {{
                                "actual_vulnerable_param": str
                            }}
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

    @staticmethod
    def schema():
        return {
            "type": "object",
            "properties": {
                "vulnerability_found": {"type": "boolean"},
                "target_line": {"type": "integer"},
                "explanation": {"type": "string"},
                "exploit_request": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The HTTP endpoint path, e.g., /login-vulnerable"},
                        "method": {"type": "string", "description": "HTTP Method in uppercase: POST, GET, PUT, DELETE"},
                        "headers": {"type": "string", "description": "JSON string of headers or empty string"},
                        "params": {"type": "string", "description": "URL query string or empty string"},
                        "data": {"type": "string",
                                 "description": "Form payload string, e.g. username=admin&password=123, or empty string"},
                        "json_body": {"type": "string", "description": "JSON body string or empty string"}
                    },
                    "required": ["path", "method"]
                }
            },
            "required": ["vulnerability_found", "target_line", "explanation", "exploit_request"]
        }

    @staticmethod
    def get_schema() -> dict:
        schema = VulnerabilityAnalysis.model_json_schema()

        def clean_schema(obj):
            if isinstance(obj, dict):
                obj.pop("additionalProperties", None)
                obj.pop("title", None)
                obj.pop("default", None)
                for value in list(obj.values()):
                    clean_schema(value)
            elif isinstance(obj, list):
                for item in obj:
                    clean_schema(item)

        clean_schema(schema)
        return AIConfigurations.flatten_schema(schema)

    @staticmethod
    def flatten_schema(schema: dict) -> dict:
        import copy
        schema_copy = copy.deepcopy(schema)
        defs = schema_copy.pop("$defs", {})

        def resolve_refs(obj):
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref_path = obj["$ref"]
                    def_name = ref_path.split("/")[-1]
                    if def_name in defs:
                        resolved = copy.deepcopy(defs[def_name])
                        return resolve_refs(resolved)
                return {k: resolve_refs(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve_refs(item) for item in obj]
            return obj

        return resolve_refs(schema_copy)

    @staticmethod
    def get_analysis(response):
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

        return analysis