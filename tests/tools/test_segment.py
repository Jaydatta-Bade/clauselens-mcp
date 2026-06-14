# tests/tools/test_segment.py
import pytest
from tools.segment import segment_clauses
from schemas import Clause


def test_returns_list_of_clauses():
    text = "1. Payment\n\nYou agree to pay $100 per month on the first day.\n\n2. Termination\n\nEither party may terminate with 30 days notice."
    clauses = segment_clauses(text)
    assert isinstance(clauses, list)
    assert all(isinstance(c, Clause) for c in clauses)


def test_offsets_are_exact():
    """The critical property: text[char_start:char_end] must equal clause.text."""
    text = "1. Payment\n\nYou agree to pay $100 per month.\n\n2. Termination\n\nEither party may terminate."
    clauses = segment_clauses(text)
    for clause in clauses:
        assert text[clause.char_start:clause.char_end] == clause.text, (
            f"Offset mismatch for {clause.id}: "
            f"text[{clause.char_start}:{clause.char_end}]={text[clause.char_start:clause.char_end]!r} "
            f"!= {clause.text!r}"
        )


def test_ids_are_unique_and_sequential():
    text = "1. Alpha\n\nFirst clause text here for testing.\n\n2. Beta\n\nSecond clause text here for testing."
    clauses = segment_clauses(text)
    ids = [c.id for c in clauses]
    assert len(ids) == len(set(ids)), "Clause IDs must be unique"
    for i, cid in enumerate(ids, 1):
        assert cid == f"cl_{i:03d}", f"Expected cl_{i:03d}, got {cid}"


def test_short_chunks_filtered_out():
    text = "1. Payment\n\nYou agree to pay $100 per month on the first day of each month.\n\n2. X\n\nOK\n\n3. Termination\n\nEither party may terminate with 30 days written notice."
    clauses = segment_clauses(text)
    for clause in clauses:
        assert len(clause.text) >= 30, f"Clause too short: {clause.text!r}"


def test_paragraph_break_segmentation():
    """Falls back to paragraph-based splitting when no section markers are present."""
    text = (
        "You agree to pay one hundred dollars per month for the service provided.\n\n"
        "Either party may terminate this agreement with thirty days written notice.\n\n"
        "All disputes shall be resolved by binding arbitration in the state of Delaware."
    )
    clauses = segment_clauses(text)
    assert len(clauses) == 3
    for clause in clauses:
        assert text[clause.char_start:clause.char_end] == clause.text


def test_numbered_section_segmentation():
    text = (
        "1. Payment Terms\n\nYou agree to pay one hundred dollars per month promptly.\n\n"
        "2. Termination\n\nEither party may terminate with thirty days written notice.\n\n"
        "3. Arbitration\n\nAll disputes shall be resolved by binding arbitration in Delaware."
    )
    clauses = segment_clauses(text)
    assert len(clauses) >= 3
    for clause in clauses:
        assert text[clause.char_start:clause.char_end] == clause.text


def test_empty_text_returns_empty_list():
    assert segment_clauses("") == []


def test_whitespace_only_returns_empty_list():
    assert segment_clauses("   \n\n   ") == []
