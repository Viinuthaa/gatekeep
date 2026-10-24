
from app.router import route_request


def test_simple_prompt_is_classified_as_simple():
    decision = route_request(
        [{"role": "user", "content": "Hi there"}],
        "test-model",
    )

    assert decision.complexity == "simple"
    assert decision.model == "test-model"


def test_complex_keyword_is_classified_as_complex():
    decision = route_request(
        [
            {
                "role": "user",
                "content": "Analyze this system architecture",
            }
        ],
        "test-model",
    )

    assert decision.complexity == "complex"
    assert decision.model == "test-model"


def test_long_prompt_is_classified_as_complex():
    decision = route_request(
        [{"role": "user", "content": "word " * 121}],
        "test-model",
    )

    assert decision.complexity == "complex"


def test_router_returns_a_reason():
    decision = route_request(
        [{"role": "user", "content": "Hello"}],
        "test-model",
    )

    assert decision.reason
