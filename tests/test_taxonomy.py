from taxonomy import get_risk_taxonomy, TAXONOMY_TEXT, RUBRIC_TEXT

EXPECTED_CATEGORIES = [
    "auto_renewal",
    "unilateral_change",
    "liability_limitation",
    "indemnification",
    "arbitration_or_class_waiver",
    "data_sharing_or_privacy",
    "ip_assignment",
    "non_compete_or_non_solicit",
    "termination_terms",
    "payment_fees_penalties",
    "confidentiality",
    "governing_law_jurisdiction",
    "warranty_disclaimer",
    "assignment_or_transfer",
    "other",
]


def test_get_risk_taxonomy_returns_all_categories():
    taxonomy = get_risk_taxonomy()
    assert set(taxonomy.keys()) == set(EXPECTED_CATEGORIES)


def test_each_category_has_required_fields():
    taxonomy = get_risk_taxonomy()
    for key, value in taxonomy.items():
        assert "name" in value, f"{key} missing 'name'"
        assert "definition" in value, f"{key} missing 'definition'"
        assert "why_it_matters" in value, f"{key} missing 'why_it_matters'"
        assert "signal_language" in value, f"{key} missing 'signal_language'"
        assert isinstance(value["signal_language"], list), f"{key} signal_language must be a list"


def test_taxonomy_text_is_non_empty_string():
    assert isinstance(TAXONOMY_TEXT, str)
    assert len(TAXONOMY_TEXT) > 100


def test_rubric_text_is_non_empty_string():
    assert isinstance(RUBRIC_TEXT, str)
    assert len(RUBRIC_TEXT) > 100


def test_rubric_text_contains_severity_levels():
    for level in ("critical", "high", "medium", "low"):
        assert level in RUBRIC_TEXT.lower(), f"RUBRIC_TEXT missing severity '{level}'"
