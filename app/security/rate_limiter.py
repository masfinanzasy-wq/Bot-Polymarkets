"""
Limitador de tasa de peticiones (Rate Limiter) por IP con ventana deslizante para mitigar ataques DDoS y fuerza bruta.
"""
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, status
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger.logger import sys_logger


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware que restringe la cantidad máxima de peticiones por minuto por cliente IP.
    """

    def __init__(self, app, max_requests_per_minute: int = 120, auth_max_requests: int = 5):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.auth_max_requests = auth_max_requests
        self.requests_store: Dict[str, List[float]] = defaultdict(list)
        self.auth_store: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60.0  # Ventana de 1 minuto (60s)

        path = request.url.path

        # Limitar intentos de login / verificacion de clave de acceso (máximo 5 por minuto)
        if "/api/v1/auth/verify-key" in path and request.method == "POST":
            history = [t for t in self.auth_store[client_ip] if t > window_start]
            self.auth_store[client_ip] = history
            if len(history) >= self.auth_max_requests:
                sys_logger.warning(f"RATE LIMIT BREACH: IP {client_ip} superó el límite de intentos de login.")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Demasiados intentos de autenticación. Intenta de nuevo en 1 minuto."}
                )
            self.auth_store[client_ip].append(now)

        # Limitar peticiones generales (máximo 120 por minuto)
        history = [t for t in self.requests_store[client_ip] if t > window_start]
        self.requests_store[client_ip] = history
        if len(history) >= self.max_requests:
            sys_logger.warning(f"RATE LIMIT BREACH: IP {client_ip} superó {self.max_requests} req/min.")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Límite de tasa de peticiones alcanzado. Por favor, disminuye la frecuencia de solicitudes."}
            )
        self.requests_store[client_ip].append(now)

        return await call_next(request)
