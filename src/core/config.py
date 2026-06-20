from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Private-School-Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # ─── Auth / JWT ──────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_HOURS: int = 1

    # ─── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ─── CORS ────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ─── Email (via Vercel relay) ─────────────────────────────────────────────
    VERCEL_EMAIL_URL: str = ""
    EMAIL_API_SECRET: str = ""

    # ─── Seed defaults ───────────────────────────────────────────────────────
    OWNER_EMAIL: str = "owner@school.dz"
    OWNER_PASSWORD: str = "Owner@School2026!"
    OWNER_FIRST_NAME: str = "Owner"
    OWNER_LAST_NAME: str = "Account"

    # ─── Cloudinary ──────────────────────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_URL: str = ""

    # ─── Misc ─────────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    REDIS_URL: str = "redis://localhost:6379/0"
    RESEND_API_KEY: str = ""
    CRON_SECRET: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
