"""
Configuración centralizada cargada dinámicamente desde variables de entorno (.env) mediante Pydantic Settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General
    APP_NAME: str = "Polymarket-M5-Bot"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    PAPER_TRADING: bool = True
    DASHBOARD_ACCESS_KEY: str = "polymarket2026"
    TELEGRAM_BOT_TOKEN: str = ""

    # Binance Config
    BINANCE_WS_URL: str = "wss://stream.binance.com:9443/ws"
    BINANCE_REST_URL: str = "https://api.binance.com"
    DEFAULT_SYMBOL: str = "btcusdt"

    # Polymarket Config
    POLYMARKET_HOST: str = "https://clob.polymarket.com"
    POLYMARKET_WS_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    POLYMARKET_CHAIN_ID: int = 137
    POLYMARKET_PRIVATE_KEY: str = ""

    # Database
    POSTGRES_USER: str = "bot_user"
    POSTGRES_PASSWORD: str = "bot_password_123"
    POSTGRES_DB: str = "polymarket_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://bot_user:bot_password_123@localhost:5432/polymarket_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Risk Parameters
    MAX_POSITION_SIZE_USD: float = 50.0
    MAX_DAILY_LOSS_USD: float = 200.0
    MIN_EXPECTED_VALUE: float = 0.05


# Instancia global de configuración
settings = Settings()
