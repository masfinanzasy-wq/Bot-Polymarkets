"""
Pruebas unitarias del sistema de configuración: perfiles y validador de seguridad.
"""
import pytest
from app.config import get_settings_for_env, ConfigValidator


class TestConfigProfiles:
    """Pruebas de los perfiles de entorno dinámicos."""

    def test_development_profile(self):
        s = get_settings_for_env("development")
        assert s.ENVIRONMENT == "development"
        assert s.LOG_LEVEL == "DEBUG"
        assert s.PAPER_TRADING is True

    def test_testing_profile(self):
        s = get_settings_for_env("testing")
        assert s.ENVIRONMENT == "testing"
        assert "sqlite" in s.DATABASE_URL
        assert s.MAX_POSITION_SIZE_USD == 5.0

    def test_production_profile(self):
        s = get_settings_for_env("production")
        assert s.ENVIRONMENT == "production"
        assert s.LOG_LEVEL == "INFO"
        assert s.PAPER_TRADING is True  # Protección por defecto

    def test_unknown_env_defaults_to_development(self):
        s = get_settings_for_env("staging_xyz")
        assert s.ENVIRONMENT == "development"


class TestConfigValidator:
    """Pruebas del validador de seguridad de configuración."""

    def test_valid_paper_trading_config_passes(self):
        s = get_settings_for_env("development")
        validator = ConfigValidator(s)
        assert validator.validate() is True

    def test_invalid_private_key_fails_in_live_mode(self):
        s = get_settings_for_env("production")
        s.PAPER_TRADING = False
        s.POLYMARKET_PRIVATE_KEY = "not_a_valid_key"
        validator = ConfigValidator(s)
        assert validator.validate() is False

    def test_negative_max_position_fails(self):
        s = get_settings_for_env("development")
        s.MAX_POSITION_SIZE_USD = -10.0
        validator = ConfigValidator(s)
        assert validator.validate() is False

    def test_ev_threshold_out_of_range_fails(self):
        s = get_settings_for_env("development")
        s.MIN_EXPECTED_VALUE = 1.5  # Fuera del rango 0.0-1.0
        validator = ConfigValidator(s)
        assert validator.validate() is False
