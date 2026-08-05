"""
Módulo de configuración centralizada con perfiles de entorno y validación de seguridad.
"""
from app.config.settings import Settings, settings
from app.config.profiles import DevelopmentSettings, TestingSettings, ProductionSettings, get_settings_for_env
from app.config.validator import ConfigValidator

__all__ = [
    "Settings",
    "settings",
    "DevelopmentSettings",
    "TestingSettings",
    "ProductionSettings",
    "get_settings_for_env",
    "ConfigValidator",
]
