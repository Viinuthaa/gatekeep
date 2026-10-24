
import pytest

from app.evaluations import (
    EvaluationCase,
    evaluate_case,
    run_evaluations,
)


def test_evaluation_passes_when_expected_text_is_present():
    case = EvaluationCase(
        name="photosynthesis response",
        response="Photosynthesis uses light energy and chlorophyll.",
        expected_contains=("light energy", "chlorophyll"),
    )

    result = evaluate_case(case)

    assert result.passed is True
    assert result.checks_passed == 2
    assert result.total_checks == 2
    assert result.score == 100.0


def test_evaluation_fails_when_expected_text_is_missing():
    case = EvaluationCase(
        name="missing information",
        response="Photosynthesis uses light energy.",
        expected_contains=("chlorophyll",),
    )

    result = evaluate_case(case)

    assert result.passed is False
    assert result.score == 0.0
    assert len(result.failures) == 1


def test_evaluation_detects_unexpected_text():
    case = EvaluationCase(
        name="unexpected information",
        response="The result is approved.",
        expected_not_contains=("approved",),
    )

    result = evaluate_case(case)

    assert result.passed is False
    assert result.score == 0.0


def test_evaluation_is_case_insensitive():
    case = EvaluationCase(
        name="case insensitive",
        response="GATEKEEP protects LLM requests.",
        expected_contains=("gatekeep",),
    )

    assert evaluate_case(case).passed is True


def test_evaluation_without_checks_scores_one_hundred():
    case = EvaluationCase(
        name="no checks",
        response="Any response",
    )

    result = evaluate_case(case)

    assert result.passed is True
    assert result.score == 100.0
    assert result.total_checks == 0


def test_evaluation_rejects_empty_case_name():
    case = EvaluationCase(
        name=" ",
        response="Some response",
    )

    with pytest.raises(ValueError):
        evaluate_case(case)


def test_runner_summarizes_multiple_cases():
    cases = [
        EvaluationCase(
            name="passing case",
            response="Gatekeep protects requests.",
            expected_contains=("protects",),
        ),
        EvaluationCase(
            name="failing case",
            response="Something else.",
            expected_contains=("Gatekeep",),
        ),
    ]

    report = run_evaluations(cases)

    assert report["total_cases"] == 2
    assert report["passed_cases"] == 1
    assert report["failed_cases"] == 1
    assert report["pass_rate"] == 50.0


def test_runner_rejects_empty_case_list():
    with pytest.raises(ValueError):
        run_evaluations([])
