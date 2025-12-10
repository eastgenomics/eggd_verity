from decouple import config

class Settings:
    USERNAME: str = config("VERITY_USERNAME")
    PASSWORD: str = config("VERITY_PASSWORD")
    SECRET_KEY: str = config("VERITY_SECRET_KEY")
    SLACK_WEBHOOK_URL: str = config("SLACK_WEBHOOK_URL", default="")
    
settings = Settings()   