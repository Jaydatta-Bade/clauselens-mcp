# ClauseLens MCP

![tests](https://github.com/Jaydatta-Bade/clauselens-mcp/actions/workflows/test.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.12%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

**ClauseLens turns any MCP-capable AI (Claude, Cursor, etc.) into a contract analyst.** Point it at a lease, NDA, employment offer, SaaS agreement, or Terms of Service and it walks the AI through a disciplined workflow: fetch the document, split it into clauses, classify each against a risk taxonomy, score severity from *your* side of the deal, and — critically — verify every quote is real before showing it to you.

It's a remote [Model Context Protocol](https://modelcontextprotocol.io) server. The connecting AI does all the reasoning; the server just gives it sharp, safe tools and a rigorous process to follow.

> **🔗 Live server:** `https://clauselens-mcp-production.up.railway.app/mcp`
> No sign-up, no API key — add the URL to Claude and start analyzing.

---

## Why it's built this way

Three design decisions make ClauseLens different from "just paste your contract into ChatGPT":

1. **Zero server-side LLM calls.** The server never talks to an LLM and needs no `ANTHROPIC_API_KEY`. All intelligence lives in the AI that connects to it. The server's job is to be a *trustworthy instrument* — fetch, segment, verify — not a second brain. This makes it cheap, fast, stateless, and model-agnostic.

2. **Grounding guardrail against hallucination.** AIs love to paraphrase and occasionally invent contract language. ClauseLens forces the model to call `verify_spans` and prove every quote it intends to show appears *verbatim* at the exact character offsets in the source. Anything that doesn't verify gets dropped. You never see a fabricated clause.

3. **No document retention.** Contracts are sensitive. Every byte is processed in memory during the request and then gone — nothing is stored, logged, or persisted. Ever.

---

## How it works

### The analysis flow

When you ask Claude to "analyze this contract," the `analyze_contract` prompt injects a 7-step workflow that drives the tools in order:

```
You: "Analyze this freelance agreement from the contractor's side: <url>"
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. fetch_document(url)      → clean text (SSRF-hardened)     │
│  2. segment_clauses(text)    → clauses w/ exact char offsets  │
│  3. read clauselens://taxonomy + severity-rubric resources   │
│  4. classify each clause against the 15 risk categories      │
│  5. judge risk FROM THE CHOSEN SIDE (contractor here)        │
│  6. score severity (low→critical) + confidence (0.0–1.0)     │
│  7. verify_spans(text, quotes) → drop anything not verbatim  │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
You get: an overall risk score, a severity breakdown, and per-clause
findings — each with a verbatim quote, plain-English meaning, why it
matters to you, and what you might do about it.
```

The AI is told to pick a **side** first (tenant vs. landlord, contractor vs. client), because the same indemnification clause that endangers a freelancer protects the company. Risk is always relative to *who's signing*.

### System architecture

```
┌─────────────────────┐
│   Claude / Cursor   │   does all reasoning · zero server-side LLM calls
└─────────┬───────────┘
          │  HTTPS · Streamable HTTP (MCP)
          ▼
┌─────────────────────┐
│   Railway           │   TLS termination · public HTTPS URL
└─────────┬───────────┘
          ▼
┌──────────────────────────────────────────────────────────────┐
│  FastMCP 3.x  (Streamable HTTP transport)                    │
│                                                              │
│  Middleware                                                  │
│    • IP rate limiting (60 req/hr, returns 429)              │
│    • /health bypass                                          │
│                                                              │
│  Tools                                                       │
│    fetch_document   → SSRF-hardened, streaming, capped fetch │
│    segment_clauses  → offset-exact clause splitter          │
│    verify_spans     → verbatim-quote grounding guardrail    │
│    get_risk_taxonomy→ the 15-category risk reference        │
│                                                              │
│  Resources                                                   │
│    clauselens://taxonomy          (15 risk categories)      │
│    clauselens://severity-rubric   (low / med / high / crit) │
│                                                              │
│  Prompt                                                      │
│    analyze_contract   (injects the 7-step workflow)         │
│                                                              │
│  No document retention — everything in-memory               │
└──────────────────────────────────────────────────────────────┘
```

---

## Integrating with AI tools

### Claude.ai (web)

1. Go to **Settings → Connectors → Add custom connector**
2. Name it `ClauseLens` and paste the URL:
   `https://clauselens-mcp-production.up.railway.app/mcp`
3. Click **Add** / **Connect** — no sign-in required.
4. Start a chat and try: *"Use ClauseLens to analyze this Terms of Service from the customer's side: https://example.com/terms"*

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "clauselens": {
      "url": "https://clauselens-mcp-production.up.railway.app/mcp"
    }
  }
}
```

Restart Claude Desktop. ClauseLens tools appear in the 🔌 menu.

### Cursor

In **Settings → MCP → Add new MCP server**, choose transport `HTTP` and enter the same URL. ClauseLens tools become available to the agent.

### Any MCP client

ClauseLens speaks standard MCP over Streamable HTTP at `/mcp`. Any compliant client can connect with just the URL — there are no auth headers to configure.

---

## MCP surface reference

### Tools

| Tool | Description |
|------|-------------|
| `fetch_document(url)` | Fetches a public URL and returns cleaned readable text (via trafilatura). SSRF-hardened, streams the body with a 2 MB cap, 10s timeout, 100k-char text cap. Returns `DocumentText`. |
| `segment_clauses(text)` | Splits contract text into clauses with exact character offsets. Guarantees the invariant `text[c.char_start:c.char_end] == c.text`. Returns `list[Clause]`. |
| `verify_spans(text, spans)` | Grounding guardrail. Confirms each quoted span matches the source verbatim at its offsets. The AI must drop any clause that fails. Returns `VerificationResult`. |
| `get_risk_taxonomy()` | Returns the 15 risk categories with definitions and signal language. Returns `dict`. |

### Resources

| URI | Description |
|-----|-------------|
| `clauselens://taxonomy` | The 15 risk categories in markdown |
| `clauselens://severity-rubric` | The 4-level severity scale and confidence calibration guidance |

### Prompt

**`analyze_contract(document, is_url=False, perspective=None)`** — injects the full 7-step analysis workflow.

| Parameter | Type | Description |
|-----------|------|-------------|
| `document` | `str` | Contract text, or a URL if `is_url=True` |
| `is_url` | `bool` | Whether `document` is a URL to fetch |
| `perspective` | `str` | The side you're on (e.g. `"tenant"`, `"freelancer"`). If omitted, the AI assumes you're the weaker party being asked to sign. |

### The 15 risk categories

`auto_renewal` · `unilateral_change` · `liability_limitation` · `indemnification` · `arbitration_or_class_waiver` · `data_sharing_or_privacy` · `ip_assignment` · `non_compete_or_non_solicit` · `termination_terms` · `payment_fees_penalties` · `confidentiality` · `governing_law_jurisdiction` · `warranty_disclaimer` · `assignment_or_transfer` · `other`

---

## Security

**SSRF hardening.** `fetch_document` blocks requests to private IP ranges (RFC 1918, loopback, link-local, and cloud metadata endpoints like `169.254.169.254`), allows only `http`/`https`, and enforces a 10-second timeout. It defends against **DNS-rebinding (TOCTOU)** by resolving the hostname once and pinning the TCP connection to that validated IP — while preserving the original hostname for TLS SNI and certificate verification. The URL is **re-validated on every redirect hop**, so a public URL can't 302 you into the internal network.

**Memory-exhaustion protection.** The response body is *streamed* and capped at 2 MB — the transfer aborts the instant it crosses the limit, so a hostile server can't push an unbounded payload into memory. Extracted text is further capped at 100k characters.

**No document retention.** All processing happens in memory during the request lifecycle. No contract text, extracted content, or analysis is stored, logged, or persisted.

**Rate limiting.** IP-based fixed-window limiter runs in middleware before any tool logic. Default 60 req/hour per IP; returns HTTP 429 when exceeded. Tunable via `RATELIMIT_REQUESTS` / `RATELIMIT_WINDOW_SECONDS`.

> **Scaling note:** the rate limiter is in-process, so counters are per-instance and reset on restart — correct for the current single-instance deployment. Multiple replicas would need a shared store (e.g. Redis).

**Typed I/O.** All tool inputs and outputs are validated through Pydantic models.

---

## Local development

```bash
git clone https://github.com/Jaydatta-Bade/clauselens-mcp.git
cd clauselens-mcp
pip install -r requirements.txt
python server.py            # serves http://localhost:8000/mcp
```

No configuration is required — every environment variable is optional (see `.env.example`).

### Running tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

44 tests cover SSRF hardening, the streaming size cap, clause segmentation offset-exactness, the grounding guardrail, rate limiting, and schema validation. CI runs them on Python 3.12 and 3.13 on every push.

---

## Deploy your own instance

ClauseLens runs anywhere that serves a Python ASGI app. On [Railway](https://railway.app):

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Railway assigns a public HTTPS URL; append `/mcp` to get your MCP endpoint. Optional env vars:

| Variable | Description | Default |
|----------|-------------|---------|
| `RATELIMIT_REQUESTS` | Requests per window per IP | `60` |
| `RATELIMIT_WINDOW_SECONDS` | Window length in seconds | `3600` |
| `PORT` | Server port (Railway sets this automatically) | `8000` |

---

## Project structure

```
server.py            FastMCP app: tools, resources, prompt, middleware
ratelimit.py         in-process IP rate limiter
schemas.py           Pydantic models (DocumentText, Clause, Span, …)
taxonomy.py          the 15 risk categories + severity rubric text
prompts.py           the analyze_contract workflow prompt
tools/
  fetch.py           SSRF-hardened streaming document fetch
  segment.py         offset-exact clause segmentation
  verify.py          verbatim-quote grounding guardrail
tests/               44 tests (pytest)
```

---

## Tech stack

[FastMCP 3.x](https://github.com/jlowin/fastmcp) · Starlette/ASGI · Pydantic v2 · httpx · trafilatura · Railway · GitHub Actions

---

## Disclaimer

ClauseLens provides automated information, **not legal advice**. It can miss issues or misread context. For decisions that matter, consult a qualified lawyer.

---

## License

[MIT](LICENSE)
