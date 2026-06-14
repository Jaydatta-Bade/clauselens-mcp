# ClauseLens MCP — Design Spec
**Date:** 2026-06-14
**Status:** Approved

---

## 1. What It Is

A remote MCP server that turns a user's own Claude (or Cursor) into a contract analyst. Connect it, point Claude at any contract, lease, NDA, freelance agreement, or Terms of Service, and it x-rays the fine print — flagging risky clauses, explaining them in plain English, and scoring severity.

**Three non-negotiable properties (from the original spec):**
1. **Remote, not local.** Streamable HTTP, public HTTPS URL, connectable from any Claude/Cursor.
2. **OAuth 2.1.** AuthKit-protected. Unauthenticated calls are rejected.
3. **Thin by design.** Zero LLM calls, zero `ANTHROPIC_API_KEY`. The server provides tools + domain knowledge; the connecting Claude does all reasoning.

---

## 2. Stack

| Concern | Choice | Rationale |
|---|---|---|
| MCP framework | fastmcp 2.x | Native Streamable HTTP + OAuth support |
| Language | Python 3.12+ | Spec requirement |
| Schemas | Pydantic v2 | Spec requirement |
| HTTP fetching | httpx | Async-capable, timeout/redirect control for SSRF hardening |
| Text extraction | trafilatura | Readable text from fetched HTML |
| JWT validation | PyJWT[crypto] | Validate AuthKit Bearer tokens against JWKS |
| OAuth provider | WorkOS AuthKit | Cleanest for MCP per spec |
| Deployment | Railway | Stable public HTTPS, simple deploy from requirements.txt |
| Rate limiting | In-process token-bucket | No external DB cost; resets on redeploy (acceptable for now) |

---

## 3. Architecture

Single Python process. FastMCP 2.x serves Streamable HTTP at `/mcp`. WorkOS AuthKit provides OAuth 2.1 — the server validates Bearer JWTs via AuthKit's JWKS endpoint on every inbound request.

```
Claude/Cursor client
    │
    ▼  HTTPS + Bearer JWT
Railway (public URL)
    │
    ▼
FastMCP 2.x  (Streamable HTTP /mcp)
    │── OAuth validation (AuthKit JWKS via PyJWT)
    │── In-process rate limiter (token-bucket per `sub`, resets on restart)
    │
    ├── tools/fetch.py      → fetch_document   (SSRF-hardened)
    ├── tools/segment.py    → segment_clauses  (heuristic, exact offsets)
    ├── tools/verify.py     → verify_spans     (grounding guardrail)
    ├── taxonomy.py         → get_risk_taxonomy + clauselens://taxonomy resource
    │                          + clauselens://severity-rubric resource
    └── prompts.py          → analyze_contract prompt
```

Zero LLM calls. Zero `ANTHROPIC_API_KEY`. The connecting Claude does all reasoning.

---

## 4. MCP Surface

### 4.1 Tools

| Tool | Signature | What it does |
|---|---|---|
| `fetch_document` | `(url: str) -> DocumentText` | Fetch public contract text. SSRF-hardened. 10s timeout, 2MB response cap, 100k char extracted-text cap. |
| `segment_clauses` | `(text: str) -> list[Clause]` | Heuristic split into clauses with exact `char_start`/`char_end` offsets. Deterministic. |
| `verify_spans` | `(text: str, spans: list[Span]) -> VerificationResult` | Confirm each quoted span is verbatim at its offsets. Grounding guardrail — Claude drops any clause that fails. |
| `get_risk_taxonomy` | `() -> Taxonomy` | Returns the 15-category risk vocabulary. Mirrors the resource for tool-style access. |

### 4.2 Resources

| URI | Content |
|---|---|
| `clauselens://taxonomy` | 15 risk categories: definition, why it matters, signal language |
| `clauselens://severity-rubric` | 4-level severity scale (critical/high/medium/low) + confidence calibration rules |

### 4.3 Prompt — `analyze_contract`

Parameters: `document: str`, `is_url: bool = False`, `perspective: str | None`

Injects the full 9-step analysis workflow (verbatim from spec Appendix A):
1. Fetch or use text
2. Call `segment_clauses`
3. Read `clauselens://taxonomy` and `clauselens://severity-rubric`
4. Classify clauses; flag risky ones
5. Explain each: plain English / why it matters / what you might do
6. Score severity + confidence; `confidence < 0.6` → `needs_human_review = true`
7. Call `verify_spans`; drop any clause that fails
8. Emit structured report ordered by severity
9. Always append disclaimer

---

## 5. Schemas (Pydantic v2)

```python
class DocumentText(BaseModel):
    text: str
    char_count: int
    source_url: str | None

class Clause(BaseModel):
    id: str          # e.g. "cl_001"
    text: str
    char_start: int
    char_end: int

class Span(BaseModel):
    char_start: int
    char_end: int
    quoted_text: str

class VerificationResult(BaseModel):
    results: list[dict]  # [{span, valid: bool}]
    all_valid: bool
```

Report shape (emitted by connecting Claude per prompt instructions):
```json
{
  "document_type": "...",
  "overall_risk": 0-100,
  "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
  "summary": "...",
  "assessments": [{
    "excerpt": "...",
    "risk_category": "...",
    "severity": "low|medium|high|critical",
    "confidence": 0.0-1.0,
    "plain_english": "...",
    "why_it_matters": "...",
    "recommendation": "...",
    "needs_human_review": false
  }],
  "disclaimer": "ClauseLens provides automated information..."
}
```

---

## 6. SSRF Hardening (`fetch_document`)

Before fetching and after every redirect:
1. Allow `http`/`https` schemes only
2. Resolve hostname → reject any address in private, loopback, link-local, or reserved ranges (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, `::1`, fc00::/7)
3. Block cloud metadata endpoints (169.254.169.254, 100.100.100.200)
4. Re-validate after redirects (a redirect can point back to an internal address)
5. Enforce 10s timeout, 2MB response size cap, 100k char extracted-text cap

---

## 7. Auth & Rate Limiting

**OAuth 2.1 (AuthKit):**
- Every request must carry a valid Bearer JWT
- Server fetches AuthKit's JWKS once at startup (cached in memory)
- Validates signature, `aud`, `iss`, and expiry on every request
- `sub` claim is the per-identity key for rate limiting

**In-process rate limiter:**
- Token-bucket per `sub`, module-level `dict`
- `fetch_document` only (only tool that touches the network)
- Default: 10 requests/identity/hour (fixed window — counter + timestamp per `sub`)
- Configurable via env vars
- Resets on redeploy — acceptable until Redis is added

**WorkOS AuthKit env vars:**
```
WORKOS_CLIENT_ID=client_01ABCDEFGHIJK...
WORKOS_API_KEY=sk_live_XXXXXXXXXX...
WORKOS_JWKS_URI=https://api.workos.com/sso/jwks/<client_id>
```

---

## 8. Privacy & Safety

- **No retention.** `fetch_document` and `segment_clauses` are in-process only. No document content written to disk, logged, or persisted.
- **Railway logs** contain only request metadata (method, path, status) — never document content.
- **Disclaimer** (emitted verbatim by prompt on every report):
  > *ClauseLens provides automated information, not legal advice. It can miss issues or misread context. For decisions that matter, consult a qualified lawyer.*
- **Honest uncertainty:** `confidence < 0.6` → `needs_human_review: true` and tentative language instead of firm assertions.

---

## 9. Project Structure

```
clauselens-mcp/
├── server.py            # FastMCP app, registrations, OAuth config
├── tools/
│   ├── __init__.py
│   ├── fetch.py         # fetch_document + SSRF hardening
│   ├── segment.py       # segment_clauses (heuristic, exact offsets)
│   └── verify.py        # verify_spans (grounding guardrail)
├── taxonomy.py          # Risk taxonomy + severity rubric (static data)
├── prompts.py           # analyze_contract prompt template + FastMCP registration
├── schemas.py           # Pydantic v2 models
├── auth.py              # AuthKit JWT validation + in-process rate limiter
├── requirements.txt
├── railway.toml         # Railway deploy config
└── README.md            # Architecture writeup + connection guide
```

**`requirements.txt`:**
```
fastmcp>=2.0
pydantic>=2.0
httpx
trafilatura
PyJWT[crypto]
cryptography
```

---

## 10. Environment Variables

```
MCP_PUBLIC_URL=https://<railway-subdomain>.railway.app/mcp
WORKOS_CLIENT_ID=client_01ABCDEFGHIJK...
WORKOS_API_KEY=sk_live_XXXXXXXXXX...
WORKOS_JWKS_URI=https://api.workos.com/sso/jwks/<client_id>
WORKOS_AUDIENCE=<your-audience>
RATELIMIT_REQUESTS=10
RATELIMIT_WINDOW_SECONDS=3600
```

---

## 11. Build Order

**Phase 1 — Deterministic core:**
1. `schemas.py`, `taxonomy.py`
2. `tools/fetch.py` + SSRF unit tests
3. `tools/segment.py`, `tools/verify.py` + offset/fabrication unit tests
4. `prompts.py`

**Phase 2 — Production MCP:**
5. `server.py` — register tools/resources/prompt on FastMCP 2.x Streamable HTTP
6. `auth.py` — AuthKit JWT validation + in-process rate limiter
7. `railway.toml` — deploy config
8. End-to-end test: connect real Claude, invoke `analyze_contract` on a live ToS URL
9. `README.md`

---

## 12. Credibility Checklist

- [ ] Remote MCP server reachable over Streamable HTTP at a public HTTPS URL
- [ ] OAuth 2.1 enforced; unauthenticated calls rejected
- [ ] Real Claude/Cursor connects and runs `analyze_contract` end-to-end on a live URL
- [ ] Core server makes zero LLM calls, requires no `ANTHROPIC_API_KEY`
- [ ] `fetch_document` SSRF-hardened (private IPs, metadata endpoints, redirect-to-internal blocked) with tests
- [ ] `segment_clauses` returns exact char offsets; `verify_spans` catches fabricated spans (with tests)
- [ ] Taxonomy and severity rubric exposed as resources
- [ ] `analyze_contract` prompt enforces span-grounding and low-confidence → `needs_human_review` fallback
- [ ] No raw document content persisted or logged
- [ ] Disclaimer present in every report

---

## 13. Out of Scope

User accounts/dashboards, billing, document history, fine-tuned models, non-English languages, OCR for scanned PDFs, multi-document comparison, Phase 3 web playground.
