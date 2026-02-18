"""
Configuration management using Pydantic Settings.
Follows Single Responsibility Principle - handles ONLY configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    debug: bool = True

    # Database (PostgreSQL)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vinschool_ai"
    postgres_user: str = "vinschool"
    postgres_password: str = "vinschool_password"

    @property
    def database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct sync database URL for Alembic."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Milvus (Vector Database)
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection_prefix: str = "vinschool"

    # LLM API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # For Gemini

    # Default LLM Provider
    default_provider: str = "openai"  # openai, google, anthropic

    # Embedding Configuration
    embedding_provider: str = "google"  # openai or google
    embedding_model: str = "models/text-embedding-004"
    embedding_dimension: int = 768  # text-embedding-004 with output_dimensionality=768

    # Agent Configuration
    default_llm_model: str = "gpt-4-turbo-preview"  # or gemini-1.5-pro, claude-3-opus
    grading_llm_model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_tokens: int = 2000

    # File Upload Configuration
    max_upload_size_mb: int = 50
    allowed_extensions: str = ".pdf,.docx,.pptx,.jpg,.jpeg,.png"

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Parse allowed extensions into list."""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    # Workflow Configuration
    enable_auto_grading: bool = True
    enable_question_routing: bool = True
    teacher_escalation_threshold: float = 0.6

    # Notification Configuration
    # Email (SMTP) settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    TEACHER_EMAIL: str = "teacher@vinschool.edu.vn"  # Teacher email for escalations
    NOTIFICATION_SENDER_EMAIL: str = "ai-assistant@vinschool.edu.vn"
    NOTIFICATION_SENDER_NAME: str = "Vinschool AI Assistant"

    # Google Chat settings
    GOOGLE_CHAT_WEBHOOK_URL: Optional[str] = None

    # Google Chat Pub/Sub settings (for bidirectional chat — @mention based)
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = None
    GOOGLE_CHAT_PUBSUB_SUBSCRIPTION: Optional[str] = None  # e.g. "projects/my-proj/subscriptions/chat-sub"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None  # Path to service account JSON key
    GOOGLE_CHAT_SPACE_ID: Optional[str] = None  # e.g. "spaces/AAAAxxxxxx"

    # Chat debounce settings
    CHAT_DEBOUNCE_SECONDS: float = 3.0

    # Zalo settings
    ZALO_OA_ACCESS_TOKEN: Optional[str] = None

    # Notification behavior
    ENABLE_EMAIL_NOTIFICATIONS: bool = False
    ENABLE_GOOGLE_CHAT_NOTIFICATIONS: bool = False
    ENABLE_ZALO_NOTIFICATIONS: bool = False
    NOTIFICATION_TIMEOUT: int = 30  # seconds

    # Low grade alert threshold (score out of max_score)
    LOW_GRADE_THRESHOLD: float = 7.0

    # Security
    secret_key: str = "change_me_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


# Global settings instance (Singleton pattern)
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
