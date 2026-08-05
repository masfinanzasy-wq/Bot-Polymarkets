"""
Capa de Seguridad Integral para Polymarket M5 Bot.
Provee cifrado de datos (AES-256), encabezados de seguridad HTTP, limitador de tasa (Rate Limiting) y auditoría.
"""
from app.security.vault import EncryptionVault
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limiter import RateLimiterMiddleware

__all__ = [
    "EncryptionVault",
    "SecurityHeadersMiddleware",
    "RateLimiterMiddleware",
]
