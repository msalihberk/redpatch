from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

class VulnerabilityAnalysis(BaseModel):
    vulnerability_found: bool = False
    target_line: int = Field(default=0, ge=0)
    exploit_payload: str = ""
    explanation: str = ""

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_code(self, code: str, vulnerability_type: str, routes: list, lab_link: str) -> VulnerabilityAnalysis:
        pass
