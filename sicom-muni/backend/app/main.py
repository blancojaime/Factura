"""SICOM-MUNI — API de Contratacion Menor Municipal (FastAPI)."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .database import engine
from .errors import EstadoInvalidoError, NoEncontradoError, ReglaNegocioError
from .routers import admin, auth, catalogos, contrataciones, reportes, verificacion

log = logging.getLogger("sicom")
API = "/api/v1"


def crear_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="SICOM-MUNI", version="1.0.0",
                  description="Sistema Integrado de Contratación Menor Municipal",
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def cabeceras_seguridad(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.exception_handler(ReglaNegocioError)
    async def _regla(_: Request, exc: ReglaNegocioError):
        return JSONResponse(status_code=422, content={"detail": {"codigo": exc.codigo, "mensaje": exc.mensaje, "errores": exc.errores}})

    @app.exception_handler(EstadoInvalidoError)
    async def _estado(_: Request, exc: EstadoInvalidoError):
        status = 403 if exc.codigo == "ROL_NO_AUTORIZADO" else 409
        return JSONResponse(status_code=status, content={"detail": {"codigo": exc.codigo, "mensaje": exc.mensaje, "errores": []}})

    @app.exception_handler(NoEncontradoError)
    async def _nf(_: Request, exc: NoEncontradoError):
        return JSONResponse(status_code=404, content={"detail": {"codigo": "NO_ENCONTRADO", "mensaje": exc.mensaje, "errores": []}})

    @app.get(f"{API}/salud", tags=["sistema"])
    def salud():
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        return {"estado": "ok"}

    for r in (auth.router, admin.router, catalogos.router, contrataciones.router, reportes.router, verificacion.router):
        app.include_router(r, prefix=API)
    return app


app = crear_app()
