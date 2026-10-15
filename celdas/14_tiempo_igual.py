# ===== Comparación a TIEMPO igual (preguntas 9 y 10): 2 segundos por ejecución =====
import statistics
from IPython.display import Markdown, display

TIME_BUDGET = 2.0                                 # segundos de reloj por ejecución
TIME_ALGORITHMS = ("HC-restarts", "SA", "GA")
RESULTS_TIME = []
for _nombre in MANDATORY:
    _inst = INSTANCES[_nombre]
    # SA necesita saber su presupuesto para repartir el calendario de enfriamiento. Se mide
    # su velocidad con una corrida piloto (semilla 99, fuera de la evaluación) y se dimensiona
    # el número de evaluaciones para ocupar ≈ 90 % del tiempo. HC con reinicios y GA se
    # limitan directamente por reloj.
    _piloto = run_one("SA", _inst, seed=99, config=FROZEN, scale="B", variant="piloto")
    _rate = _piloto.candidate_evaluations / _piloto.elapsed_seconds
    for _alg in TIME_ALGORITHMS:
        _cfg = frozen_copy()
        _cfg["scale_b"]["max_seconds"] = TIME_BUDGET
        _cfg["scale_b"]["max_evals"] = int(_rate * TIME_BUDGET * 0.9) if _alg == "SA" else 10 ** 9
        for _s in FROZEN["seeds"]:
            RESULTS_TIME.append(run_one(_alg, _inst, seed=_s, config=_cfg, scale="B", variant="tiempo_igual"))

_filas = ["| Instancia | Método | Gap mediano % | Mejor costo | Evaluaciones medianas | Tiempo mediano s |", "|---|---|---|---|---|---|"]
for _nombre in MANDATORY:
    for _alg in TIME_ALGORITHMS:
        _rs = [r for r in RESULTS_TIME if r.instance == _nombre and r.algorithm == _alg]
        _filas.append("| {0} | {1} | {2:.2f} | {3} | {4:.0f} | {5:.2f} |".format(
            _nombre, _alg, statistics.median([r.gap_percent for r in _rs]), min(r.cost for r in _rs),
            statistics.median([r.candidate_evaluations for r in _rs]),
            statistics.median([r.elapsed_seconds for r in _rs])))
display(Markdown("**Dos segundos de reloj por ejecución** (10 semillas por celda; resultados aparte de las tablas principales)\n\n" + "\n".join(_filas)))
