from abc import ABC, abstractmethod

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

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_code(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        pass
