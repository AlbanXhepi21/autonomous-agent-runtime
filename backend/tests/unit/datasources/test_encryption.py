"""Envelope encryption for a stored data source password."""

import pytest
from cryptography.fernet import Fernet

from app.datasources.encryption import FernetSecretCipher, SecretCipherError
from app.security.credentials import CredentialProvider, SecretReference


class _FixedCredentialProvider(CredentialProvider):
    def __init__(self, value: str | None) -> None:
        self._value = value

    def resolve(self, reference: SecretReference) -> str | None:
        return self._value


def test_a_missing_key_refuses_to_construct_the_cipher() -> None:
    with pytest.raises(SecretCipherError, match="not configured"):
        FernetSecretCipher(_FixedCredentialProvider(None))


def test_an_invalid_key_refuses_to_construct_the_cipher() -> None:
    with pytest.raises(SecretCipherError, match="not a valid Fernet key"):
        FernetSecretCipher(_FixedCredentialProvider("not-a-real-key"))


def test_encrypt_then_decrypt_round_trips() -> None:
    cipher = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))

    ciphertext = cipher.encrypt("super-secret-password")

    assert ciphertext != "super-secret-password"
    assert cipher.decrypt(ciphertext) == "super-secret-password"


def test_ciphertext_does_not_contain_the_plaintext() -> None:
    cipher = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))

    ciphertext = cipher.encrypt("a-very-recognizable-password-string")

    assert "a-very-recognizable-password-string" not in ciphertext


def test_tampered_ciphertext_is_refused() -> None:
    cipher = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))

    with pytest.raises(SecretCipherError, match="could not be decrypted"):
        cipher.decrypt("not-a-real-token")


def test_a_different_key_cannot_decrypt_another_key_s_ciphertext() -> None:
    cipher_a = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))
    cipher_b = FernetSecretCipher(_FixedCredentialProvider(Fernet.generate_key().decode()))

    ciphertext = cipher_a.encrypt("password")

    with pytest.raises(SecretCipherError):
        cipher_b.decrypt(ciphertext)
