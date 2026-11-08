"""Aplicación FastAPI: API REST + frontend estático (modalidad web y base del escritorio)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, config
from .db import init_db
from .routers import asistencia, auth, catalogos, permisos, personal, reportes, sistema
from .services.proceso import ReglaNegocio


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Gestión de Personal y Asistencia Municipal", version=__version__, lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.exception_handler(ReglaNegocio)
async def regla(_: Request, e: ReglaNegocio):
    return JSONResponse({"detail": str(e)}, status_code=422)


@app.middleware("http")
async def cabeceras(request: Request, call_next):
    r = await call_next(request)
    r.headers.setdefault("X-Content-Type-Options", "nosniff")
    r.headers.setdefault("X-Frame-Options", "DENY")
    r.headers.setdefault("Referrer-Policy", "no-referrer")
    if not request.url.path.startswith("/api/docs"):
        r.headers.setdefault("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; frame-src 'self'; object-src 'self'")
    return r


for m in (auth, catalogos, personal, asistencia, permisos, reportes, sistema):
    app.include_router(m.router)


@app.get("/api/salud")
def salud():
    return {"ok": True, "version": __version__}


if config.FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(config.FRONTEND_DIR / "index.html")
