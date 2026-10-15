# ===== Comparación controlada HC vs. SA (11.1) y primera mejora vs. mejor mejora =====
import statistics
from IPython.display import Markdown, display

# 1) Misma ruta inicial por semilla: HC y SA parten de la misma permutación.
_inst = INSTANCES["eil51"]
filas = ["| semilla | HC (una ruta) | SA | misma ruta inicial |", "|---|---|---|---|"]
for _s in range(5):
    _hc = run_one("HC", _inst, seed=_s, config=FROZEN, scale="B")
    _sa = run_one("SA", _inst, seed=_s, config=FROZEN, scale="B")
    _misma = _hc.extras["initial_route"] == _sa.extras["initial_route"]
    assert _misma
    filas.append("| {0} | {1} ({2}) | {3} ({4}) | {5} |".format(
        _s, _hc.cost, _hc.stop_reason, _sa.cost, _sa.stop_reason, "sí" if _misma else "NO"))
display(Markdown("**eil51 (óptimo 426), 30000 evaluaciones:** costo final por semilla\n\n" + "\n".join(filas)))

# 2) Primera mejora vs. mejor mejora, en una SUBINSTANCIA y por separado de la variante principal.
_sub = INSTANCES["berlin52"].subinstance(30)
_filas = ["| variante | costo mediano (10 semillas) | evaluaciones medianas hasta el óptimo local | paradas |", "|---|---|---|---|"]
for _estrategia in ("best", "first"):
    _costos, _evals, _par = [], [], []
    for _s in range(10):
        _init, _ = make_rngs(_s)
        _r = hill_climbing(_sub, random_tour(_sub.n, _init), Budget(max_evals=30000), strategy=_estrategia)
        _costos.append(_r.cost); _evals.append(_r.candidate_evaluations); _par.append(_r.stop_reason)
    _filas.append("| {0} | {1} | {2} | {3} |".format(
        "mejor mejora" if _estrategia == "best" else "primera mejora",
        statistics.median(_costos), statistics.median(_evals), ", ".join(sorted(set(_par)))))
display(Markdown("**berlin52[k=30]** (subinstancia; no se mezcla con los resultados principales)\n\n" + "\n".join(_filas)))
