
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    response: str
    expected_contains: tuple[str, ...] = ()
    expected_not_contains: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    name: str
    passed: bool
    checks_passed: int
    total_checks: int
    score: float
    failures: tuple[str, ...]


def evaluate_case(case: EvaluationCase) -> EvaluationResult:
    if not case.name.strip():
        raise ValueError("Evaluation case name cannot be empty")

    if not isinstance(case.response, str):
        raise ValueError("Response must be a string")

    failures = []

    for expected in case.expected_contains:
        if expected.lower() not in case.response.lower():
            failures.append(f"Missing expected text: {expected}")

    for unexpected in case.expected_not_contains:
        if unexpected.lower() in case.response.lower():
            failures.append(f"Found unexpected text: {unexpected}")

    total_checks = (
        len(case.expected_contains)
        + len(case.expected_not_contains)
    )
    checks_passed = total_checks - len(failures)
    score = (
        checks_passed / total_checks * 100
        if total_checks
        else 100.0
    )

    return EvaluationResult(
        name=case.name,
        passed=len(failures) == 0,
        checks_passed=checks_passed,
        total_checks=total_checks,
        score=round(score, 2),
        failures=tuple(failures),
    )


def run_evaluations(
    cases: list[EvaluationCase],
) -> dict:
    if not cases:
        raise ValueError("At least one evaluation case is required")

    results = [evaluate_case(case) for case in cases]
    total_cases = len(results)
    passed_cases = sum(result.passed for result in results)

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": total_cases - passed_cases,
        "pass_rate": round(passed_cases / total_cases * 100, 2),
        "results": [
            {
                "name": result.name,
                "passed": result.passed,
                "checks_passed": result.checks_passed,
                "total_checks": result.total_checks,
                "score": result.score,
                "failures": list(result.failures),
            }
            for result in results
        ],
    }
