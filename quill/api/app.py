"""Quill FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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

app.include_router(basic.router)
app.include_router(security.router)
app.include_router(annotations.router)
app.include_router(extraction.router)
app.include_router(forms.router)
app.include_router(convert.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Quill PDF API"}


# Serve the UI
import pathlib
_static = pathlib.Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def ui():
    return (_static / "index.html").read_text(encoding="utf-8")
