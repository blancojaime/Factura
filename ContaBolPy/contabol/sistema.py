"""Sistema maestro: usuarios, empresas, gestiones, permisos, auditoría y respaldos de alto nivel."""
from __future__ import annotations

import os
import platform
import re
from datetime import date, datetime

from . import schema
from .db import Database
from .normativa import Normativa, sembrar_normativa
from .permisos import TODAS, permisos_de_rol
from .security import hash_clave, nueva_sal, validar_clave, verificar
from .seed import sembrar_gestion
from .util import iso

NOMBRE_MAESTRA = "sistema.db"


class ErrorNegocio(Exception):
    """Error de regla de negocio mostrado al usuario tal cual."""


class Sistema:
    def __init__(self, raiz: str):
        self.raiz = os.path.abspath(raiz)
        for sub in ("", "datos", "backups", "reportes"):
            os.makedirs(os.path.join(self.raiz, sub), exist_ok=True)
        archivo = os.path.join(self.raiz, NOMBRE_MAESTRA)
        nuevo = not os.path.exists(archivo)
        self.db = Database(archivo)
        if nuevo:
            with self.db.tx():
                for stmt in schema.SISTEMA.split(";\n"):
                    if stmt.strip():
                        self.db.execute(stmt)
                self.db.execute("INSERT INTO config (clave, valor) VALUES ('version_esquema', ?)", (str(schema.VERSION_ESQUEMA),))
                self._sembrar_admin()
        sembrar_normativa(self.db)
        self.normativa = Normativa(self.db)

    # ------------------------------------------------------------------ usuarios
    def _sembrar_admin(self) -> None:
        sal = nueva_sal()
        self.db.insert("usuario", login="admin", nombre="Administrador del Sistema", hash=hash_clave("admin", sal), salt=sal,
                       activo=1, es_admin=1, cambiar_clave=1, intentos=0)

    def autenticar(self, login: str, clave: str) -> dict:
        u = self.db.one("SELECT * FROM usuario WHERE login=?", ((login or "").strip(),))
        if not u:
            raise ErrorNegocio("Usuario o contraseña incorrectos.")
        if not u["activo"]:
            raise ErrorNegocio("El usuario está inactivo. Consulte con el administrador.")
        if u["intentos"] >= 5:
            raise ErrorNegocio("Usuario bloqueado por intentos fallidos. El administrador debe restablecer la contraseña.")
        if not verificar(clave or "", u["salt"], u["hash"]):
            self.db.execute("UPDATE usuario SET intentos=intentos+1 WHERE id=?", (u["id"],))
            self.auditar(u, None, None, "Seguridad", "LOGIN_FALLIDO", "Contraseña incorrecta")
            raise ErrorNegocio("Usuario o contraseña incorrectos.")
        self.db.execute("UPDATE usuario SET intentos=0, ultimo_acceso=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), u["id"]))
        self.auditar(u, None, None, "Seguridad", "LOGIN", "Ingreso al sistema")
        return self.usuario(u["id"])

    def usuario(self, uid: int) -> dict:
        return self.db.one("SELECT id, login, nombre, email, activo, es_admin, cambiar_clave, ultimo_acceso FROM usuario WHERE id=?", (uid,))

    def listar_usuarios(self) -> list[dict]:
        return self.db.query("SELECT id, login, nombre, email, activo, es_admin, intentos, ultimo_acceso FROM usuario ORDER BY login")

    def crear_usuario(self, login: str, nombre: str, clave: str, es_admin: bool = False, email: str = "") -> int:
        login = (login or "").strip()
        if len(login) < 3 or not re.fullmatch(r"[A-Za-z0-9_.-]+", login):
            raise ErrorNegocio("El usuario debe tener al menos 3 caracteres (letras, números, punto o guion).")
        validar_clave(clave)
        if self.db.scalar("SELECT COUNT(*) FROM usuario WHERE login=?", (login,)):
            raise ErrorNegocio("Ya existe un usuario con ese nombre.")
        sal = nueva_sal()
        return self.db.insert("usuario", login=login, nombre=nombre.strip() or login, hash=hash_clave(clave, sal), salt=sal,
                              email=email, activo=1, es_admin=1 if es_admin else 0, cambiar_clave=1, intentos=0)

    def actualizar_usuario(self, uid: int, nombre: str, email: str, activo: bool, es_admin: bool) -> None:
        if not activo or not es_admin:
            admins = self.db.scalar("SELECT COUNT(*) FROM usuario WHERE es_admin=1 AND activo=1 AND id<>?", (uid,), 0)
            if admins == 0:
                raise ErrorNegocio("Debe quedar al menos un administrador activo.")
        self.db.update("usuario", uid, nombre=nombre, email=email, activo=1 if activo else 0, es_admin=1 if es_admin else 0)

    def cambiar_clave(self, uid: int, nueva: str, forzar_cambio: bool = False) -> None:
        validar_clave(nueva)
        sal = nueva_sal()
        self.db.update("usuario", uid, hash=hash_clave(nueva, sal), salt=sal, cambiar_clave=1 if forzar_cambio else 0, intentos=0)

    def eliminar_usuario(self, uid: int) -> None:
        u = self.usuario(uid)
        if u["es_admin"] and self.db.scalar("SELECT COUNT(*) FROM usuario WHERE es_admin=1 AND activo=1 AND id<>?", (uid,), 0) == 0:
            raise ErrorNegocio("No puede eliminar al último administrador.")
        self.db.delete("usuario", uid)

    # ----------------------------------------------------------------- permisos
    def asignar_empresa(self, uid: int, empresa_id: int, rol: str) -> None:
        with self.db.tx():
            self.db.execute("INSERT INTO usuario_empresa (usuario_id, empresa_id, rol) VALUES (?,?,?) "
                            "ON CONFLICT(usuario_id, empresa_id) DO UPDATE SET rol=excluded.rol", (uid, empresa_id, rol))
            self.db.execute("DELETE FROM permiso WHERE usuario_id=? AND empresa_id=?", (uid, empresa_id))
            for op in permisos_de_rol(rol):
                self.db.execute("INSERT INTO permiso (usuario_id, empresa_id, opcion) VALUES (?,?,?)", (uid, empresa_id, op))

    def quitar_empresa(self, uid: int, empresa_id: int) -> None:
        with self.db.tx():
            self.db.execute("DELETE FROM usuario_empresa WHERE usuario_id=? AND empresa_id=?", (uid, empresa_id))
            self.db.execute("DELETE FROM permiso WHERE usuario_id=? AND empresa_id=?", (uid, empresa_id))

    def guardar_permisos(self, uid: int, empresa_id: int, opciones: list[str]) -> None:
        with self.db.tx():
            self.db.execute("DELETE FROM permiso WHERE usuario_id=? AND empresa_id=?", (uid, empresa_id))
            for op in opciones:
                if op in TODAS:
                    self.db.execute("INSERT INTO permiso (usuario_id, empresa_id, opcion) VALUES (?,?,?)", (uid, empresa_id, op))

    def permisos(self, uid: int, empresa_id: int) -> set[str]:
        u = self.usuario(uid)
        if u and u["es_admin"]:
            return set(TODAS)
        return {r["opcion"] for r in self.db.query("SELECT opcion FROM permiso WHERE usuario_id=? AND empresa_id=?", (uid, empresa_id))}

    def rol(self, uid: int, empresa_id: int) -> str:
        return self.db.scalar("SELECT rol FROM usuario_empresa WHERE usuario_id=? AND empresa_id=?", (uid, empresa_id), "")

    def empresas_de(self, usuario: dict) -> list[dict]:
        if usuario["es_admin"]:
            return self.db.query("SELECT * FROM empresa WHERE activa=1 ORDER BY razon_social")
        return self.db.query("SELECT e.* FROM empresa e JOIN usuario_empresa ue ON ue.empresa_id=e.id "
                             "WHERE ue.usuario_id=? AND e.activa=1 ORDER BY e.razon_social", (usuario["id"],))

    # ----------------------------------------------------------------- empresas
    def crear_empresa(self, datos: dict, anio: int, usuario: dict, correlativo_mensual: bool = True,
                      mes_inicio: int = 1) -> tuple[int, int]:
        codigo = re.sub(r"[^A-Z0-9_]", "", (datos.get("codigo") or "").upper())[:12]
        if not codigo:
            raise ErrorNegocio("Indique un código de empresa (letras y números).")
        if not (datos.get("razon_social") or "").strip():
            raise ErrorNegocio("La razón social es obligatoria.")
        if self.db.scalar("SELECT COUNT(*) FROM empresa WHERE codigo=?", (codigo,)):
            raise ErrorNegocio(f"Ya existe una empresa con el código {codigo}.")
        if not 1990 <= anio <= 2100:
            raise ErrorNegocio("Año de gestión no válido.")
        with self.db.tx():
            eid = self.db.insert(
                "empresa", codigo=codigo, razon_social=datos["razon_social"].strip(), nombre_comercial=datos.get("nombre_comercial", ""),
                nit=datos.get("nit", ""), direccion=datos.get("direccion", ""), ciudad=datos.get("ciudad", ""),
                telefono=datos.get("telefono", ""), email=datos.get("email", ""), actividad=datos.get("actividad", ""),
                rep_legal=datos.get("rep_legal", ""), matricula=datos.get("matricula", ""), carpeta=codigo, activa=1,
                creada_en=datetime.now().isoformat(timespec="seconds"))
            gid = self._crear_gestion(eid, codigo, datos, anio, correlativo_mensual, mes_inicio)
            self.asignar_empresa(usuario["id"], eid, "ADMIN")
        self.auditar(usuario, eid, gid, "Empresas", "CREAR_EMPRESA", f"{codigo} - {datos['razon_social']}")
        return eid, gid

    def _crear_gestion(self, eid: int, codigo: str, datos: dict, anio: int, mensual: bool, mes_inicio: int = 1) -> int:
        inicio = date(anio, mes_inicio, 1)
        fin = date(anio + 1, mes_inicio, 1) if mes_inicio != 1 else date(anio + 1, 1, 1)
        from datetime import timedelta
        fin = fin - timedelta(days=1)
        carpeta = os.path.join(self.raiz, "datos", codigo)
        os.makedirs(carpeta, exist_ok=True)
        archivo = os.path.join(carpeta, f"{anio}.db")
        if os.path.exists(archivo):
            raise ErrorNegocio(f"Ya existe el archivo de la gestión {anio}.")
        gdb = Database(archivo)
        try:
            for stmt in schema.GESTION.split(";\n"):
                if stmt.strip():
                    gdb.execute(stmt)
            sembrar_gestion(gdb, datos, anio)
        finally:
            gdb.close()
        return self.db.insert("gestion", empresa_id=eid, anio=anio, fecha_inicio=inicio.isoformat(), fecha_fin=fin.isoformat(),
                              archivo=os.path.join("datos", codigo, f"{anio}.db"), estado="A",
                              correlativo_mensual=1 if mensual else 0, creada_en=datetime.now().isoformat(timespec="seconds"))

    def nueva_gestion_vacia(self, empresa_id: int, anio: int, mensual: bool = True, mes_inicio: int = 1) -> int:
        e = self.empresa(empresa_id)
        return self._crear_gestion(empresa_id, e["codigo"], {"razon_social": e["razon_social"], "nit": e["nit"],
                                                            "direccion": e["direccion"], "ciudad": e["ciudad"]}, anio, mensual, mes_inicio)

    def empresa(self, eid: int) -> dict:
        return self.db.one("SELECT * FROM empresa WHERE id=?", (eid,))

    def actualizar_empresa(self, eid: int, **vals) -> None:
        permitidas = {"razon_social", "nombre_comercial", "nit", "direccion", "ciudad", "telefono", "email", "actividad", "rep_legal", "matricula"}
        self.db.update("empresa", eid, **{k: v for k, v in vals.items() if k in permitidas})

    def gestiones(self, empresa_id: int) -> list[dict]:
        return self.db.query("SELECT * FROM gestion WHERE empresa_id=? ORDER BY anio DESC", (empresa_id,))

    def gestion(self, gid: int) -> dict:
        return self.db.one("SELECT * FROM gestion WHERE id=?", (gid,))

    def ruta_gestion(self, g: dict) -> str:
        return os.path.join(self.raiz, g["archivo"])

    # --------------------------------------------------------------- contexto
    def abrir_contexto(self, usuario: dict, empresa_id: int, gestion_id: int):
        from .contexto import Contexto
        e = self.empresa(empresa_id)
        g = self.gestion(gestion_id)
        if not e or not g or g["empresa_id"] != empresa_id:
            raise ErrorNegocio("Empresa o gestión no válida.")
        if not usuario["es_admin"] and empresa_id not in {x["id"] for x in self.empresas_de(usuario)}:
            raise ErrorNegocio("No tiene acceso a esta empresa.")
        ruta = self.ruta_gestion(g)
        if not os.path.exists(ruta):
            raise ErrorNegocio(f"No se encuentra el archivo de la gestión:\n{ruta}")
        db = Database(ruta)
        chk = db.integrity_check()
        if chk != "ok":
            db.close()
            raise ErrorNegocio(f"El archivo de datos presenta errores de integridad: {chk}\nRestaure una copia de seguridad.")
        ctx = Contexto(self, usuario, e, g, db)
        self.auditar(usuario, empresa_id, gestion_id, "Sistema", "ABRIR_GESTION", f"{e['codigo']} {g['anio']}")
        return ctx

    # --------------------------------------------------------------- auditoría
    def auditar(self, usuario: dict | None, empresa_id, gestion_id, modulo: str, accion: str, detalle: str = "") -> None:
        try:
            self.db.insert("auditoria", fecha=datetime.now().isoformat(timespec="seconds"),
                           usuario_id=usuario["id"] if usuario else None, login=usuario["login"] if usuario else None,
                           empresa_id=empresa_id, gestion_id=gestion_id, modulo=modulo, accion=accion,
                           detalle=(detalle or "")[:255], equipo=platform.node()[:60])
        except Exception:
            pass

    def auditoria(self, desde=None, hasta=None, limite: int = 2000) -> list[dict]:
        sql = "SELECT * FROM auditoria WHERE 1=1"
        p: list = []
        if desde:
            sql += " AND fecha>=?"
            p.append(iso(desde))
        if hasta:
            sql += " AND fecha<=?"
            p.append(iso(hasta) + "T23:59:59")
        return self.db.query(sql + " ORDER BY id DESC LIMIT ?", p + [limite])

    def close(self) -> None:
        self.db.close()
