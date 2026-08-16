import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "RedPatch"
    VERSION: str = "v0.4.0"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").strip()
    API_KEY: str = (os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY") or "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()

    def validate(self):
        if not self.API_KEY:
            raise ValueError("GEMINI_API_KEY (or API_KEY) is not configured.")

settings = Settings()
