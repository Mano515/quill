"""Quill FastAPI application."""

import pathlib

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from quill.api.auth import API_KEY, require_key
from quill.api.routes import annotations, basic, convert, extraction, forms, security

app = FastAPI(
    title="Quill PDF API",
    description="Complete PDF editing and processing API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_auth = Depends(require_key)

app.include_router(basic.router, dependencies=[_auth])
app.include_router(security.router, dependencies=[_auth])
app.include_router(annotations.router, dependencies=[_auth])
app.include_router(extraction.router, dependencies=[_auth])
app.include_router(forms.router, dependencies=[_auth])
app.include_router(convert.router, dependencies=[_auth])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Quill PDF API"}


@app.post("/auth/login")
async def login(body: dict):
    """Exchange a key for confirmation — used by the UI login form."""
    import secrets as _s
    key = body.get("key", "")
    if not _s.compare_digest(key, API_KEY):
        return JSONResponse({"ok": False}, status_code=401)
    return {"ok": True}


_static = pathlib.Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def ui():
    return (_static / "index.html").read_text(encoding="utf-8")
