from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel
from typing import Dict, Any, Optional

class ExploitRequest(BaseModel):
    path: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    json_body: Optional[Dict[str, Any]] = None

class VulnerabilityAnalysis(BaseModel):
    vulnerability_found: bool
    target_line: int
    explanation: str
    exploit_request: Optional[ExploitRequest] = None

async def execute_exploit_request(
    exploit_request: ExploitRequest,
    lab_link: str,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    relative_path = exploit_request.path.lstrip("/")
    target_url = f"http://{lab_link}/{relative_path}"

    if not target_url.startswith(f"http://{lab_link}"):
        return {
            "success": False,
            "error": "Scope Violation: Target URL is outside the allowed container boundary.",
        }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=exploit_request.method.upper(),
                url=target_url,
                headers=exploit_request.headers or {},
                params=exploit_request.params,
                data=exploit_request.data if not exploit_request.json_body else None,
                json=exploit_request.json_body,
            )

            return {
                "success": True,
                "status_code": response.status_code,
                "target_url": str(response.url),
                "headers": dict(response.headers),
                "response_body": response.text[:3000],
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out while connecting to the target container.",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to execute exploit request: {str(exc)}",
        }

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_code(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        pass
