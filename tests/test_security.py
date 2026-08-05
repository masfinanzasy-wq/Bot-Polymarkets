"""
Pruebas unitarias para la Capa de Seguridad (Bóveda AES-256, Headers HTTP y Rate Limiting).
"""
import pytest
from app.security import EncryptionVault


class TestEncryptionVault:
    """Pruebas de la Bóveda de Cifrado AES-256."""

    def test_encrypt_and_decrypt_secret(self):
        vault = EncryptionVault(master_secret="test_master_secret_2026")
        original_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        encrypted = vault.encrypt(original_key)
        assert encrypted != original_key
        assert len(encrypted) > 20

        decrypted = vault.decrypt(encrypted)
        assert decrypted == original_key

    def test_empty_string_handling(self):
        vault = EncryptionVault()
        assert vault.encrypt("") == ""
        assert vault.decrypt("") == ""

    def test_invalid_decryption_key_raises_error(self):
        vault1 = EncryptionVault(master_secret="secret_one")
        vault2 = EncryptionVault(master_secret="secret_two")

        encrypted = vault1.encrypt("my_private_key")
        with pytest.raises(ValueError):
            vault2.decrypt(encrypted)
