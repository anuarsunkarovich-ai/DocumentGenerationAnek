"""Application configuration and environment loading."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class AppSettings(BaseModel):
    """HTTP application settings."""

    model_config = ConfigDict(extra="forbid")

    name: str = "Lean Generator Backend"
    version: str = "0.1.0"
    description: str = "Template-driven backend for document generation."
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @property
    def is_production(self) -> bool:
        """Return whether the application is running in production mode."""
        return self.environment.lower() == "production"


class DatabaseSettings(BaseModel):
    """Database connectivity settings."""

    model_config = ConfigDict(extra="forbid")

    host: str = "db"
    port: int = 5432
    name: str = "lean_generator"
    user: str = "postgres"
    password: str = "postgres"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        """Build the async SQLAlchemy database URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class StorageSettings(BaseModel):
    """Object storage settings for templates and generated artifacts."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str = "minio:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "documents"
    secure: bool = False
    region: str | None = None
    templates_prefix: str = "templates"
    artifacts_prefix: str = "artifacts"
    cache_prefix: str = "cache"
    previews_prefix: str = "previews"
    presigned_url_expiry_seconds: int = 3600
    auto_create_bucket: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def public_base_url(self) -> str:
        """Return the base storage URL for the current protocol."""
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}"


class GenerationSettings(BaseModel):
    """Generation-time limits and behavior settings."""

    model_config = ConfigDict(extra="forbid")

    cache_ttl_hours: int = 24
    job_timeout_seconds: int = 180
    max_upload_size_mb: int = 25
    max_template_variables: int = 250
    max_document_blocks: int = 150
    max_table_rows: int = 500
    max_image_size_mb: int = 10
    max_artifacts_per_job: int = 4
    preview_enabled: bool = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert the upload size limit to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_image_size_bytes(self) -> int:
        """Convert the image size limit to bytes."""
        return self.max_image_size_mb * 1024 * 1024


class AuthSettings(BaseModel):
    """Authentication and token settings."""

    model_config = ConfigDict(extra="forbid")

    jwt_secret_key: str = "change-this-in-production-32-byte-key"
    jwt_algorithm: str = "HS256"
    issuer: str = "lean-generator-backend"
    audience: str = "lean-generator-clients"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    password_min_length: int = 8

    @computed_field  # type: ignore[prop-decorator]
    @property
    def access_token_ttl_seconds(self) -> int:
        """Return the access-token lifetime in seconds."""
        return self.access_token_ttl_minutes * 60

    @computed_field  # type: ignore[prop-decorator]
    @property
    def refresh_token_ttl_seconds(self) -> int:
        """Return the refresh-token lifetime in seconds."""
        return self.refresh_token_ttl_days * 24 * 60 * 60


class PathsSettings(BaseModel):
    """Local filesystem paths used by the application."""

    model_config = ConfigDict(extra="forbid")

    root_dir: Path = ROOT_DIR
    templates_dir: Path = ROOT_DIR / "data" / "templates"
    artifacts_dir: Path = ROOT_DIR / "data" / "artifacts"
    temp_dir: Path = ROOT_DIR / "data" / "tmp"


class Settings(BaseSettings):
    """Top-level application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
