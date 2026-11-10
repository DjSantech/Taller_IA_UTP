# ===== Experimento 1 EN VIVO: ahorro de busqueda con evaluacion fija (profundidades 1, 2 y 3) =====
# Se re-ejecuta completo aqui (unos segundos a un minuto). run_exp1 comprueba con assert que los
# tres algoritmos dan el MISMO valor y que el tablero queda intacto.
import os
import time

import matplotlib.pyplot as plt
from IPython.display import Markdown, display

_t0 = time.perf_counter()
exp1_filas = run_exp1(depths=(1, 2, 3))
print(f"Experimento 1 re-ejecutado en {time.perf_counter() - _t0:.1f} s "
      f"({len(exp1_filas)} busquedas: 5 posiciones x 3 profundidades x 3 algoritmos).")

_lineas = ["| Posición | d | Algoritmo | Valor | Jugada | Nodos | Hojas | Podas | Tiempo (s) | Ordenar (s) | Nodos / minimax |",
           "|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|"]
for _r in exp1_filas:
    _lineas.append(f"| {_r['position_id']} | {_r['depth']} | {_r['algorithm']} | {_r['value']:+.1f} | "
                   f"{_r['move']} | {_r['nodes']} | {_r['leaves']} | {_r['cutoffs']} | "
                   f"{_r['time_s']:.3f} | {_r['sort_time_s']:.4f} | {_r['nodes_vs_minimax']:.3f} |")
display(Markdown("\n".join(_lineas)))

_lineas = ["| d | Algoritmo | Nodos (5 posiciones) | Hojas | Podas | Tiempo total (s) | de él, ordenar (s) | Nodos / minimax |",
           "|---:|---|---:|---:|---:|---:|---:|---:|"]
for _s in exp1_summary(exp1_filas):
    _lineas.append(f"| {_s['depth']} | {_s['algorithm']} | {_s['nodes']} | {_s['leaves']} | {_s['cutoffs']} | "
                   f"{_s['time_s']:.3f} | {_s['sort_time_s']:.4f} | {_s['nodes_vs_minimax']:.3f} |")
display(Markdown("\n".join(_lineas)))

# Valores y nodos son deterministas: deben coincidir con la corrida guardada (los tiempos no).
_ruta_exp1 = os.path.join("resultados", "exp1_ahorro.csv")
if os.path.exists(_ruta_exp1):
    _guardadas = {(r["position_id"], r["depth"], r["algorithm"]): r for r in exp1_load(_ruta_exp1)}
    _iguales = sum(1 for r in exp1_filas
                   if (k := (r["position_id"], r["depth"], r["algorithm"])) in _guardadas
                   and _guardadas[k]["nodes"] == r["nodes"] and abs(_guardadas[k]["value"] - r["value"]) < 1e-6)
    print(f"Contra resultados/exp1_ahorro.csv: {_iguales}/{len(exp1_filas)} filas con el mismo valor y "
          "los mismos nodos.")
    assert _iguales == len(exp1_filas)
else:
    print("AVISO: aun no existe resultados/exp1_ahorro.csv (lo escribe tools/correr_experimentos.py).")

fig_exp1_nodes(exp1_filas)
plt.show()
