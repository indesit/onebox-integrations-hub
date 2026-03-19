from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore',
    )

    # OneBox CRM
    onebox_domain: str = ""
    onebox_login: str = ""
    onebox_api_key: str = ""
    onebox_webhook_secret: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # SendPulse
    sendpulse_client_id: str = ""
    sendpulse_client_secret: str = ""

    # Google Sheets
    google_service_account_json: str = ""

    # Infrastructure
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./data/hub.db"

    # App
    log_level: str = "INFO"
    debug: bool = False
    
    # BAF
    baf_user: str = "odata.user"
    baf_password: str = "123123"
    
    # Sync
    sync_interval_seconds: int = 60
    
    @property
    def onebox_url(self) -> str:
        return f"https://{self.onebox_domain}"


settings = Settings()
