"""
Configuración centralizada de logs mediante Loguru con formateo y rotación automática.
"""
import sys
from pathlib import Path
from loguru import logger
from app.config.settings import settings

# Directorio de logs
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Remover handler por defecto de loguru
logger.remove()

# Configurar salida por consola con colores
logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# Configurar salida a archivo rotativo diario
logger.add(
    LOGS_DIR / "bot_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="00:00",
    retention="14 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,  # Asíncrono y thread-safe
)

# Exportar logger configurado
sys_logger = logger
