"""Comprueba que un paquete (carpeta dist\\ContaJB) no importe funciones que Windows 7 no tiene.

Recorre todos los .exe/.dll/.pyd, lee su tabla de importaciones y marca las funciones propias de Windows 8/10
(p. ej. WaitOnAddress, ProcessPrng: las usan las bibliotecas escritas en Rust recientes, como `cryptography`).
Si el DLL de la API ya viene dentro del paquete (como los api-ms-win-core-* del runtime universal de C), se considera satisfecho.
Uso:  python tools/verificar_win7.py dist/ContaJB      (código de salida 1 si hay problemas)
"""
from __future__ import annotations

import os
import sys

import pefile

FUNCIONES_WIN8 = {
    "WaitOnAddress", "WakeByAddressSingle", "WakeByAddressAll", "GetSystemTimePreciseAsFileTime", "SetThreadDescription", "GetThreadDescription",
    "GetCurrentPackageFullName", "GetCurrentPackageFamilyName", "CreateFile2", "GetOverlappedResultEx", "DiscardVirtualMemory", "PrefetchVirtualMemory",
    "ProcessPrng", "PathCchCanonicalizeEx", "PathCchCombineEx", "SetProcessMitigationPolicy", "GetDpiForWindow", "SetThreadpoolTimerEx", "SetThreadpoolWaitEx"}
DLLS_WIN8 = ("bcryptprimitives.dll", "api-ms-win-core-synch-l1-2", "api-ms-win-core-winrt", "api-ms-win-core-path-l1-1", "api-ms-win-core-comm", "shcore.dll")


def revisar(raiz: str) -> dict:
    presentes = {f.lower() for _, _, fs in os.walk(raiz) for f in fs}
    hallazgos: dict = {}
    for d, _, fs in os.walk(raiz):
        for f in fs:
            if not f.lower().endswith((".exe", ".dll", ".pyd")):
                continue
            ruta = os.path.join(d, f)
            try:
                pe = pefile.PE(ruta, fast_load=True)
                pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
            except Exception:  # noqa: BLE001
                continue
            for ent in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
                dll = ent.dll.decode().lower()
                if dll in presentes:           # el paquete trae su propia versión
                    continue
                for imp in ent.imports:
                    nombre = (imp.name or b"").decode()
                    if nombre in FUNCIONES_WIN8 or any(dll.startswith(x) for x in DLLS_WIN8):
                        hallazgos.setdefault(os.path.relpath(ruta, raiz), set()).add(f"{dll}!{nombre}")
    return hallazgos


if __name__ == "__main__":
    raiz = sys.argv[1] if len(sys.argv) > 1 else os.path.join("dist", "ContaJB")
    h = revisar(raiz)
    for k, v in sorted(h.items()):
        print("NO COMPATIBLE CON WINDOWS 7:", k, sorted(v)[:5])
    print("Archivos revisados con importaciones de Windows 8+:", len(h))
    sys.exit(1 if h else 0)
