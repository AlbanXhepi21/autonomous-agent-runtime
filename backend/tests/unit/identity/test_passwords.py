"""Argon2id hashing: correct verification, rejection, and non-plaintext storage."""

from app.identity.passwords import Argon2PasswordHasher


def test_hash_is_not_plaintext_and_looks_like_argon2id() -> None:
    hasher = Argon2PasswordHasher()

    encoded = hasher.hash("correct horse battery staple")

    assert "correct horse battery staple" not in encoded
    assert encoded.startswith("$argon2id$")


def test_verify_accepts_the_correct_password() -> None:
    hasher = Argon2PasswordHasher()
    encoded = hasher.hash("s3cret-password")

    assert hasher.verify(password_hash=encoded, password="s3cret-password") is True


def test_verify_rejects_an_incorrect_password() -> None:
    hasher = Argon2PasswordHasher()
    encoded = hasher.hash("s3cret-password")

    assert hasher.verify(password_hash=encoded, password="wrong-password") is False


def test_verify_rejects_a_malformed_hash_without_raising() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.verify(password_hash="not-a-real-hash", password="anything") is False


def test_two_hashes_of_the_same_password_differ() -> None:
    """A fresh random salt each time -- confirms this isn't a bare digest."""

    hasher = Argon2PasswordHasher()

    assert hasher.hash("same-password") != hasher.hash("same-password")


def test_needs_rehash_is_false_for_a_freshly_produced_hash() -> None:
    hasher = Argon2PasswordHasher()

    assert hasher.needs_rehash(hasher.hash("s3cret-password")) is False
