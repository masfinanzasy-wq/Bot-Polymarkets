"""
Prueba unitaria del sistema de configuración: perfiles de entorno y validador de seguridad.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.config import get_settings_for_env, ConfigValidator
from app.logger.logger import sys_logger


def test_config_profiles():
    sys_logger.info("=== CASO 1: Perfil Development ===")
    dev_settings = get_settings_for_env("development")
    assert dev_settings.ENVIRONMENT == "development"
    assert dev_settings.LOG_LEVEL == "DEBUG"
    assert dev_settings.PAPER_TRADING is True
    sys_logger.info(f"Environment: {dev_settings.ENVIRONMENT} | Paper Trading: {dev_settings.PAPER_TRADING} | Log Level: {dev_settings.LOG_LEVEL}")

    sys_logger.info("\n=== CASO 2: Perfil Testing ===")
    test_settings = get_settings_for_env("testing")
    assert test_settings.ENVIRONMENT == "testing"
    assert test_settings.PAPER_TRADING is True
    assert "sqlite" in test_settings.DATABASE_URL
    sys_logger.info(f"Environment: {test_settings.ENVIRONMENT} | DB URL: {test_settings.DATABASE_URL}")

    sys_logger.info("\n=== CASO 3: Perfil Production ===")
    prod_settings = get_settings_for_env("production")
    assert prod_settings.ENVIRONMENT == "production"
    assert prod_settings.LOG_LEVEL == "INFO"
    assert prod_settings.PAPER_TRADING is True  # Proteccion por defecto
    sys_logger.info(f"Environment: {prod_settings.ENVIRONMENT} | Paper Trading: {prod_settings.PAPER_TRADING} (proteccion activa)")

    sys_logger.info("\n=== CASO 4: Validacion de Configuracion en Development ===")
    validator = ConfigValidator(dev_settings)
    result = validator.validate()
    assert result is True
    sys_logger.info(f"Validacion de configuracion: {'APROBADA' if result else 'FALLIDA'}")

    sys_logger.info("\n=== CASO 5: Deteccion de error en configuracion critica ===")
    prod_settings_unsafe = get_settings_for_env("production")
    prod_settings_unsafe.PAPER_TRADING = False  # Simular modo real
    prod_settings_unsafe.POLYMARKET_PRIVATE_KEY = "invalid_key"  # Simular key invalida
    validator_unsafe = ConfigValidator(prod_settings_unsafe)
    result_unsafe = validator_unsafe.validate()
    assert result_unsafe is False  # Debe fallar
    sys_logger.info(f"Deteccion de configuracion insegura: {'DETECTADA correctamente' if not result_unsafe else 'ERROR: no detectada'}")

    sys_logger.info("\nTodas las pruebas de configuracion pasaron exitosamente!")


if __name__ == "__main__":
    test_config_profiles()
