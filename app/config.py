from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )

    USERNAME: str
    PASSWORD: str
    SECRET_KEY: str


try:
    settings = Settings()
    print("Settings loaded successfully from .env file.")
except ValidationError as e:
    print("Error loading settings. Make sure your .env file is correctly set up.")
    raise e
