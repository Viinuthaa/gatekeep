
from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingDecision:
    model: str
    reason: str
    complexity: str


def route_request(
    messages: list[dict],
    requested_model: str,
) -> RoutingDecision:
    prompt = " ".join(
        message.get("content", "")
        for message in messages
        if message.get("role") == "user"
    ).strip()

    word_count = len(prompt.split())
    lower_prompt = prompt.lower()

    complex_keywords = (
        "analyze",
        "compare",
        "debug",
        "explain in detail",
        "step by step",
        "architecture",
        "prove",
        "derive",
        "evaluate",
    )

    is_complex = (
        word_count > 120
        or any(keyword in lower_prompt for keyword in complex_keywords)
    )

    if is_complex:
        return RoutingDecision(
            model=requested_model,
            reason="Complex request; preserving the requested model",
            complexity="complex",
        )

    return RoutingDecision(
        model=requested_model,
        reason="Simple request; preserving the requested model",
        complexity="simple",
    )
