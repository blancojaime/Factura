"""Ayudas para recorrer el flujo completo por la API."""
from datetime import datetime, timedelta, timezone

API = "/api/v1"


class Flujo:
    def __init__(self, client, tokens):
        self.c, self.t = client, tokens

    def req(self, metodo, ruta, usuario, esperado=None, **kw):
        r = self.c.request(metodo, API + ruta, headers=self.t[usuario], **kw)
        if esperado is not None:
            assert r.status_code == esperado, f"{metodo} {ruta} como {usuario}: {r.status_code} {r.text[:600]}"
        return r

    def partida(self, codigo):
        r = self.req("GET", f"/partidas?q={codigo}", "solicitante", 200)
        return next(p for p in r.json() if p["codigo_partida"] == codigo)

    def crear(self, objeto, tipo, plazo, **extra):
        datos = {"objeto_contratacion": objeto, "tipo_objeto": tipo, "plazo_dias_calendario": plazo,
                 "unidad_solicitante": "Unidad de Obras Públicas",
                 "justificacion": "Atención de la necesidad institucional programada en el POA.",
                 "especificaciones_tecnicas": "Cumplir las especificaciones técnicas detalladas para cada ítem solicitado.",
                 "lugar_entrega": "Almacén municipal, calle Bolívar N° 123"}
        datos.update(extra)
        return self.req("POST", "/contrataciones", "solicitante", 201, json=datos).json()

    def item(self, cid, partida_codigo, desc, unidad, cant, precio, codigo="", fuera=False, esperado=201):
        p = self.partida(partida_codigo)
        return self.req("POST", f"/contrataciones/{cid}/items", "solicitante", esperado, json={
            "codigo_unspsc": codigo, "partida_id": p["id"], "descripcion_especifica": desc, "unidad_medida": unidad,
            "cantidad": str(cant), "precio_unitario_ref": str(precio), "fuera_catalogo_chb": fuera})

    def accion(self, cid, accion, usuario, esperado=200, **kw):
        return self.req("POST", f"/contrataciones/{cid}/{accion}", usuario, esperado, **kw)

    def detalle(self, cid, usuario="rpa"):
        return self.req("GET", f"/contrataciones/{cid}", usuario, 200).json()


def ahora_mas(**delta):
    return (datetime.now(timezone.utc) + timedelta(**delta)).isoformat()
