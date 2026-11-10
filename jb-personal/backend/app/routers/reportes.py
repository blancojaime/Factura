from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Entidad, Usuario
from ..reports import asistencia_xlsx, auditoria_txt, informe_docx, planillas_xlsx
from ..security import LEE
from ..services.consultas import cargar
from ..services.proceso import formato_cite, siguiente_correlativo
from .deps import log

router = APIRouter(prefix="/api/reportes", tags=["reportes"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _resp(data: bytes, mime: str, nombre: str):
    return Response(data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{nombre}"',
                                                    "X-Content-Type-Options": "nosniff"})


def _chk(anio, mes):
    if not (1 <= mes <= 12 and 2000 <= anio <= 2100):
        raise HTTPException(422, "Periodo inválido")


@router.get("/{anio}/{mes}/informe.docx")
def informe(anio: int, mes: int, emitir: bool = False, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    """emitir=true asigna el N° correlativo oficial del informe (se consume); false = borrador sin número."""
    _chk(anio, mes)
    d = cargar(db, anio, mes, u.username)
    nro = None
    if emitir:
        nro = f"{siguiente_correlativo(db, 'INFORME_ASIST', anio):03d}"
        log(db, u, "EMITIR_INFORME", "informe_asistencia", f"{anio}-{mes:02d}", {"nro": nro})
        db.commit()
    data = informe_docx.construir(d, nro, date.today())
    return _resp(data, DOCX, f"Informe_Asistencia_{anio}-{mes:02d}.docx")


@router.get("/{anio}/{mes}/nuevos.xlsx")
def nuevos(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    _chk(anio, mes)
    return _resp(planillas_xlsx.planilla_altas(cargar(db, anio, mes, u.username)), XLSX, f"Planilla_Nuevo_Personal_{anio}-{mes:02d}.xlsx")


@router.get("/{anio}/{mes}/desvinculados.xlsx")
def desvinculados(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    _chk(anio, mes)
    return _resp(planillas_xlsx.planilla_bajas(cargar(db, anio, mes, u.username)), XLSX, f"Planilla_Desvinculados_{anio}-{mes:02d}.xlsx")


@router.get("/{anio}/{mes}/planilla.xlsx")
def planilla(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    _chk(anio, mes)
    return _resp(planillas_xlsx.planilla_sueldos(cargar(db, anio, mes, u.username)), XLSX, f"Planilla_Sueldos_{anio}-{mes:02d}.xlsx")


@router.get("/{anio}/{mes}/asistencia.xlsx")
def asistencia(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    _chk(anio, mes)
    return _resp(asistencia_xlsx.reporte_asistencia(cargar(db, anio, mes, u.username)), XLSX, f"Reporte_Asistencia_{anio}-{mes:02d}.xlsx")


@router.get("/{anio}/{mes}/auditoria.txt")
def auditoria(anio: int, mes: int, delimitador: str = "tab", bom: bool = False, u: Usuario = Depends(LEE),
              db: Session = Depends(get_db)):
    _chk(anio, mes)
    delim = {"tab": "\t", "coma": ",", "pyc": ";"}.get(delimitador)
    if delim is None:
        raise HTTPException(422, "delimitador: tab | coma | pyc")
    data = auditoria_txt.reporte_plano(cargar(db, anio, mes, u.username), delim, bom)
    ext = "csv" if delim != "\t" else "txt"
    return _resp(data, "text/plain; charset=utf-8", f"Consolidado_Auditoria_{anio}-{mes:02d}.{ext}")


@router.get("/{anio}/{mes}/auditoria.xlsx")
def auditoria_xlsx(anio: int, mes: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    """Consolidado plano en Excel: solo títulos y contenido."""
    _chk(anio, mes)
    return _resp(auditoria_txt.reporte_plano_xlsx(cargar(db, anio, mes, u.username)), XLSX, f"Consolidado_Auditoria_{anio}-{mes:02d}.xlsx")
