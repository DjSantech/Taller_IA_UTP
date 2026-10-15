# ===== Calibración de SA y GA en instancias DISTINTAS de las de evaluación =====
import statistics
from IPython.display import Markdown, display

CAL_INSTANCES = ["gr17", "burma14", "eil51"]
CAL_SEEDS = tuple(range(100, 105))         # distintas de las semillas 0..9 de la evaluación


def _score(config, algorithm):
    """Gap mediano por instancia (sobre las semillas de calibración) y su promedio."""
    medianas = []
    for nombre in CAL_INSTANCES:
        gaps = [run_one(algorithm, INSTANCES[nombre], seed=s, config=config, scale="B").gap_percent
                for s in CAL_SEEDS]
        medianas.append(statistics.median(gaps))
    return medianas, statistics.mean(medianas)


sa_filas, sa_cand = [], []
for alpha in (0.90, 0.97, 0.995):
    for p0 in (0.5, 0.8):
        cfg = frozen_copy()
        cfg["sa"].update(alpha=alpha, p0=p0)
        meds, score = _score(cfg, "SA")
        sa_cand.append((score, alpha, p0))
        sa_filas.append("| {0} | {1} | {2} | {3:.2f} |".format(
            alpha, p0, " | ".join("{0:.2f}".format(m) for m in meds), score))
SA_BEST = min(sa_cand)

ga_filas, ga_cand = [], []
for pop in (40, 80):
    for elite in (1, 2):
        for pm in (0.1, 0.3):
            cfg = frozen_copy()
            cfg["ga"].update(population_size=pop, elite_count=elite, pm=pm)
            meds, score = _score(cfg, "GA")
            ga_cand.append((score, pop, elite, pm))
            ga_filas.append("| {0} | {1} | {2} | {3} | {4:.2f} |".format(
                pop, elite, pm, " | ".join("{0:.2f}".format(m) for m in meds), score))
GA_BEST = min(ga_cand)

cab = " | ".join("gap mediano % {0}".format(n) for n in CAL_INSTANCES)
display(Markdown("**Calibración de SA** (30000 evaluaciones, semillas 100–104; el enfriamiento ajusta `steps` al presupuesto)\n\n"
                 "| α | p0 | {0} | promedio |\n|---|---|---|---|---|---|\n".format(cab) + "\n".join(sa_filas)))
display(Markdown("**Calibración de GA** (30000 evaluaciones, semillas 100–104, torneo 3, pc = 0.9)\n\n"
                 "| población | élites | pm | {0} | promedio |\n|---|---|---|---|---|---|---|\n".format(cab) + "\n".join(ga_filas)))
display(Markdown("**Configuración elegida** (menor promedio de gap mediano): "
                 "SA con α = {0}, p0 = {1}; GA con población = {2}, élites = {3}, pm = {4}.".format(
                     SA_BEST[1], SA_BEST[2], GA_BEST[1], GA_BEST[2], GA_BEST[3])))

# Congelación: los parámetros quedan fijos ANTES de la evaluación principal. Si esta
# celda se vuelve a ejecutar, debe reproducir la misma elección (semillas fijas).
if FROZEN["sa"]["calibrated"]:
    assert (FROZEN["sa"]["alpha"], FROZEN["sa"]["p0"]) == (SA_BEST[1], SA_BEST[2]), "la calibración de SA cambió"
    assert (FROZEN["ga"]["population_size"], FROZEN["ga"]["elite_count"], FROZEN["ga"]["pm"]) == GA_BEST[1:], \
        "la calibración de GA cambió"
assert_frozen()
