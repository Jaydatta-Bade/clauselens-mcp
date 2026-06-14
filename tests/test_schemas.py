from schemas import DocumentText, Clause, Span, VerificationResult


def test_document_text_fields():
    doc = DocumentText(text="hello", char_count=5, source_url="https://example.com")
    assert doc.text == "hello"
    assert doc.char_count == 5
    assert doc.source_url == "https://example.com"


def test_document_text_no_url():
    doc = DocumentText(text="hello", char_count=5, source_url=None)
    assert doc.source_url is None


def test_clause_fields():
    cl = Clause(id="cl_001", text="You agree to pay.", char_start=0, char_end=17)
    assert cl.id == "cl_001"
    assert cl.char_end == 17


def test_span_fields():
    sp = Span(char_start=0, char_end=17, quoted_text="You agree to pay.")
    assert sp.quoted_text == "You agree to pay."


def test_verification_result_all_valid():
    result = VerificationResult(
        results=[{"span": {}, "valid": True}, {"span": {}, "valid": True}],
        all_valid=True,
    )
    assert result.all_valid is True


def test_verification_result_not_all_valid():
    result = VerificationResult(
        results=[{"span": {}, "valid": True}, {"span": {}, "valid": False}],
        all_valid=False,
    )
    assert result.all_valid is False
