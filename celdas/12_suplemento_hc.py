# ===== Suplemento: ¿cuánto cuesta realmente llegar a un óptimo local con HC? =====
import statistics
from IPython.display import Markdown, display

# (a) Evaluaciones que necesita HC (mejor mejora) hasta su PRIMER óptimo local, sin tope práctico.
filas = ["| Instancia | Pares 2-opt por barrido | Evaluaciones hasta el óptimo local (mediana) | Gap del óptimo local % (mediana) | Veces que 30000 evaluaciones alcanzan |", "|---|---|---|---|---|"]
for _nombre in MANDATORY:
    _inst = INSTANCES[_nombre]
    _ev, _gap = [], []
    for _s in FROZEN["seeds"]:
        _init, _ = make_rngs(_s)
        _r = hill_climbing(_inst, random_tour(_inst.n, _init), Budget(max_evals=5_000_000, max_seconds=120))
        assert _r.stop_reason == "LOCAL_OPTIMUM"
        _ev.append(_r.candidate_evaluations)
        _gap.append(gap_percent(_r.cost, _inst.optimum))
    filas.append("| {0} | {1} | {2:.0f} | {3:.2f} | {4} de 10 |".format(
        _nombre, count_valid_pairs(_inst.n), statistics.median(_ev), statistics.median(_gap),
        sum(1 for e in _ev if e <= 30000)))
display(Markdown("**(a) Costo de llegar al primer óptimo local** (HC mejor mejora, 10 semillas, sin tope práctico de evaluaciones)\n\n" + "\n".join(filas)))

# (b) Dónde sí ayudan los reinicios: instancias pequeñas, donde 30000 evaluaciones alcanzan para varios ascensos.
filas = ["| Instancia | Método | Reinicios (mediana) | Gap mediano % | Ejecuciones que igualan el óptimo |", "|---|---|---|---|---|"]
for _nombre in ("burma14", "gr17"):
    for _alg in ("HC", "HC-restarts"):
        _rs = [run_one(_alg, INSTANCES[_nombre], seed=s, config=FROZEN, scale="B", variant="suplemento")
               for s in FROZEN["seeds"]]
        _rei = [len(r.extras.get("local_optima_costs", [])) or 1 for r in _rs]
        filas.append("| {0} | {1} | {2} | {3:.2f} | {4} de 10 |".format(
            _nombre, _alg, statistics.median(_rei), statistics.median([r.gap_percent for r in _rs]),
            sum(1 for r in _rs if r.cost == INSTANCES[_nombre].optimum)))
display(Markdown("**(b) Reinicios en instancias pequeñas** (30000 evaluaciones, 10 semillas)\n\n" + "\n".join(filas)))
