"""Estructura del libro Excel de importación (hojas y columnas).

Un solo libro ``.xlsx`` con una hoja por tipo de dato.  La fila 1 de cada hoja son
los encabezados (no cambiar los nombres); los datos empiezan en la fila 2.
Las hojas que no se necesitan pueden dejarse vacías o eliminarse.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

SHEET_ORDER = ["UNIDADES", "OFICINAS", "RESPONSABLES", "AUXILIARES",
               "ACTIVOS", "REVALUOS", "TRANSFERENCIAS", "BAJAS"]


@dataclass(frozen=True)
class Col:
    name: str
    required: bool
    width: int
    help: str
    example: str = ""


@dataclass(frozen=True)
class Sheet:
    name: str
    title: str
    cols: Tuple[Col, ...]
    help: str


_UNIDAD = Col("unidad", False, 9, "Código de la Unidad Administrativa tal como está en el VSIAF "
              "(ej. 1, 025). Si se deja vacío se usa la unidad elegida en el importador.", "1")

SHEETS: List[Sheet] = [
    Sheet("UNIDADES", "Unidades administrativas",
          (Col("unidad", True, 9, "Código de la unidad (máx. 5 caracteres).", "2"),
           Col("descripcion", True, 40, "Descripción de la unidad (máx. 120).", "UNIDAD EDUCATIVA LAJA"),
           Col("ciudad", False, 18, "Ciudad / ubicación (máx. 20).", "LAJA")),
          "Solo para crear unidades nuevas. Las que ya existen en el VSIAF se omiten."),
    Sheet("OFICINAS", "Oficinas",
          (_UNIDAD,
           Col("oficina", True, 40, "Nombre de la oficina (máx. 65). El código lo asigna el sistema.",
               "UNIDAD DE CONTABILIDAD"),
           Col("observacion", False, 30, "Observación (opcional).", "")),
          "Oficinas que aún no existen. Si ya existe una con el mismo nombre se omite."),
    Sheet("RESPONSABLES", "Responsables",
          (_UNIDAD,
           Col("oficina", True, 34, "Oficina a la que pertenece (debe existir en el VSIAF o en la hoja OFICINAS).",
               "UNIDAD DE CONTABILIDAD"),
           Col("responsable", True, 34, "Nombre completo (máx. 35).", "EDWIN TONY CHUCA ORDOÑEZ"),
           Col("cargo", True, 34, "Cargo (máx. 35).", "DIRECTOR ADMINISTRATIVO FINANCIERO"),
           Col("ci", False, 14, "Carnet de identidad (máx. 20).", "43101256"),
           Col("expedido", False, 10, "Departamento de expedición: LPZ, CBB, SCZ, ORU, PTS, CHQ, TAR, BEN, PAN, OTR.", "LPZ"),
           Col("observacion", False, 25, "Observación (opcional).", "")),
          "Responsables que aún no existen en su oficina."),
    Sheet("AUXILIARES", "Auxiliares contables",
          (_UNIDAD,
           Col("grupo_contable", True, 36, "Código (1-40) o nombre del grupo contable (D.S. 24051).",
               "EQUIPOS DE COMPUTACION"),
           Col("auxiliar", True, 34, "Nombre del auxiliar (máx. 50). El código lo asigna el sistema.", "LAPTOP"),
           Col("observacion", False, 25, "Observación (opcional).", "")),
          "Auxiliares nuevos dentro de un grupo contable."),
    Sheet("ACTIVOS", "Activos fijos (incorporaciones)",
          (_UNIDAD,
           Col("codigo", True, 18, "Código único del activo (máx. 15). Se guarda en MAYÚSCULAS.", "01-02-3.12-001"),
           Col("codigo_adicional", False, 16, "Código adicional / secundario (máx. 15).", ""),
           Col("descripcion", True, 45, "Descripción del bien (máx. 150).", "COMPUTADORA TODO EN UNO COLOR NEGRO"),
           Col("grupo_contable", True, 32, "Código (1-40) o nombre del grupo contable.", "EQUIPOS DE COMPUTACION"),
           Col("auxiliar", True, 22, "Auxiliar del grupo (debe existir en el VSIAF o en la hoja AUXILIARES).", "TODO EN UNO"),
           Col("oficina", True, 28, "Oficina donde está el bien.", "UNIDAD DE CONTABILIDAD"),
           Col("responsable", True, 30, "Responsable asignado (debe pertenecer a la oficina).", "EDWIN TONY CHUCA ORDOÑEZ"),
           Col("estado_bien", True, 11, "Bueno, Regular o Malo.", "Bueno"),
           Col("fecha_incorporacion", True, 14, "Fecha de alta (dd/mm/aaaa). Debe tener UFV registrada.", "01/09/2026"),
           Col("costo_inicial", True, 14, "Costo histórico en Bs (> 0).", "10000.00"),
           Col("vida_util", False, 10, "Años de vida útil. Vacío = la del grupo contable. Distinta del grupo solo con "
               "incorporación especial autorizada.", ""),
           Col("dep_acumulada_inicial", False, 14, "Solo incorporaciones especiales (bienes recibidos usados).", ""),
           Col("cod_rube", False, 14, "Código RUBE (opcional, máx. 15).", ""),
           Col("organismo_financiador", True, 12, "Código de 3 dígitos del clasificador (ej. 111, 113, 000 = NC).", "113"),
           Col("nro_convenio", False, 12, "Número de convenio (máx. 10).", ""),
           Col("observaciones", False, 30, "Observaciones (opcional).", ""),
           Col("estado_registro", False, 12, "ELABORADO (por defecto) o APROBADO.", "ELABORADO"),
           Col("incorporacion_especial", False, 12, "SI / NO (por defecto NO). Requiere la habilitación de la DGCF.", "NO")),
          "Altas de activos fijos. Un activo = una fila."),
    Sheet("REVALUOS", "Revalúos técnicos",
          (_UNIDAD,
           Col("codigo", True, 18, "Código de un activo APROBADO.", "01-02-3.04-006"),
           Col("fecha_revaluo", True, 14, "Fecha del revalúo técnico (dd/mm/aaaa).", "20/10/2026"),
           Col("nuevo_costo", True, 14, "Nuevo costo en Bs (> 0).", "1500.00"),
           Col("nueva_vida_util", True, 10, "Nueva vida útil en años.", "2"),
           Col("disposicion_respaldo", True, 18, "Resolución / disposición legal (máx. 16).", "45/2026"),
           Col("motivo", False, 40, "Motivo del revalúo.", "DONACION")),
          "Se registra igual que la opción Opciones → Revalúo técnico del VSIAF."),
    Sheet("TRANSFERENCIAS", "Transferencias",
          (Col("unidad_origen", False, 9, "Unidad actual del activo (vacío = unidad elegida).", "1"),
           Col("codigo", True, 18, "Código de un activo APROBADO.", "01-02-3.13-002"),
           Col("unidad_destino", False, 9, "Unidad destino (vacío = misma unidad).", ""),
           Col("oficina_destino", True, 30, "Oficina destino.", "ALMACEN"),
           Col("responsable_destino", True, 30, "Responsable destino.", "JUAN PEREZ"),
           Col("auxiliar_destino", False, 22, "Obligatorio si cambia de unidad.", "")),
          "Se registra igual que el botón Transferencia de Activos Fijos."),
    Sheet("BAJAS", "Bajas de activos (disposición de bienes)",
          (_UNIDAD,
           Col("codigo", True, 18, "Código de un activo APROBADO.", "01-02-3.007-007"),
           Col("fecha_baja", True, 14, "Fecha de la baja (dd/mm/aaaa).", "20/10/2026"),
           Col("motivo_baja", True, 30, "Código 1-9 o texto del motivo (ver hoja CATALOGOS).", "Inutilización"),
           Col("disposicion_respaldo", True, 18, "Resolución / disposición legal (máx. 16).", "045/2026"),
           Col("observaciones", False, 40, "Observaciones o motivos.", "NO ENCIENDE")),
          "Se registra igual que Opciones → Dar de baja del VSIAF."),
]

SHEET_BY_NAME = {s.name: s for s in SHEETS}
