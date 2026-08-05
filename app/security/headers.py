"""
Middleware de encabezados de seguridad HTTP para protección de ataques Web (XSS, Clickjacking, MIME sniffing, HSTS).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Inyecta encabezados de seguridad modernos en todas las respuestas HTTP de FastAPI.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        
        # Prevenir Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevenir MIME Type Sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Habilitar filtro XSS en navegadores
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Política de Referrer estricta
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS - Forzar HTTPS por 1 año
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (CSP)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: https:;"
        )

        return response
