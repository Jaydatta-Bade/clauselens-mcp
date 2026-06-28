# tests/tools/test_verify.py
import pytest
from tools.verify import verify_spans
from schemas import Span, VerificationResult


TEXT = "You agree to pay $100 per month. Disputes go to arbitration. No class actions."


def _span(start: int, end: int, text: str) -> Span:
    return Span(char_start=start, char_end=end, quoted_text=text)


def test_valid_span_returns_true():
    span = _span(0, 32, "You agree to pay $100 per month.")
    result = verify_spans(TEXT, [span])
    assert result.results[0].valid is True
    assert result.all_valid is True


def test_fabricated_text_returns_false():
    span = _span(0, 32, "You must pay $500 per week.")  # invented text at those offsets
    result = verify_spans(TEXT, [span])
    assert result.results[0].valid is False
    assert result.all_valid is False


def test_wrong_offsets_returns_false():
    # Correct text but wrong offsets
    span = _span(5, 37, "You agree to pay $100 per month.")
    result = verify_spans(TEXT, [span])
    assert result.results[0].valid is False


def test_mixed_valid_and_invalid():
    valid_span = _span(0, 32, "You agree to pay $100 per month.")
    invalid_span = _span(0, 32, "This was not in the document at all.")
    result = verify_spans(TEXT, [valid_span, invalid_span])
    assert result.results[0].valid is True
    assert result.results[1].valid is False
    assert result.all_valid is False


def test_empty_span_list():
    result = verify_spans(TEXT, [])
    assert result.results == []
    assert result.all_valid is True


def test_out_of_bounds_offsets_returns_false():
    span = _span(0, 9999, "some text")
    result = verify_spans(TEXT, [span])
    assert result.results[0].valid is False


def test_returns_verification_result_type():
    result = verify_spans(TEXT, [])
    assert isinstance(result, VerificationResult)


def test_result_contains_span_info():
    span = _span(0, 32, "You agree to pay $100 per month.")
    result = verify_spans(TEXT, [span])
    assert result.results[0].span == span
    assert result.results[0].valid is True
