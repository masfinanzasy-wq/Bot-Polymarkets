from typing import ClassVar
from pydantic_settings import SettingsConfigDict
from app.config.settings import Settings


class DevelopmentSettings(Settings):
    """
    Perfil de configuración para entorno de Desarrollo local.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    PAPER_TRADING: bool = True

    def model_post_init(self, __context):
        # Forzar DEBUG en desarrollo independientemente del .env
        object.__setattr__(self, "ENVIRONMENT", "development")
        object.__setattr__(self, "LOG_LEVEL", "DEBUG")


class TestingSettings(Settings):
    """
    Perfil de configuración para entorno de Pruebas (CI/CD).
    Usa SQLite en memoria para evitar dependencias externas.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "testing"
    PAPER_TRADING: bool = True
    MAX_POSITION_SIZE_USD: float = 5.0
    MAX_DAILY_LOSS_USD: float = 20.0

    def model_post_init(self, __context):
        object.__setattr__(self, "ENVIRONMENT", "testing")
        object.__setattr__(self, "LOG_LEVEL", "WARNING")
        object.__setattr__(self, "DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        object.__setattr__(self, "REDIS_URL", "redis://localhost:6379/1")
        object.__setattr__(self, "MAX_POSITION_SIZE_USD", 5.0)
        object.__setattr__(self, "MAX_DAILY_LOSS_USD", 20.0)


class ProductionSettings(Settings):
    """
    Perfil de configuración para entorno de Producción.
    PAPER_TRADING = False debe configurarse explícitamente en el .env de producción.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "production"
    PAPER_TRADING: bool = True  # Seguridad: por defecto siempre arranca en shadow mode

    def model_post_init(self, __context):
        object.__setattr__(self, "ENVIRONMENT", "production")
        object.__setattr__(self, "LOG_LEVEL", "INFO")


def get_settings_for_env(env: str = "development") -> Settings:
    """
    Factory que retorna el perfil de configuración apropiado según el entorno activo.
    """
    profiles = {
        "development": DevelopmentSettings,
        "testing": TestingSettings,
        "production": ProductionSettings,
    }
    profile_class = profiles.get(env.lower(), DevelopmentSettings)
    return profile_class()
