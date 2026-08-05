"""
Módulo de cifrado simétrico AES-256 (Fernet) para la protección de claves privadas y secretos.
"""
import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.logger.logger import sys_logger


class EncryptionVault:
    """
    Bóveda de cifrado seguro para claves privadas de Polygon y credenciales de API.
    """

    def __init__(self, master_secret: Optional[str] = None):
        secret = master_secret or os.getenv("ENCRYPTION_MASTER_KEY", "polymarket_default_secret_key_2026")
        salt = b"polymarket_m5_salt_bytes_2026"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        self.cipher = Fernet(key)

    def encrypt(self, plain_text: str) -> str:
        """
        Cifra un texto plano y devuelve el token cifrado en formato base64.
        """
        if not plain_text:
            return ""
        encrypted_bytes = self.cipher.encrypt(plain_text.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        Descifra un token cifrado y devuelve el texto plano original.
        """
        if not encrypted_text:
            return ""
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            sys_logger.error(f"Error en descifrado de bóveda: {e}")
            raise ValueError("No se pudo descifrar el texto especificado. Clave maestra inválida.")
