"""Modo sin motor PDF (equipos sin las librerias de WeasyPrint): el documento se guarda como HTML imprimible."""
from app.services import generador_pdf
from tests.helpers import Flujo


def test_documento_html_cuando_no_hay_weasyprint(client, tokens, monkeypatch):
    monkeypatch.setattr(generador_pdf, "PDF_DISPONIBLE", False)
    f = Flujo(client, tokens)
    c = f.crear("Compra de útiles de escritorio para la oficina", "BIEN", 5)
    cid = c["id"]
    f.item(cid, "39500", "Resma de papel bond tamaño carta", "Resma", 10, "40.00", codigo="14111507", fuera=True)
    # sin catalogo: se marca excepcion antes de solicitar
    f.req("PATCH", f"/contrataciones/{cid}", "solicitante", 200, json={
        "justificacion_excepcion_chb": "x" * 90, "codigo_autorizacion_chb": "AUT-1"})
    d = f.accion(cid, "solicitar", "solicitante").json()
    doc = next(x for x in d["documentos"] if x["tipo_doc"] == "C1_SOLICITUD")
    r = f.req("GET", f"/contrataciones/{cid}/documentos/{doc['id']}/descargar", "solicitante", 200)
    assert r.headers["content-type"].startswith("text/html")
    assert "Vista HTML" in r.text and "Solicitud" in r.text
    assert 'filename="' in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.html"')
