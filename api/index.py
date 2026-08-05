"""
Punto de entrada para Vercel Serverless Functions.
Vercel detecta automáticamente los archivos en api/ sin necesidad de la propiedad heredada 'builds'.
"""
from app.api.server import app

# Exportar la instancia FastAPI para el runtime de Vercel Serverless
__all__ = ["app"]
