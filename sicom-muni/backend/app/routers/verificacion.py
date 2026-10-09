"""Verificacion publica de autenticidad de documentos (sin autenticacion; solo metadatos)."""
import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ContratacionMenor, DocumentoExpediente
from ..services.storage import get_storage

router = APIRouter(prefix="/verificar", tags=["verificacion"])
MAX_BYTES = 15 * 1024 * 1024


def _ficha(db: Session, doc_id: uuid.UUID) -> dict:
    d = db.get(DocumentoExpediente, doc_id)
    if d is None:
        raise HTTPException(404, "Documento no registrado en el expediente digital")
    c = db.get(ContratacionMenor, d.contratacion_id)
    return {
        "documento_id": str(d.id), "tipo_doc": d.tipo_doc, "version": d.version,
        "tramite": c.correlativo_interno if c else "", "objeto": c.objeto_contratacion if c else "",
        "estado_tramite_al_generar": d.estado_tramite, "estado_tramite_actual": c.estado if c else "",
        "fecha_generacion": d.fecha_generacion, "hash_sha256_archivo": d.hash_sha256,
        "hash_sha256_contenido": d.hash_contenido,
        "vigente": bool(c) and d.version == max((x.version for x in c.documentos if x.tipo_doc == d.tipo_doc), default=0),
    }


@router.get("/{doc_id}")
def verificar(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    return _ficha(db, doc_id)


@router.post("/{doc_id}/archivo")
async def verificar_archivo(doc_id: uuid.UUID, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Compara el SHA-256 de un PDF cargado con el registrado: detecta cualquier alteracion."""
    ficha = _ficha(db, doc_id)
    datos = await archivo.read(MAX_BYTES + 1)
    if len(datos) > MAX_BYTES:
        raise HTTPException(413, "Archivo demasiado grande")
    h = hashlib.sha256(datos).hexdigest()
    ficha["hash_sha256_cargado"] = h
    ficha["coincide"] = h == ficha["hash_sha256_archivo"]
    return ficha
