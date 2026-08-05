"""
Validador de seguridad para credenciales y parámetros críticos de la aplicación.
"""
import re
from typing import Optional
from app.config.settings import Settings
from app.logger.logger import sys_logger


class ConfigValidator:
    """
    Verifica que la configuración sea coherente y segura antes de arrancar el bot.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """
        Ejecuta todas las validaciones. Retorna True si el sistema puede arrancar.
        """
        self._check_trading_mode()
        self._check_private_key()
        self._check_database_url()
        self._check_risk_parameters()
        self._check_api_endpoints()

        for warning in self.warnings:
            sys_logger.warning(f"CONFIG WARNING: {warning}")

        if self.errors:
            for error in self.errors:
                sys_logger.error(f"CONFIG ERROR: {error}")
            return False

        sys_logger.info(f"Configuracion validada exitosamente para entorno [{self.settings.ENVIRONMENT.upper()}]")
        return True

    def _check_trading_mode(self) -> None:
        if not self.settings.PAPER_TRADING:
            self.warnings.append(
                "PAPER_TRADING=false. El bot operara con DINERO REAL. Asegurate de tener "
                "la clave privada de Polygon configurada y haber probado exhaustivamente en modo sombra."
            )
        else:
            sys_logger.info("Modo de ejecucion: PAPER TRADING (Modo Sombra) activo.")

    def _check_private_key(self) -> None:
        key = self.settings.POLYMARKET_PRIVATE_KEY
        # Solo validar key si no estamos en modo Paper Trading
        if not self.settings.PAPER_TRADING:
            if not key or key == "your_polygon_private_key_here":
                self.errors.append(
                    "POLYMARKET_PRIVATE_KEY no configurada. Es obligatoria para operar con dinero real."
                )
            elif not re.match(r"^0x[0-9a-fA-F]{64}$", key):
                self.errors.append(
                    "POLYMARKET_PRIVATE_KEY tiene formato invalido. Debe ser un string hex de 64 caracteres con prefijo 0x."
                )

    def _check_database_url(self) -> None:
        url = self.settings.DATABASE_URL
        if not url:
            self.errors.append("DATABASE_URL no configurada.")
        elif "your_password" in url or "CHANGE_ME" in url.upper():
            self.warnings.append("DATABASE_URL parece contener credenciales placeholder. Verifica el archivo .env.")

    def _check_risk_parameters(self) -> None:
        if self.settings.MAX_POSITION_SIZE_USD <= 0:
            self.errors.append("MAX_POSITION_SIZE_USD debe ser un valor positivo mayor a 0.")
        if self.settings.MAX_DAILY_LOSS_USD <= 0:
            self.errors.append("MAX_DAILY_LOSS_USD debe ser un valor positivo mayor a 0.")
        if self.settings.MIN_EXPECTED_VALUE <= 0 or self.settings.MIN_EXPECTED_VALUE >= 1:
            self.errors.append("MIN_EXPECTED_VALUE debe estar entre 0.0 y 1.0 (ej. 0.05 para EV minimo del 5%).")
        if self.settings.MAX_POSITION_SIZE_USD > 500:
            self.warnings.append(
                f"MAX_POSITION_SIZE_USD=${self.settings.MAX_POSITION_SIZE_USD:.2f} es un valor elevado. "
                "Verifica que corresponda a tu capital disponible y tolerancia al riesgo."
            )

    def _check_api_endpoints(self) -> None:
        if "stream.binance.com" not in self.settings.BINANCE_WS_URL:
            self.warnings.append("BINANCE_WS_URL no apunta al endpoint oficial de Binance.")
        if "polymarket" not in self.settings.POLYMARKET_HOST.lower():
            self.warnings.append("POLYMARKET_HOST no apunta a un dominio de Polymarket reconocido.")
