"""Token generation and hashing: random, high-entropy, and one-way."""

from app.identity.tokens import generate_token, hash_token


def test_generated_tokens_are_unique() -> None:
    assert generate_token() != generate_token()


def test_generated_token_has_no_padding_or_unsafe_characters() -> None:
    token = generate_token()

    assert len(token) >= 32
    assert all(character.isalnum() or character in "-_" for character in token)


def test_hash_is_deterministic() -> None:
    token = generate_token()

    assert hash_token(token) == hash_token(token)


def test_hash_does_not_reveal_the_token() -> None:
    token = generate_token()

    assert hash_token(token) != token


def test_different_tokens_hash_differently() -> None:
    assert hash_token(generate_token()) != hash_token(generate_token())
