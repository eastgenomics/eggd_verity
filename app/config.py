from decouple import config
from data.utils.secrets import load_secrets

#secrets = load_secrets("verity/prod/app") TODO: setup secret manager

class Settings:
    USERNAME: str = config("VERITY_USERNAME")
    PASSWORD: str = config("VERITY_PASSWORD")
    SECRET_KEY: str = config("VERITY_SECRET_KEY")
    SLACK_WEBHOOK_URL: str = config("SLACK_WEBHOOK_URL", default="")
    
settings = Settings()   