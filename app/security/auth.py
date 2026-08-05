"""
Módulo de Autenticación de Usuarios SaaS: Hashing de Contraseñas y Gestión de Tokens JWT.
"""
import hashlib
import hmac
import time
import json
import base64
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "polymarket_saas_jwt_secret_key_2026"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = 86400 * 7  # 7 días de validez

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Genera un hash seguro de la contraseña del usuario mediante HMAC-SHA256 con salt."""
    salt = b"polymarket_saas_salt_2026"
    return hmac.new(salt, password.encode('utf-8'), hashlib.sha256).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con el hash almacenado."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
    """Crea un token JWT firmado de forma segura."""
    payload = data.copy()
    expire = time.time() + (expires_delta or TOKEN_EXPIRATION_SECONDS)
    payload["exp"] = int(expire)
    payload["iat"] = int(time.time())

    # Formatear Header y Payload en Base64URL
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    signature_base = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signature_base, hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica y verifica la firma y validez de un token JWT."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts

        # Recalcular firma
        signature_base = f"{header_b64}.{payload_b64}".encode()
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY.encode(), signature_base, hashlib.sha256).digest()
        ).decode().rstrip("=")

        if not hmac.compare_digest(signature_b64, expected_sig):
            return None

        # Decodificar payload
        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload).decode())

        if payload.get("exp", 0) < time.time():
            return None  # Token expirado

        return payload
    except Exception:
        return None


async def get_current_user_payload(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Dict[str, Any]:
    """Dependency para FastAPI que extrae y valida el usuario autenticado a partir del Bearer Token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida. Token Bearer ausente.",
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido o expirado.",
        )
    return payload
