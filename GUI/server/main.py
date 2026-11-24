# main.py - NL2SQL FastAPI Server
import os
import secrets
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import CORS_ORIGINS, APP_TITLE, APP_VERSION, APP_DESCRIPTION
from routers import query, approval, schema, analysis, ws, connections, audit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ephemeral bearer-token auth (DA-04)
# In production/Electron: set NL2SQL_API_TOKEN in the server process env.
# In development: a fresh token is generated each run and logged to stdout.
# ---------------------------------------------------------------------------
API_AUTH_TOKEN: str = os.environ.get("NL2SQL_API_TOKEN") or secrets.token_urlsafe(32)
if not os.environ.get("NL2SQL_API_TOKEN"):
    logger.warning(
        "NL2SQL_API_TOKEN not set — ephemeral token generated. "
        "Electron should inject this via env before spawning the server."
    )

# Paths that do not require auth (health probe, OpenAPI schema, WebSocket handshake)
_AUTH_EXEMPT_PREFIXES = ("/", "/docs", "/openapi.json", "/redoc", "/ws")

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_local_bearer_token(request: Request, call_next):
    """
    Require valid Bearer token for all API endpoints.
    Exempt: /, /docs, /openapi.json, /redoc, /ws/* (handshake carries token via query param).
    Prevents any local process or browser tab from hitting mutation endpoints without auth.
    """
    path = request.url.path
    if request.method == "OPTIONS" or any(path == p or path.startswith(p + "/") for p in _AUTH_EXEMPT_PREFIXES):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {API_AUTH_TOKEN}"
    if not secrets.compare_digest(auth_header.encode(), expected.encode()):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: missing or invalid Bearer token."},
        )
    return await call_next(request)


# Mount API routers under /api
app.include_router(query.router, prefix="/api")
app.include_router(approval.router, prefix="/api")
app.include_router(schema.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(connections.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(ws.router)  # /ws/{user_id} at root


@app.get("/")
async def retrieveServerHealthAndMetadata():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "docs_url": "/docs",
        "health": "healthy",
    }


root = retrieveServerHealthAndMetadata


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
