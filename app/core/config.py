import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

DEFAULT_CONFIG = {
    "API_KEY": "",
    "LLM_PROVIDER": "gemini",
    "MODEL": "gemini-flash-lite-latest",
}

def create_default_config(file_path: str):
    path = Path(file_path)

    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"Created default config.json: {path}")

class Settings:
    def __init__(self):
        self.PROJECT_NAME: str = "RedPatch"
        self.VERSION: str = "v0.8.7"

        self.CONFIG_JSON: str = os.getenv("CONFIG_JSON", "core/config.json").strip()
        self.ARCHIVE_DIR: str = os.getenv("ARCHIVE_DIR", "labs/archives").strip()

        self.LLM_PROVIDER: str = self.get_config_json("LLM_PROVIDER", "gemini")
        self.API_KEY: str = self.get_config_json("API_KEY", "")
        self.MODEL: str = self.get_config_json("MODEL", "gemini-flash-lite-latest")

    def get_options(self):
        return {
            "LLM_PROVIDER" : self.LLM_PROVIDER,
            "API_KEY" : self.API_KEY,
            "MODEL" : self.MODEL
        }

    def set_options(self, config:dict):
        self.set_config_json(config)
        self.LLM_PROVIDER = config.get("LLM_PROVIDER", "")
        self.API_KEY = config.get("API_KEY", "")
        self.MODEL = config.get("MODEL", "")

    def validate(self):
        if not self.API_KEY:
            raise ValueError("API_KEY is not configured.")

        self.validate_config()

    def validate_config(self):
        if not os.path.exists(self.CONFIG_JSON) or not os.path.isfile(self.CONFIG_JSON):
            create_default_config(self.CONFIG_JSON)

    def get_config_json(self, key:str, default:str):
        self.validate_config()

        with open(self.CONFIG_JSON, "r") as f:
            json_config = json.load(f)
            try:
                if not key:
                    raise ValueError("key is required")
                return json_config[key]

            except KeyError:
                if not default:
                    raise KeyError(f"Key {key} not found in config.json")
                return default

    def set_config_json(self, data: dict):
        with open(self.CONFIG_JSON, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

settings = Settings()
