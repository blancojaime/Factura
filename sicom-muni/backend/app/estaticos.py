"""Sirve la pantalla web exportada (Next.js 'export') desde la propia API: una sola aplicacion, un solo puerto."""
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# rutas dinamicas: la pagina exportada usa el marcador "_" y el navegador lee el identificador real de la URL
DINAMICAS = [
    (re.compile(r"^contrataciones/(?!nueva(?:/|$))[^/]+/?$"), "contrataciones/_/index.html"),
    (re.compile(r"^verificar/[^/]+/?$"), "verificar/_/index.html"),
]
SIN_CACHE = {"Cache-Control": "no-cache"}
CACHE_LARGO = {"Cache-Control": "public, max-age=31536000, immutable"}


def montar_frontend(app: FastAPI, directorio: str) -> None:
    raiz = Path(directorio).resolve()
    if not (raiz / "index.html").is_file():
        raise RuntimeError(f"STATIC_DIR no contiene la pantalla web exportada: {raiz}")

    def archivo(ruta: Path, estado: int = 200) -> FileResponse:
        inmutable = "_next" in ruta.parts and "static" in ruta.parts
        return FileResponse(ruta, status_code=estado, headers=CACHE_LARGO if inmutable else SIN_CACHE)

    @app.get("/{ruta:path}", include_in_schema=False)
    def pantalla(ruta: str):
        if ruta.startswith("api/") or ruta == "api":
            raise HTTPException(404, "No encontrado")
        candidato = (raiz / ruta).resolve()
        if raiz not in candidato.parents and candidato != raiz:
            raise HTTPException(404, "No encontrado")
        if candidato.is_file():
            return archivo(candidato)
        if candidato.is_dir() and (candidato / "index.html").is_file():
            return archivo(candidato / "index.html")
        for patron, destino in DINAMICAS:
            if patron.match(ruta):
                return archivo(raiz / destino)
        pagina = raiz / "404.html"
        return archivo(pagina, 404) if pagina.is_file() else FileResponse(raiz / "index.html", status_code=404)
