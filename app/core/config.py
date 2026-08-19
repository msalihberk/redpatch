import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "RedPatch"
    VERSION: str = "v0.4.4"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").strip()
    API_KEY: str = (os.getenv("API_KEY") or "").strip()
    MODEL: str = os.getenv("MODEL", "gemini-flash-lite-latest").strip()
    APP_ENV:str = os.getenv("APP_ENV", "dev").strip()
    # Keep downloaded lab packages next to the manifest by default.  This is
    # deliberately a host path as Docker receives the archive through `docker load`.
    ARCHIVE_DIR: str = os.getenv(
        "ARCHIVE_DIR", str(Path(__file__).resolve().parents[1] / "labs" / "archives")
    ).strip()

    def validate(self):
        if not self.API_KEY:
            raise ValueError("API_KEY is not configured.")

settings = Settings()
