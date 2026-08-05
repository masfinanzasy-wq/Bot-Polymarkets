"""
Punto de entrada principal del Bot de Trading.
Inicializa configuración, valida el entorno y orquesta todos los componentes.
"""
import asyncio
import sys
import os

# Forzar UTF-8 en consola de Windows antes de importar cualquier otro módulo
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import settings, ConfigValidator, get_settings_for_env
from app.logger.logger import sys_logger


async def main() -> None:
    # 1. Cargar perfil de entorno
    env = os.getenv("ENVIRONMENT", "development")
    active_settings = get_settings_for_env(env)
    sys_logger.info(f"Iniciando Polymarket M5 Bot | Entorno: {active_settings.ENVIRONMENT.upper()}")

    # 2. Validar configuración antes de arrancar
    validator = ConfigValidator(active_settings)
    if not validator.validate():
        sys_logger.critical("Configuracion invalida. El bot no puede arrancar. Revisa los errores anteriores.")
        sys.exit(1)

    sys_logger.info(f"Bot de Trading listo. Paper Trading: {active_settings.PAPER_TRADING}")
    # La integración completa del loop de trading principal se construirá en fases siguientes.


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys_logger.info("Bot detenido manualmente por el usuario.")
        sys.exit(0)
