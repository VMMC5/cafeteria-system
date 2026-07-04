from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración vía variables de entorno (.env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días
    ADMIN_CORREO: str = "admin@cafeteria.local"
    ADMIN_PASSWORD: str = "cambiar_en_local"
    ADMIN_NOMBRE: str = "Administrador"


settings = Settings()
