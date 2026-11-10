"""Arranque del servidor en produccion (servicio de Windows): API + pantalla web en un solo puerto."""
import logging

import uvicorn

from .config import get_settings


def main() -> None:
    s = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("sicom").info("Iniciando SICOM-MUNI en %s:%s (licencia obligatoria: %s)", s.servidor_host, s.servidor_puerto,
                                    s.licencia_obligatoria)
    uvicorn.run("app.main:app", host=s.servidor_host, port=s.servidor_puerto, workers=1, proxy_headers=True,
                forwarded_allow_ips="127.0.0.1", log_level="info")


if __name__ == "__main__":
    main()
