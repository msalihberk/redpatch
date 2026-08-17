import json
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, model_validator
from typing import Dict, Union, Optional, Any


class ExploitRequest(BaseModel):
    path: str = Field(
        description="The HTTP endpoint path, e.g., /login-vulnerable"
    )
    method: str = Field(
        description="HTTP Method in uppercase: POST, GET, PUT, DELETE"
    )
    headers: Dict[str, str] = Field(
        default_factory=lambda: {"Content-Type": "application/json"},
        description="HTTP request headers. Include Content-Type if needed."
    )
    params: Optional[Dict[str, str]] = Field(
        default=None,
        description="URL Query parameters for GET requests. Example: {\"username\": \"admin' OR '1'='1\"}"
    )
    data: Optional[Dict[str, str]] = Field(
        default=None,
        description="Form payload (x-www-form-urlencoded). Example: {\"username\": \"admin' OR '1'='1\", \"password\": \"123\"}"
    )
    json_body: Optional[Dict[str, str]] = Field(
        default=None,
        description="JSON body payload for POST/PUT requests. MUST be populated for JSON endpoints!"
    )

    @model_validator(mode="before")
    @classmethod
    def parse_stringified_json_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ["headers", "params", "data", "json_body"]:
                if field in data and isinstance(data[field], str):
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        data[field] = {}
        return data

class VulnerabilityAnalysis(BaseModel):
    vulnerability_found: bool
    target_line: int
    explanation: str
    exploit_request: ExploitRequest

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_code(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        pass
