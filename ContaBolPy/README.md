# ContaBol 2.0 (Python)

Sistema contable integrado para Bolivia (comercial y de costos). Python 3 + PySide6 + SQLite.

- Normativa boliviana parametrizada con vigencia: IVA 13 %, IT 3 %, IUE 25 %, RC-IVA, AFP, CNS, Pro-Vivienda, ANS, bono de antigüedad, aguinaldo, indemnización.
- Seis estados financieros: Balance General, Estado de Resultados, Evolución del Patrimonio Neto, Flujo de Efectivo (directo e indirecto) y Notas.
- 65 informes en pantalla, PDF y Excel. Multiempresa y multigestión. Respaldos verificables.

```
pip install -r requirements-dev.txt
python -m pytest            # pruebas automáticas
python -m contabol          # ejecutar
scripts\compilar.bat        # ejecutable + instalador (Windows)
python tools/capturas.py    # regenera capturas reales para los manuales
python tools/generar_manuales.py
```

Manuales (PDF y Word) en `docs/`: *Manual de Implementación* y *Manual de Pruebas*, con capturas reales del aplicativo.
