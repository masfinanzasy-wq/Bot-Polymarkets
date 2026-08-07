"""
Punto de entrada para Vercel Serverless Functions.
"""
import sys
from pathlib import Path

# Añadir el directorio raíz al sys.path para resolver el módulo 'app' en Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.server import app

# Exportar la instancia FastAPI para el runtime de Vercel Serverless
__all__ = ["app"]
