"""
Pruebas unitarias para los componentes SaaS (Hashing, Tokens JWT y Gestión de Billeteras).
"""
import pytest
from app.security.auth import hash_password, verify_password, create_access_token, decode_access_token


class TestSaaSAuth:
    """Pruebas del módulo de autenticación JWT y contraseñas."""

    def test_password_hashing_and_verification(self):
        pwd = "SecretPassword123"
        hashed = hash_password(pwd)
        
        assert hashed != pwd
        assert len(hashed) == 64  # SHA-256 hex string
        assert verify_password(pwd, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_jwt_token_creation_and_decoding(self):
        user_data = {"sub": 42, "email": "trader@example.com", "role": "USER", "plan": "PRO"}
        token = create_access_token(user_data)
        
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == 42
        assert decoded["email"] == "trader@example.com"
        assert decoded["plan"] == "PRO"

    def test_invalid_or_tampered_jwt_token(self):
        user_data = {"sub": 1, "email": "user@test.com"}
        token = create_access_token(user_data)
        
        # Alterar firma
        tampered_token = token[:-4] + "XXXX"
        assert decode_access_token(tampered_token) is None
