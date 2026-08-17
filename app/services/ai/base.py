import json
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, model_validator
from typing import Dict, Union, Optional, Any
from urllib.parse import parse_qs


class ExploitRequest(BaseModel):
    path: str = Field(
        description="The HTTP endpoint path, e.g., /login-vulnerable"
    )
    method: str = Field(
        description="HTTP Method in uppercase: POST, GET, PUT, DELETE"
    )
    headers: Optional[Dict[str, str]] = Field(
        default_factory=lambda: {"Content-Type": "application/json"},
        description="HTTP request headers."
    )
    params: Optional[Dict[str, str]] = Field(
        default=None,
        description="URL Query parameters."
    )
    data: Optional[Dict[str, str]] = Field(
        default=None,
        description="Form payload."
    )
    json_body: Optional[Dict[str, str]] = Field(
        default=None,
        description="JSON body payload."
    )

    @model_validator(mode="before")
    @classmethod
    def force_dict_normalization(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for field in ["headers", "params", "data", "json_body"]:
                val = values.get(field)

                if val is None or val == "" or val == "null" or val == {}:
                    values[field] = {}
                    continue

                if isinstance(val, str):
                    val = val.strip()
                    if not val or val.lower() == "null":
                        values[field] = {}
                        continue

                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, dict):
                            values[field] = parsed
                            continue
                    except json.JSONDecodeError:
                        pass

                    try:
                        parsed_qs = parse_qs(val, keep_blank_values=True)
                        values[field] = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in
                                         parsed_qs.items()}
                    except Exception:
                        values[field] = {}

        return values

class VulnerabilityAnalysis(BaseModel):
    vulnerability_found: bool
    target_line: int
    explanation: str
    exploit_request: ExploitRequest

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_code(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        pass
