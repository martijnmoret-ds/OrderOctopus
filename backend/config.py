"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    environment: str = "development"
    debug: bool = True
    app_name: str = "OrderOctopus"
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    supabase_url: str
    supabase_key: str
    supabase_service_key: str

    # Facebook Messenger
    facebook_page_access_token: str
    facebook_verify_token: str
    facebook_app_secret: str

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "anthropic"

    # Stripe
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str

    # Application Settings
    default_venue_language: str = "en"
    max_free_menu_parses: int = 3
    default_free_credits: int = 25
    credits_per_order: float = 1.0
    credits_per_rejection: float = 0.5
    credits_per_menu_import: int = 15

    # Logging
    log_level: str = "INFO"


settings = Settings()
