# CONTA JB 2.0 (Python)

Sistema contable integrado para Bolivia (comercial y de costos). Python 3 + PySide6 + SQLite.

- Normativa boliviana parametrizada con vigencia: IVA 13 %, IT 3 %, IUE 25 %, RC-IVA, AFP, CNS, Pro-Vivienda, ANS, bono de antigüedad, aguinaldo, indemnización.
- Seis estados financieros: Balance General, Estado de Resultados, Evolución del Patrimonio Neto, Flujo de Efectivo (directo e indirecto) y Notas.
- 79 informes en pantalla, PDF y Excel. Módulos de Auditoría Financiera (MAF) y Tributaria (MAI) con cierre inmutable (SHA-256). Multiempresa y multigestión. Respaldos verificables.

```
pip install -r requirements-dev.txt
python -m pytest            # pruebas automáticas
python -m contabol          # ejecutar
scripts\compilar.bat        # ejecutable + instalador (Windows)
python tools/capturas.py    # regenera capturas reales para los manuales
python tools/generar_manuales.py
```

Manuales (PDF y Word) en `docs/`: *Manual de Implementación* y *Manual de Pruebas*, con capturas reales del aplicativo.

## Ediciones

- **Windows 10/11:** `ContaJB_Setup.exe` (Python 3.12 + PySide6).
- **Windows 7 SP1 (64 bits):** `ContaJB_Setup_Win7.exe` (Python 3.7 + PySide2, `requirements-win7.txt`). Mismas funciones y apariencia.
- **Windows 7 SP1 (32 bits):** `ContaJB_Setup_Win7_32bits.exe` (misma pila, Python 3.7 de 32 bits; `scripts/instalador_win7_32.iss`).
