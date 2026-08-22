from app.conversations.store import DEFAULT_CONVERSATION_TITLE, generate_title, should_generate_title


def test_title_generation_is_deterministic_and_needs_no_llm() -> None:
    assert generate_title("Why did revenue fall in April 2026?") == "April revenue decline"
    assert generate_title("Analyze top products by revenue and margin") == "Top products by revenue and"


def test_only_an_empty_placeholder_conversation_is_auto_named() -> None:
    assert should_generate_title(DEFAULT_CONVERSATION_TITLE, has_messages=False)
    assert not should_generate_title("April revenue decline", has_messages=False)
    assert not should_generate_title(DEFAULT_CONVERSATION_TITLE, has_messages=True)
