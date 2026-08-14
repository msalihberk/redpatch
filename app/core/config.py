import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "RedPatch"
    VERSION: str = "v0.1.0"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    API_KEY: str = os.getenv("API_KEY", "")

    def validate(self):
        if not self.API_KEY:
            raise ValueError("API_KEY not found in .env file!")

settings = Settings()
