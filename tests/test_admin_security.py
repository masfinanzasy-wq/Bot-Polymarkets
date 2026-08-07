"""
Pruebas de Seguridad y Control de Acceso (RBAC) para el Panel de Administración.
"""
import pytest
from app.security.auth import create_access_token
from app.api.admin_routes import verify_admin_access
from fastapi import HTTPException


def test_admin_access_allowed_for_admin_role():
    token_payload = {"sub": 1, "email": "admin@polymarket.com", "role": "ADMIN", "plan": "WHALE"}
    # No debe lanzar excepción
    import asyncio
    res = asyncio.run(verify_admin_access(user_payload=token_payload))
    assert res["role"] == "ADMIN"


def test_admin_access_denied_for_regular_user():
    token_payload = {"sub": 2, "email": "user@gmail.com", "role": "USER", "plan": "PRO"}
    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(verify_admin_access(user_payload=token_payload))
    assert exc_info.value.status_code == 403
