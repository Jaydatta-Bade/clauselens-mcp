# server.py
from __future__ import annotations

import os

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ratelimit import check_rate_limit
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP-based rate limiting. Uses X-Forwarded-For (set by Railway) or client host."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        forwarded_for = request.headers.get("x-forwarded-for", "")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )
        if not check_rate_limit(ip):
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status_code=429,
            )
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
    return TAXONOMY_TEXT


@mcp.resource("clauselens://severity-rubric")
def rubric_resource() -> str:
    return RUBRIC_TEXT


# --- Prompt ---
mcp.prompt(analyze_contract)


def create_app():
    return mcp.http_app(
        transport="streamable-http",
        middleware=[
            Middleware(RateLimitMiddleware),
            Middleware(HealthMiddleware),
        ],
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
