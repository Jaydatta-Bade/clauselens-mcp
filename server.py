# server.py
from __future__ import annotations

import os

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from prompts import analyze_contract
from taxonomy import RUBRIC_TEXT, TAXONOMY_TEXT, get_risk_taxonomy
from tools.fetch import fetch_document
from tools.segment import segment_clauses
from tools.verify import verify_spans


class HealthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return JSONResponse({"status": "ok"})
        return await call_next(request)


mcp = FastMCP(
    "ClauseLens",
    instructions=(
        "ClauseLens x-rays contracts for risky clauses. "
        "Start with the `analyze_contract` prompt, passing a URL or pasted text. "
        "It will guide you through fetching, segmenting, classifying, and verifying "
        "every clause before presenting findings."
    ),
)

# --- Tools ---
mcp.tool(fetch_document)
mcp.tool(segment_clauses)
mcp.tool(verify_spans)
mcp.tool(get_risk_taxonomy)


# --- Resources ---
@mcp.resource("clauselens://taxonomy")
def taxonomy_resource() -> str:
    """Risk category definitions and signal language for 15 clause types."""
    return TAXONOMY_TEXT


@mcp.resource("clauselens://severity-rubric")
def rubric_resource() -> str:
    """How to score clause severity (critical/high/medium/low) and calibrate confidence."""
    return RUBRIC_TEXT


# --- Prompt ---
mcp.prompt(analyze_contract)


def create_app():
    """FastMCP app with OAuth 2.1 via WorkOS and a /health bypass."""
    return mcp.http_app(
        transport="streamable-http",
        middleware=[Middleware(HealthMiddleware)],
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
