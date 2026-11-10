"""SICOM-MUNI — API de Contratacion Menor Municipal (FastAPI)."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .database import engine, preparar_sqlite
from .services import licencia as servicio_licencia
from .estaticos import montar_frontend
from .errors import EstadoInvalidoError, NoEncontradoError, ReglaNegocioError
from .routers import admin, auth, catalogos, contrataciones, importaciones, licencia as licencia_router, reportes, verificacion

log = logging.getLogger("sicom")
API = "/api/v1"


def crear_app() -> FastAPI:
    s = get_settings()
    preparar_sqlite()
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
        if request.url.path.startswith("/api"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.middleware("http")
    async def control_licencia(request: Request, call_next):
        """Con licencia obligatoria (instalador de Windows) la API solo responde si hay licencia o prueba vigente."""
        ruta = request.url.path
        if s.licencia_obligatoria and ruta.startswith(API) and not ruta.startswith((f"{API}/licencia", f"{API}/salud")):
            if not await run_in_threadpool(servicio_licencia.operativo):
                return JSONResponse(status_code=402, content={"detail": {
                    "codigo": "LICENCIA_REQUERIDA", "errores": [],
                    "mensaje": "Se requiere una licencia vigente de SICOM-MUNI. Active la licencia para continuar."}})
        return await call_next(request)

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

    for r in (auth.router, admin.router, catalogos.router, importaciones.router, contrataciones.router, reportes.router,
              verificacion.router, licencia_router.router):
        app.include_router(r, prefix=API)
    if s.static_dir:  # debe ir al final: la ruta comodin no debe tapar a la API
        montar_frontend(app, s.static_dir)
    return app


app = crear_app()
