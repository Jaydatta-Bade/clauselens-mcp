# tools/verify.py
from __future__ import annotations

from schemas import Span, SpanResult, VerificationResult


def verify_spans(text: str, spans: list[Span]) -> VerificationResult:
    """Confirm each quoted span is verbatim at its offsets in *text*.

    The connecting Claude calls this before displaying any clause to prove
    it did not fabricate or misquote the document text.
    """
    results: list[SpanResult] = []

    for span in spans:
        try:
            actual = text[span.char_start : span.char_end]
            valid = actual == span.quoted_text
        except Exception:
            valid = False

        results.append(SpanResult(span=span, valid=valid))

    return VerificationResult(
        results=results,
        all_valid=all(r.valid for r in results),
    )
