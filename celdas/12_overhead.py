# ===== Sobrecosto de medir memoria con tracemalloc (límite declarado de la medición) =====
import time
from IPython.display import Markdown, display

_filas = ["| Caso | Algoritmo | Tiempo con tracemalloc (s) | Tiempo sin medir memoria (s) | Factor |", "|---|---|---|---|---|"]
for _nombre, _k in (("berlin52", 10), ("att48", 10), ("brazil58", 8)):
    _sub = INSTANCES[_nombre].subinstance(_k)
    for _alg, _f in (("A*+MST", astar), ("RBFS+MST", rbfs)):
        _t = {}
        for _medir in (True, False):
            _t0 = time.perf_counter()
            _r = _f(_sub, measure_memory=_medir)
            _t[_medir] = time.perf_counter() - _t0
            assert _r.optimality_status == OPT_PROVEN
        _filas.append("| {0}[k={1}] | {2} | {3:.3f} | {4:.3f} | ×{5:.1f} |".format(
            _nombre, _k, _alg, _t[True], _t[False], _t[True] / _t[False]))
display(Markdown("\n".join(_filas)))
