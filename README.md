# ClauseLens MCP

![tests](https://github.com/Jaydatta-Bade/clauselens-mcp/actions/workflows/test.yml/badge.svg)

ClauseLens is a production remote MCP (Model Context Protocol) server that turns Claude into a contract analyst. It exposes structured tools for fetching documents, segmenting clauses, verifying spans, and accessing a risk taxonomy — the connecting LLM does all reasoning. No documents are retained and no LLM calls are made server-side.

**Live server:** `https://clauselens-mcp-production.up.railway.app/mcp`

---

## Architecture

```
┌─────────────────────┐
│   Claude / Cursor   │  (does all reasoning, zero server-side LLM calls)
└────────┬────────────┘
         │  HTTPS (Streamable HTTP / MCP protocol)
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
│   Middleware:                                       │
│     IP-based rate limiting (60 req/hour default)   │
│     /health bypass                                  │
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
| `fetch_document(url)` | SSRF-hardened HTTP fetch. Extracts readable text via trafilatura. 10s timeout, 2MB cap, 100k char extracted text cap. Returns `DocumentText`. |
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

## Connecting to Claude.ai

1. Go to [Claude.ai](https://claude.ai) → **Settings** → **Integrations** → **Add MCP Server**
2. Enter the server URL: `https://clauselens-mcp-production.up.railway.app/mcp`
3. Click **Connect** — no sign-in required
4. The ClauseLens tools, resources, and prompt will be available immediately

### Using in Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "clauselens": {
      "url": "https://clauselens-mcp-production.up.railway.app/mcp"
    }
  }
}
```

---

## Deploy Your Own Instance

### Prerequisites

- [Railway account](https://railway.app)
- Railway CLI: `npm install -g @railway/cli`

### Steps

1. Fork or clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/clauselens-mcp.git
   cd clauselens-mcp
   ```

2. Log in and create a new Railway project:
   ```bash
   railway login
   railway init
   ```

3. Deploy:
   ```bash
   railway up
   ```

4. Optionally set environment variables in the Railway dashboard (Project → Variables):

   | Variable | Description | Default |
   |----------|-------------|---------|
   | `RATELIMIT_REQUESTS` | Requests per window per IP | `60` |
   | `RATELIMIT_WINDOW_SECONDS` | Rate limit window in seconds | `3600` |
   | `PORT` | Server port (Railway sets this automatically) | `8000` |

5. Railway assigns a public HTTPS URL automatically. Append `/mcp` to get your MCP endpoint.

---

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python server.py
   ```

The server listens on `http://localhost:8000/mcp` by default.

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The test suite covers tools, rate limiting, SSRF hardening, and schema validation.

---

## Security

**SSRF hardening:** `fetch_document` blocks requests to private IP ranges (RFC 1918, loopback, link-local, cloud metadata endpoints), validates schemes (http/https only), and enforces a 10-second timeout. DNS-rebinding is prevented by pinning the TCP connection to the pre-resolved IP address, and the URL is re-validated on every redirect hop.

**Memory-exhaustion protection:** The response body is streamed and capped at 2 MB — the transfer aborts the moment it exceeds the limit, so a hostile server cannot stream an unbounded payload into memory. Extracted text is further capped at 100k characters.

**No document retention:** All document processing happens in-memory during the request lifecycle. No contract text, extracted content, or analysis results are stored, logged, or persisted anywhere.

**Rate limiting:** IP-based fixed-window rate limiter enforced at the middleware layer before any tool logic runs. Default: 60 requests per hour per IP. Configurable via `RATELIMIT_REQUESTS` and `RATELIMIT_WINDOW_SECONDS`. Returns HTTP 429 when exceeded.

> **Scaling note:** The rate limiter is in-process, so its counters are per-instance and reset on restart — correct for the current single-instance deployment. Running multiple replicas would require moving the counter to a shared store (e.g. Redis).

**Input validation:** All tool inputs and outputs are validated via Pydantic schemas.

---

## Disclaimer

ClauseLens provides automated information, not legal advice.

---

## License

[MIT](LICENSE)
