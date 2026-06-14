from pydantic import BaseModel


class DocumentText(BaseModel):
    text: str
    char_count: int
    source_url: str | None


class Clause(BaseModel):
    id: str
    char_start: int
    char_end: int
    text: str


class Span(BaseModel):
    char_start: int
    char_end: int
    quoted_text: str


class VerificationResult(BaseModel):
    results: list[dict]
    all_valid: bool
