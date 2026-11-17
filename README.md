# Taller 4: backtracking y el recorrido del caballo

**Curso:** Inteligencia Artificial (IS784, UTP)
**Integrantes:** Santiago Guevara y Januar Mena

Solucionador propio con backtracking para el recorrido del caballo en tableros n×n, en modo abierto y cerrado, con dos estrategias: orden fijo y Warnsdorff. El código respeta el contrato del enunciado: expansiones, presupuesto, traza de eventos y las tres salidas `éxito`, `fracaso` y `límite`.

El entregable es [`Backtracking_Recorrido_del_Caballo.ipynb`](Backtracking_Recorrido_del_Caballo.ipynb), el cuaderno del profesor completado y ejecutado. El primer commit contiene el enunciado intacto.

## Estructura

| Ruta | Contenido |
|---|---|
| `Backtracking_…ipynb` | Cuaderno entregable, generado por `tools/construir_cuaderno.py`, con salidas |
| `caballo/solver.py` | `saltos_legales`, `resolver`, Warnsdorff, modo cerrado y la tabla comparativa |
| `tests/test_solver.py` | Pruebas `pytest`: las del profesor, la prueba adicional y la traza idéntica a `TRAZA_DEMO` |
| `celdas/`, `apuntes/` | Celdas de código y textos propios que se insertan en el cuaderno |
| `tools/` | Construcción del cuaderno y ejecución en un kernel nuevo |
| `BITACORA.md` | Decisiones y errores corregidos |

## Reproducir

```bash
python -m venv C:\Users\<usuario>\venvs\ia-taller4      # fuera de OneDrive
C:\Users\<usuario>\venvs\ia-taller4\Scripts\activate
pip install -r requirements.txt
python -m ipykernel install --user --name ia-taller4 --display-name "Python (ia-taller4)"
python -m pytest tests -q
python tools/construir_cuaderno.py
python tools/ejecutar_cuaderno.py --guardar Backtracking_Recorrido_del_Caballo.ipynb
```

El caso asignado en clase se cambia en la celda del Reto 3, con las variables `ASIGNADO_N`, `ASIGNADO_INICIO` y `ASIGNADO_ROTACION`.

## Ayudas

El docente autorizó el uso de IA declarada. Usamos Claude (mediante Claude Code) como asistente; el detalle está en la portada del cuaderno.
