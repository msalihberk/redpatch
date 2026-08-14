from abc import ABC, abstractmethod
from pydantic import BaseModel

class VulnerabilityAnalysis(BaseModel):
    vulnerability_found: bool
    vulnerability_type: str
    target_line: int
    exploit_payload: str
    explanation: str

class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyze_code(self, code: str) -> VulnerabilityAnalysis:
        pass
