"""Application configuration and environment loading."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_secret_file(path: str | Path | None) -> str | None:
    """Load a secret value from a mounted file path when configured."""
    if path is None:
        return None
    secret_path = Path(path).expanduser()
    if not secret_path.is_absolute():
        secret_path = (ROOT_DIR / secret_path).resolve()
    return secret_path.read_text(encoding="utf-8").strip() or None


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
    password_file: str | None = None
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20

    @model_validator(mode="after")
    def resolve_secret_file(self) -> "DatabaseSettings":
        """Allow the database password to be sourced from a mounted secret file."""
        if self.password_file:
            self.password = _read_secret_file(self.password_file) or self.password
        return self

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
    public_endpoint: str | None = None
    access_key: str = "minioadmin"
    access_key_file: str | None = None
    secret_key: str = "minioadmin"
    secret_key_file: str | None = None
    bucket: str = "documents"
    secure: bool = False
    public_secure: bool | None = None
    region: str | None = None
    templates_prefix: str = "templates"
    artifacts_prefix: str = "artifacts"
    cache_prefix: str = "cache"
    previews_prefix: str = "previews"
    presigned_url_expiry_seconds: int = 3600
    auto_create_bucket: bool = True

    @model_validator(mode="after")
    def resolve_secret_files(self) -> "StorageSettings":
        """Allow object-storage credentials to come from mounted secret files."""
        if self.access_key_file:
            self.access_key = _read_secret_file(self.access_key_file) or self.access_key
        if self.secret_key_file:
            self.secret_key = _read_secret_file(self.secret_key_file) or self.secret_key
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def public_base_url(self) -> str:
        """Return the base storage URL for the current protocol."""
        scheme = "https" if self.public_secure_value else "http"
        endpoint = self.public_endpoint or self.endpoint
        return f"{scheme}://{endpoint}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def public_secure_value(self) -> bool:
        """Return the effective secure flag for public download URLs."""
        return self.public_secure if self.public_secure is not None else self.secure


class RedisSettings(BaseModel):
    """Redis settings used by Celery broker and backend wiring."""

    model_config = ConfigDict(extra="forbid")

    host: str = "redis"
    port: int = 6379
    broker_db: int = 0
    result_db: int = 1
    password: str | None = None
    password_file: str | None = None

    @model_validator(mode="after")
    def resolve_secret_file(self) -> "RedisSettings":
        """Allow the Redis password to be sourced from a mounted secret file."""
        if self.password_file:
            self.password = _read_secret_file(self.password_file) or self.password
        return self

    def _auth_segment(self) -> str:
        """Return the auth prefix for Redis URLs."""
        return f":{self.password}@" if self.password else ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def broker_url(self) -> str:
        """Build the Celery broker URL."""
        return (
            f"redis://{self._auth_segment()}{self.host}:{self.port}/{self.broker_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def result_backend_url(self) -> str:
        """Build the Celery result backend URL."""
        return (
            f"redis://{self._auth_segment()}{self.host}:{self.port}/{self.result_db}"
        )


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
    jwt_secret_key_file: str | None = None
    jwt_algorithm: str = "HS256"
    issuer: str = "lean-generator-backend"
    audience: str = "lean-generator-clients"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    password_min_length: int = 8

    @model_validator(mode="after")
    def resolve_secret_file(self) -> "AuthSettings":
        """Allow the JWT signing key to be sourced from a mounted secret file."""
        if self.jwt_secret_key_file:
            self.jwt_secret_key = _read_secret_file(self.jwt_secret_key_file) or self.jwt_secret_key
        return self

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


class WorkerSettings(BaseModel):
    """Celery worker behavior for generation jobs."""

    model_config = ConfigDict(extra="forbid")

    queue_name: str = "document-generation"
    max_retries: int = 4
    retry_backoff_seconds: int = 15
    stale_job_timeout_seconds: int = 300
    stale_job_recovery_batch_size: int = 100
    result_expires_seconds: int = 3600
    maintenance_cleanup_interval_minutes: int = 60
    billing_cycle_interval_minutes: int = 60


class RetentionSettings(BaseModel):
    """Retention windows for generated data and operational cleanup."""

    model_config = ConfigDict(extra="forbid")

    generated_artifact_retention_days: int = 30
    failed_job_retention_days: int = 14
    audit_log_retention_days: int = 90
    temp_data_retention_hours: int = 24
    cleanup_batch_size: int = 250


class ApiKeySettings(BaseModel):
    """API-key auth, scopes, and quota settings for public SaaS routes."""

    model_config = ConfigDict(extra="forbid")

    header_name: str = "X-API-Key"
    public_prefix: str = "/public"
    requests_per_minute_per_key: int = 120
    requests_per_minute_per_org: int = 600
    requests_per_day_per_key: int = 5000
    requests_per_day_per_org: int = 50000


class ObservabilitySettings(BaseModel):
    """Structured logging, metrics, and error-reporting settings."""

    model_config = ConfigDict(extra="forbid")

    sentry_dsn: str | None = None
    sentry_dsn_file: str | None = None
    sentry_traces_sample_rate: float = 0.0
    request_id_header: str = "X-Request-ID"
    correlation_id_header: str = "X-Correlation-ID"

    @model_validator(mode="after")
    def resolve_secret_file(self) -> "ObservabilitySettings":
        """Allow the Sentry DSN to be sourced from a mounted secret file."""
        if self.sentry_dsn_file:
            self.sentry_dsn = _read_secret_file(self.sentry_dsn_file) or self.sentry_dsn
        return self


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
    redis: RedisSettings = Field(default_factory=RedisSettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)
    api_keys: ApiKeySettings = Field(default_factory=ApiKeySettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)

    @model_validator(mode="after")
    def validate_production_secret_management(self) -> "Settings":
        """Require mounted secrets for production deployments."""
        if not self.app.is_production:
            return self

        required_secret_files = {
            "DATABASE__PASSWORD_FILE": self.database.password_file,
            "STORAGE__ACCESS_KEY_FILE": self.storage.access_key_file,
            "STORAGE__SECRET_KEY_FILE": self.storage.secret_key_file,
            "AUTH__JWT_SECRET_KEY_FILE": self.auth.jwt_secret_key_file,
        }
        missing = [name for name, value in required_secret_files.items() if not value]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                "Production deployments must provide mounted secret files for "
                f"{joined}."
            )
        if self.redis.password and not self.redis.password_file:
            raise ValueError(
                "Production Redis passwords must be provided through REDIS__PASSWORD_FILE."
            )
        if self.observability.sentry_dsn and not self.observability.sentry_dsn_file:
            raise ValueError(
                "Production Sentry DSNs must be provided through "
                "OBSERVABILITY__SENTRY_DSN_FILE."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
