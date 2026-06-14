# ClauseLens MCP

ClauseLens is a production remote MCP (Model Context Protocol) server that turns Claude or Cursor into a contract analyst. It exposes structured tools for fetching documents, segmenting clauses, verifying spans, and accessing a risk taxonomy — the connecting LLM does all reasoning. No documents are retained and no LLM calls are made server-side.

---

## Architecture

```
┌─────────────────────┐
│   Claude / Cursor   │  (does all reasoning, zero server-side LLM calls)
└────────┬────────────┘
         │  HTTPS + JWT (OAuth 2.1 via WorkOS AuthKit)
         ▼
┌─────────────────────┐
│   Railway (public   │  (TLS termination, public HTTPS URL)
│   HTTPS endpoint)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│   FastMCP 3.x (Streamable HTTP)                     │
│                                                     │
│   Auth middleware: JWT validation + rate limiting   │
│                                                     │
│   Tools:                                            │
│     fetch_document  ──► SSRF-hardened HTTP fetch    │
│     segment_clauses ──► heuristic clause splitter   │
│     verify_spans    ──► grounding guardrail         │
│     get_risk_taxonomy ► taxonomy lookup             │
│                                                     │
│   Resources:                                        │
│     clauselens://taxonomy                           │
│     clauselens://severity-rubric                    │
│                                                     │
│   Prompt:                                           │
│     analyze_contract                                │
│                                                     │
│   No document retention — all processing in-memory │
└─────────────────────────────────────────────────────┘
```

---

## MCP Surface

### Tools

| Tool | Description |
|------|-------------|
| `fetch_document(url)` | SSRF-hardened HTTP fetch. Extracts readable text via trafilatura. 10s timeout, 2MB cap, 100k char extracted text cap. Rate-limited per user (10 req/hour default). Returns `DocumentText`. |
| `segment_clauses(text)` | Splits contract text into clauses with exact character offsets. Invariant: `text[c.char_start:c.char_end] == c.text`. Returns `list[Clause]`. |
| `verify_spans(text, spans)` | Grounding guardrail. Verifies that clause spans still match the original text. Claude must drop any clause that fails. Returns `VerificationResult`. |
| `get_risk_taxonomy()` | Returns the 15 risk categories with definitions and signal language. Returns `dict`. |

### Resources

| Resource URI | Description |
|--------------|-------------|
| `clauselens://taxonomy` | 15 risk categories in markdown format |
| `clauselens://severity-rubric` | 4-level severity scale: critical, high, medium, low |

### Prompt

**`analyze_contract(document, is_url, perspective)`**

Injects a full 9-step contract analysis workflow into the conversation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `document` | string | Contract text or URL |
| `is_url` | bool | Whether `document` is a URL to fetch |
| `perspective` | string | Analyzing party's perspective (e.g. "vendor", "buyer") |

---

## Connecting Claude

1. Go to [Claude.ai](https://claude.ai) → **Settings** → **Integrations** → **Add MCP Server**
2. Enter the MCP URL: `https://YOUR-SUBDOMAIN.railway.app`
3. Sign in with WorkOS AuthKit when prompted
4. The ClauseLens tools, resources, and prompt will now be available in Claude

---

## Deploy to Railway

### Prerequisites

- [Railway account](https://railway.app)
- Railway CLI: `npm install -g @railway/cli`
- WorkOS account with AuthKit configured (see [WorkOS AuthKit Setup](#workos-authkit-setup))

### Steps

1. Fork or clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/clauselens-mcp.git
   cd clauselens-mcp
   ```

2. Log in and link to Railway:
   ```bash
   railway login
   railway link
   ```

3. Deploy:
   ```bash
   railway up
   ```

4. Set environment variables in the Railway dashboard (Project → Variables):

   | Variable | Description |
   |----------|-------------|
   | `WORKOS_CLIENT_ID` | WorkOS application client ID (e.g. `client_01...`) |
   | `WORKOS_API_KEY` | WorkOS API key (e.g. `sk_live_...`) |
   | `WORKOS_JWKS_URI` | JWKS endpoint: `https://api.workos.com/sso/jwks/<client_id>` |
   | `WORKOS_AUDIENCE` | JWT audience claim, set to `clauselens` |
   | `RATELIMIT_REQUESTS` | Requests per window per user (default: `10`) |
   | `RATELIMIT_WINDOW_SECONDS` | Rate limit window in seconds (default: `3600`) |
   | `PORT` | Port for the server (Railway sets this automatically; default: `8000`) |
   | `MCP_PUBLIC_URL` | Full public URL of the MCP endpoint, e.g. `https://YOUR-SUBDOMAIN.railway.app/mcp` |

5. Railway assigns a public HTTPS URL automatically. Use it as your MCP Server URL.

---

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` and fill in your values:
   ```bash
   cp .env.example .env
   # edit .env with your WorkOS credentials
   ```

3. Start the server:
   ```bash
   python server.py
   ```

The server will listen on `http://localhost:8000/mcp` by default.

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The test suite contains 47 tests covering tools, auth middleware, rate limiting, SSRF hardening, and schema validation.

---

## WorkOS AuthKit Setup

1. Go to [workos.com](https://workos.com) and create an account
2. Navigate to **AuthKit** → **Applications**
3. Create or select an application
4. Collect the following values:
   - **Client ID**: shown on the application overview page
   - **API Key**: found under **API Keys** in your WorkOS dashboard
   - **JWKS URI**: `https://api.workos.com/sso/jwks/<your-client-id>`
5. Set `WORKOS_AUDIENCE` to `clauselens` (must match the `aud` claim in issued JWTs)

---

## Security

**SSRF hardening:** `fetch_document` blocks requests to private IP ranges (RFC 1918, loopback, link-local, metadata endpoints), validates schemes (HTTPS only in production), and enforces a 10-second timeout with a 2MB response cap.

**No document retention:** All document processing happens in-memory during the request lifecycle. No contract text, extracted content, or analysis results are stored, logged, or persisted anywhere.

**Rate limiting:** Per-user token-bucket rate limiter enforced in-process. Default: 10 requests per hour. Configurable via `RATELIMIT_REQUESTS` and `RATELIMIT_WINDOW_SECONDS`.

**Authentication:** Every request must carry a valid JWT issued by WorkOS AuthKit. Unauthenticated or invalid requests are rejected before any tool logic runs.

---

## Disclaimer

ClauseLens provides automated information, not legal advice.
