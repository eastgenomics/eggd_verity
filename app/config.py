from decouple import config


def parse_bool(value: str, setting_name: str) -> bool:
    """Parse a strict environment-backed boolean setting."""
    normalized_value = value.strip().lower()
    if normalized_value in {"true", "1", "yes", "on"}:
        return True
    if normalized_value in {"false", "0", "no", "off"}:
        return False
    raise ValueError(
        f"{setting_name} must be one of true/false, 1/0, yes/no, or on/off; "
        f"received {value!r}"
    )


class Settings:
    AUTH_ENABLED: bool = parse_bool(
        config("VERITY_AUTH_ENABLED", default="true"), "VERITY_AUTH_ENABLED"
    )
    USERNAME: str = config("VERITY_USERNAME", default="")
    PASSWORD: str = config("VERITY_PASSWORD", default="")
    SECRET_KEY: str = config("VERITY_SECRET_KEY")
    SLACK_WEBHOOK_URL: str = config("SLACK_WEBHOOK_URL", default="")

    if AUTH_ENABLED and (not USERNAME.strip() or not PASSWORD.strip()):
        raise ValueError(
            "VERITY_USERNAME and VERITY_PASSWORD are required when "
            "VERITY_AUTH_ENABLED is enabled"
        )


settings = Settings()
