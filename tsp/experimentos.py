# -*- coding: utf-8 -*-
"""Protocolo experimental (secciones 14, 14.1, 15 y 15.1 del enunciado).

Este modulo NO contiene algoritmos: solo orquesta, mide y resume. Los solvers se
importan de forma PEREZOSA dentro de `_solver(...)`, de modo que el modulo se
puede importar y probar (con solvers falsos) antes de que existan los reales, y
de modo que, al concatenar los modulos en el cuaderno, se usen los nombres ya
definidos en el espacio global.

Principios que se aplican aqui:
  * Presupuesto comparable: HC, SA y GA reciben el MISMO tope de evaluaciones de
    candidatos y el mismo tope de tiempo; A*/RBFS reciben limites propios
    (tiempo, expansiones, memoria) porque no se pueden equiparar con evaluaciones.
  * Semillas independientes: `make_rngs(seed)` da un generador para la ruta
    inicial y otro para las decisiones; HC y SA con la misma semilla parten de la
    MISMA ruta inicial.
  * El tiempo de cada ejecucion incluye TODO lo que el metodo necesita (ruta
    inicial y calibracion de T0 en SA): el trabajo de calibracion se descuenta
    del presupuesto y se cuenta en `candidate_evaluations`.
  * Un gap negativo frente a una referencia certificada es una senal de error en
    datos, ruta o costo: se lanza `AuditError` y hay que detenerse a auditar.
"""
import copy
import csv
import importlib
import json
import math
import os
import platform
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from tsp.modelo import (Budget, RunResult, make_rngs, random_tour, gap_percent,
                        tour_cost, tour_problems, STOP_TIME, STOP_EXPANSIONS,
                        STOP_MEMORY, OPT_PROVEN, OPT_NO_ROUTE)

# --- Configuracion congelada ----------------------------------------------------
# Los valores de SA y GA marcados "calibrated": False son PROVISIONALES: el
# coordinador los reemplaza tras la calibracion (datos de calibracion separados
# de los de evaluacion) y pone "calibrated": True. `assert_frozen` lo comprueba
# antes de la corrida final para no publicar resultados con parametros sin fijar.
FROZEN = {
    "seeds": tuple(range(10)),
    "ks": (6, 8, 10, 12),
    "origin": 0,
    "instances": ("att48", "berlin52", "brazil58", "gr48"),
    "exact": {                      # limites de A*/RBFS (seccion 14)
        "max_seconds": 30.0,
        "max_expansions": 100000,
        "max_memory_bytes": 256 * 1024 * 1024,
        "heuristic": "mst",
    },
    # Escala A (subinstancias, k<=12): presupuesto pequeno para los aproximados.
    "scale_a": {"max_evals": 5000, "max_seconds": 30.0, "sa_steps": "auto"},
    # Escala B (instancias completas): 30000 evaluaciones y 30 s por ejecucion.
    "scale_b": {"max_evals": 30000, "max_seconds": 30.0, "sa_steps": "auto"},
    "hc": {"strategy": "best"},
    # Parametros CONGELADOS tras la calibracion (gr17, burma14, eil51; semillas
    # 100-104; ver la celda de calibracion del cuaderno, que los reproduce y
    # verifica). SA: empate con alpha=0.995; se elige el menor alpha.
    "sa": {"p0": 0.8, "alpha": 0.97, "tmin_ratio": 1e-3, "samples": 200,
           "window": 500, "calibrated": True},
    "ga": {"population_size": 40, "elite_count": 2, "pc": 0.9, "pm": 0.3,
           "tournament_size": 3, "calibrated": True},
}

EXACT_ALGORITHMS = ("A*+MST", "RBFS+MST")
APPROX_ALGORITHMS = ("HC", "HC-restarts", "SA", "GA")
ALGORITHMS = EXACT_ALGORITHMS + APPROX_ALGORITHMS
# Etiquetas de la plantilla 15.1 (mismo orden que ALGORITHMS).
TABLE_LABELS = {"A*+MST": "A* + MST", "RBFS+MST": "RBFS + MST", "HC": "HC una ruta",
                "HC-restarts": "HC reinicios", "SA": "SA", "GA": "GA básico"}
# Parada por LIMITE de recursos (censura). EVAL_LIMIT no cuenta: es el presupuesto
# de diseno de los metodos locales, no una interrupcion.
LIMIT_REASONS = (STOP_TIME, STOP_EXPANSIONS, STOP_MEMORY)

# Columnas extra que este modulo agrega a cada RunResult (viajan en `.row()`).
EXTRA_COLUMNS = ("scale", "k", "repetition", "variant", "reference", "reference_source")


class AuditError(Exception):
    """Hallazgo que obliga a detenerse y auditar (gap negativo, ruta invalida,
    costo incoherente, optimo certificado contradictorio)."""


def frozen_copy(**overrides):
    """Copia profunda de FROZEN (para pruebas o presupuestos reducidos)."""
    cfg = copy.deepcopy(FROZEN)
    cfg.update(overrides)
    return cfg


def assert_frozen(config=None):
    """Falla si SA o GA siguen con parametros provisionales."""
    config = config or FROZEN
    for clave in ("sa", "ga"):
        if not config[clave].get("calibrated"):
            raise AuditError("Los parametros de {0} no estan congelados "
                             "(calibrated=False).".format(clave.upper()))
    return True


# --- Solvers (importacion perezosa) ----------------------------------------------
_SOLVER_HOME = {
    "astar": ("astar", "astar"),
    "rbfs": ("rbfs", "rbfs"),
    "hill_climbing": ("hc", "hill_climbing"),
    "hill_climbing_restarts": ("hc", "hill_climbing_restarts"),
    "calibrate_t0": ("sa", "calibrate_t0"),
    "simulated_annealing": ("sa", "simulated_annealing"),
    "genetic_algorithm": ("ga", "genetic_algorithm"),
}


def _solver(key, solvers=None):
    """Devuelve el solver `key`: primero el inyectado (pruebas), luego el nombre
    ya definido en el espacio global (cuaderno), por ultimo el modulo `tsp.*`."""
    if solvers and key in solvers:
        return solvers[key]
    modulo, atributo = _SOLVER_HOME[key]
    en_global = globals().get(atributo)
    if callable(en_global):
        return en_global
    try:
        return getattr(importlib.import_module("tsp." + modulo), atributo)
    except ImportError as error:
        raise ImportError("Falta el modulo tsp.{0} ({1}).".format(modulo, error))


# --- Subinstancias --------------------------------------------------------------
def select_subinstance(inst, k):
    """Primeros k identificadores ORDENADOS (pesos originales). Devuelve
    (subinstancia, listado de identificadores reales): el listado se registra, no
    solo el tamano, porque el optimo del subproblema depende de ESOS nodos."""
    sub = inst.subinstance(k)
    return sub, tuple(sub.node_ids)


def exact_optimum_dp(D, origin=0):
    """Optimo exacto por programacion dinamica de Held-Karp (n pequeno). Sirve
    como certificado independiente de A*/RBFS para k<=10: no comparte codigo con
    ellos, asi un error comun no se cancela."""
    n = len(D)
    if n == 1:
        return 0
    others = [c for c in range(n) if c != origin]
    m = len(others)
    inf = float("inf")
    dp = [[inf] * m for _ in range(1 << m)]
    for j in range(m):
        dp[1 << j][j] = D[origin][others[j]]
    for mask in range(1, 1 << m):
        for j in range(m):
            actual = dp[mask][j]
            if actual == inf or not (mask >> j) & 1:
                continue
            for t in range(m):
                if (mask >> t) & 1:
                    continue
                nuevo = actual + D[others[j]][others[t]]
                nm = mask | (1 << t)
                if nuevo < dp[nm][t]:
                    dp[nm][t] = nuevo
    full = (1 << m) - 1
    return min(dp[full][j] + D[others[j]][origin] for j in range(m))


# --- Una ejecucion --------------------------------------------------------------
def _tag(res, scale, k, repetition, variant, reference, reference_source):
    res.scale = scale
    res.k = k
    res.repetition = repetition
    res.variant = variant
    res.reference = reference
    res.reference_source = reference_source
    return res


def _audit(res, inst, origin, reference):
    """Auditoria obligatoria de cada resultado (seccion 15)."""
    if res.tour is None:
        if res.cost is not None or res.gap_percent is not None:
            raise AuditError("Sin ruta pero con costo/gap: {0} {1}".format(
                res.instance, res.algorithm))
        return
    problemas = tour_problems(res.tour, inst.n, origin)
    if problemas:
        raise AuditError("Ruta invalida de {0} (semilla {1}): {2}".format(
            res.algorithm, res.seed, problemas))
    if res.cost != tour_cost(inst.D, res.tour):
        raise AuditError("Costo incoherente de {0}: informa {1}, recalculado {2}".format(
            res.algorithm, res.cost, tour_cost(inst.D, res.tour)))
    if reference is not None:
        g = gap_percent(res.cost, reference)
        if g < -1e-9:
            raise AuditError(
                "GAP NEGATIVO ({0:.4f}%) de {1} en {2}, semilla {3}: costo {4} < "
                "referencia {5}. Detenerse y auditar datos, ruta y costo.".format(
                    g, res.algorithm, res.instance, res.seed, res.cost, reference))
        if res.optimality_status == OPT_PROVEN and res.cost != reference:
            raise AuditError("{0} declara optimo {1} pero la referencia certificada "
                             "es {2} ({3}).".format(res.algorithm, res.cost,
                                                    reference, res.instance))


def run_one(algorithm, inst, seed=None, config=None, scale="B", origin=0,
            reference=None, reference_source=None, repetition=1, variant="main",
            keep_history=False, solvers=None):
    """Ejecuta UN metodo de la tabla 15.1 sobre `inst` y devuelve un RunResult
    completo y auditado.

    reference: optimo certificado contra el que se calcula el gap. Si es None se
    usa el optimo oficial de la instancia completa; en subinstancias NO hay
    referencia por omision (su optimo no es el oficial) y el gap queda en None.
    """
    if algorithm not in ALGORITHMS:
        raise ValueError("Algoritmo desconocido: {0}".format(algorithm))
    config = config or FROZEN
    sc = config["scale_" + scale.lower()]
    es_exacto = algorithm in EXACT_ALGORITHMS
    if not es_exacto and origin != 0:
        raise ValueError("Los metodos locales fijan el origen en la posicion 0.")
    if not es_exacto and seed is None:
        raise ValueError("Los metodos aproximados requieren semilla.")
    if reference is None and inst.parent is None and inst.optimum is not None:
        reference, reference_source = inst.optimum, "oficial TSPLIB"

    t0 = time.perf_counter()                      # el cronometro abarca todo el metodo
    if es_exacto:
        ex = config["exact"]
        budget = Budget(max_seconds=ex["max_seconds"], max_expansions=ex["max_expansions"],
                        max_memory_bytes=ex["max_memory_bytes"])
        clave = "astar" if algorithm == "A*+MST" else "rbfs"
        res = _solver(clave, solvers)(inst, origin=origin, budget=budget,
                                      heuristic=ex["heuristic"])
        mine = {"origin": origin, "max_seconds": ex["max_seconds"],
                "max_expansions": ex["max_expansions"],
                "max_memory_bytes": ex["max_memory_bytes"], "heuristic": ex["heuristic"]}
    else:
        init_rng, algo_rng = make_rngs(seed)
        mine = {"max_evals": sc["max_evals"], "max_seconds": sc["max_seconds"]}
        if algorithm == "HC-restarts":
            budget = Budget(max_evals=sc["max_evals"], max_seconds=sc["max_seconds"])
            res = _solver("hill_climbing_restarts", solvers)(
                inst, init_rng, budget, strategy=config["hc"]["strategy"])
            mine["strategy"] = config["hc"]["strategy"]
        elif algorithm == "GA":
            g = config["ga"]
            budget = Budget(max_evals=sc["max_evals"], max_seconds=sc["max_seconds"])
            res = _solver("genetic_algorithm", solvers)(
                inst, budget, algo_rng, population_size=g["population_size"],
                elite_count=g["elite_count"], pc=g["pc"], pm=g["pm"],
                tournament_size=g["tournament_size"], origin=0)
            mine.update({k: g[k] for k in ("population_size", "elite_count", "pc", "pm",
                                           "tournament_size")})
        else:
            # HC y SA parten de la MISMA ruta inicial (mismo generador, misma semilla).
            initial = random_tour(inst.n, init_rng, 0)
            if algorithm == "HC":
                budget = Budget(max_evals=sc["max_evals"], max_seconds=sc["max_seconds"])
                res = _solver("hill_climbing", solvers)(
                    inst, initial, budget, strategy=config["hc"]["strategy"],
                    keep_history=keep_history)
                mine["strategy"] = config["hc"]["strategy"]
            else:
                res = _run_sa(inst, initial, algo_rng, config, sc, keep_history,
                              solvers, mine)
            res.extras.setdefault("initial_route", list(initial))
    res.elapsed_seconds = time.perf_counter() - t0   # tiempo total, no el interno
    res.seed = seed
    res.subset = tuple(inst.node_ids) if inst.parent is not None else None
    res.parameters = dict(res.parameters or {}, **mine)
    res.gap_percent = gap_percent(res.cost, reference)
    _audit(res, inst, origin if es_exacto else 0, reference)
    if res.tour is None:
        res.optimality_status = OPT_NO_ROUTE
    return _tag(res, scale, inst.n, repetition, variant, reference, reference_source)


def _run_sa(inst, initial, algo_rng, config, sc, keep_history, solvers, mine):
    """SA con calibracion de T0 CONTADA: sus evaluaciones y su tiempo se descuentan
    del presupuesto y se suman al resultado (seccion 11 y 14.1)."""
    p = config["sa"]
    tc = time.perf_counter()
    T0, calib_evals = _solver("calibrate_t0", solvers)(inst, initial, algo_rng,
                                                        p["p0"], samples=p["samples"])
    calib_secs = time.perf_counter() - tc
    budget = Budget(max_evals=max(1, sc["max_evals"] - calib_evals),
                    max_seconds=max(1e-3, sc["max_seconds"] - calib_secs))
    Tmin = T0 * p["tmin_ratio"]
    steps = sc["sa_steps"]
    if steps == "auto":
        # Hallazgo de calibracion: con `steps` fijo y alpha cercano a 1, SA agota el
        # presupuesto sin enfriar. Se reparte el presupuesto entre los niveles de
        # temperatura que hay hasta Tmin: ceil(ln(tmin_ratio)/ln(alpha)).
        niveles = max(1, math.ceil(math.log(p["tmin_ratio"]) / math.log(p["alpha"])))
        steps = max(1, budget.max_evals // niveles)
    res = _solver("simulated_annealing", solvers)(
        inst, initial, budget, algo_rng, T0, Tmin, p["alpha"], steps,
        keep_history=keep_history, window=p["window"])
    res.candidate_evaluations += calib_evals
    # La traza se desplaza para que el eje de evaluaciones/tiempo incluya la calibracion.
    res.trace = [(e + calib_evals, c, s + calib_secs) for (e, c, s) in res.trace]
    if res.extras.get("series_evals"):
        res.extras["series_evals"] = [e + calib_evals for e in res.extras["series_evals"]]
    res.extras["calibration_evals"] = calib_evals
    res.extras["calibration_seconds"] = calib_secs
    res.extras["T0"] = T0
    mine.update({"p0": p["p0"], "alpha": p["alpha"], "T0": T0, "Tmin": Tmin,
                 "steps": steps, "window": p["window"],
                 "calibration_evals": calib_evals})
    return res


# --- Orquestacion -----------------------------------------------------------------
def _execute_job(job, config, solvers=None):
    return run_one(job["algorithm"], job["inst"], seed=job.get("seed"), config=config,
                   scale=job["scale"], origin=job.get("origin", 0),
                   reference=job.get("reference"),
                   reference_source=job.get("reference_source"),
                   repetition=job.get("repetition", 1), variant=job.get("variant", "main"),
                   keep_history=job.get("keep_history", False), solvers=solvers)


def _pool_job(args):                     # nivel de modulo: debe ser serializable
    job, config = args
    return _execute_job(job, config)


def _run_jobs(jobs, config, workers, solvers, progress, counter):
    """Ejecuta los trabajos y devuelve los resultados EN EL MISMO ORDEN que `jobs`.

    Por omision va en SERIE (workers=1). Con varios procesos el orden sigue siendo
    determinista, pero el tiempo medido puede inflarse: los procesos compiten por
    CPU, cache y memoria, asi que las comparaciones de tiempo de la corrida final
    deben hacerse en serie. Los solvers inyectados solo funcionan en serie."""
    out = []
    if workers and workers > 1:
        if solvers:
            raise ValueError("Los solvers inyectados no son compatibles con procesos.")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for r in pool.map(_pool_job, [(j, config) for j in jobs]):
                out.append(r)
                counter[0] += 1
                if progress:
                    progress(counter[0], counter[1], "{0} {1}".format(r.instance, r.algorithm))
    else:
        for j in jobs:
            r = _execute_job(j, config, solvers)
            out.append(r)
            counter[0] += 1
            if progress:
                progress(counter[0], counter[1], "{0} {1}".format(r.instance, r.algorithm))
    return out


def _as_inst_list(instances):
    return list(instances.values()) if isinstance(instances, dict) else list(instances)


def _certify(sub, exact_main):
    """Optimo certificado del SUBPROBLEMA: A*/RBFS si terminaron sin interrupcion,
    o enumeracion (Held-Karp) si k<=10. Devuelve (valor, fuente) o (None, None).
    Si dos certificados chocan es un error de implementacion: AuditError."""
    cert = {}
    for r in exact_main:
        if r.optimality_status == OPT_PROVEN and r.cost is not None:
            cert[r.algorithm] = r.cost
    if sub.n <= 10:
        cert["enumeracion (Held-Karp)"] = exact_optimum_dp(sub.D, 0)
    if not cert:
        return None, None
    if len(set(cert.values())) > 1:
        raise AuditError("Optimos certificados contradictorios en {0}: {1}".format(
            sub.name, cert))
    fuente = " = ".join(sorted(cert))
    return next(iter(cert.values())), fuente


def run_scale_a(instances, ks=None, seeds=None, config=None, timing_repeats=1,
                check_origin=True, algorithms=None, progress=None, workers=1,
                solvers=None):
    """Escala A: subinstancias de k nodos de cada instancia (seccion 14).

    * A*/RBFS: una ejecucion por caso (+ repeticiones solo de TIEMPO si
      timing_repeats>1) y, si check_origin, una ejecucion extra con otro origen
      (k-1) cuyo costo debe coincidir (invarianza); si no, AuditError.
    * Aproximados: una ejecucion por semilla (0..9 por omision).
    * El gap se calcula frente al optimo del SUBPROBLEMA, solo si fue certificado.
    Devuelve la lista de RunResult en orden determinista, con columnas extra
    scale, k, repetition, variant, reference, reference_source."""
    config = config or FROZEN
    ks = tuple(ks or config["ks"])
    seeds = tuple(config["seeds"] if seeds is None else seeds)
    algos = tuple(algorithms or ALGORITHMS)
    cases = []
    for inst in _as_inst_list(instances):
        for k in ks:
            sub, _ = select_subinstance(inst, k)
            cases.append(sub)

    # Fase 1: exactos (de ellos sale el certificado que necesitan los aproximados).
    jobs1, owners1 = [], []
    for sub in cases:
        for alg in (a for a in EXACT_ALGORITHMS if a in algos):
            for rep in range(1, timing_repeats + 1):
                jobs1.append({"algorithm": alg, "inst": sub, "scale": "A", "repetition": rep})
                owners1.append(sub.name)
            if check_origin and sub.n >= 3:
                jobs1.append({"algorithm": alg, "inst": sub, "scale": "A", "origin": sub.n - 1,
                              "variant": "origin"})
                owners1.append(sub.name)
    n_aprox = len([a for a in algos if a in APPROX_ALGORITHMS])
    counter = [0, len(jobs1) + len(cases) * n_aprox * len(seeds)]
    res1 = _run_jobs(jobs1, config, workers, solvers, progress, counter)

    por_caso = {sub.name: [] for sub in cases}
    for owner, r in zip(owners1, res1):
        por_caso[owner].append(r)
    refs = {}
    for sub in cases:
        main = [r for r in por_caso[sub.name] if r.variant == "main"]
        refs[sub.name] = _certify(sub, main)
        if check_origin:                       # invarianza del costo respecto al origen
            for r in por_caso[sub.name]:
                if r.variant != "origin" or r.optimality_status != OPT_PROVEN:
                    continue
                base = [m for m in main if m.algorithm == r.algorithm
                        and m.optimality_status == OPT_PROVEN]
                if base and base[0].cost != r.cost:
                    raise AuditError("El costo optimo cambia con el origen en {0} ({1}): "
                                     "{2} vs {3}".format(sub.name, r.algorithm,
                                                         base[0].cost, r.cost))

    # Fase 2: aproximados con la referencia certificada (o sin ella).
    jobs2, owners2 = [], []
    for sub in cases:
        ref, src = refs[sub.name]
        for alg in (a for a in APPROX_ALGORITHMS if a in algos):
            for s in seeds:
                jobs2.append({"algorithm": alg, "inst": sub, "seed": s, "scale": "A",
                              "reference": ref, "reference_source": src})
                owners2.append(sub.name)
    res2 = _run_jobs(jobs2, config, workers, solvers, progress, counter)
    for owner, r in zip(owners2, res2):
        por_caso[owner].append(r)

    # Los exactos tambien llevan la referencia en su columna (su gap es 0 si certifican).
    out = []
    for sub in cases:
        ref, src = refs[sub.name]
        for r in por_caso[sub.name]:
            if r.algorithm in EXACT_ALGORITHMS and r.reference is None:
                r.reference, r.reference_source = ref, src
                r.gap_percent = gap_percent(r.cost, ref)
                _audit(r, sub, r.parameters.get("origin", 0), ref)
            out.append(r)
    return out


def run_scale_b(instances, seeds=None, config=None, algorithms=None, progress=None,
                workers=1, solvers=None):
    """Escala B: instancias completas (seccion 14). HC, HC-reinicios, SA y GA con
    10 semillas; A* y RBFS un unico ensayo diagnostico (sin exigir ruta ni
    optimalidad). Orden determinista: instancia, algoritmo, semilla."""
    config = config or FROZEN
    seeds = tuple(config["seeds"] if seeds is None else seeds)
    algos = tuple(algorithms or ALGORITHMS)
    jobs = []
    for inst in _as_inst_list(instances):
        for alg in algos:
            if alg in EXACT_ALGORITHMS:
                jobs.append({"algorithm": alg, "inst": inst, "scale": "B"})
            else:
                for s in seeds:
                    jobs.append({"algorithm": alg, "inst": inst, "seed": s, "scale": "B"})
    return _run_jobs(jobs, config, workers, solvers, progress, [0, len(jobs)])


# --- Registros: CSV y JSON ---------------------------------------------------------
_INT_FIELDS = {"seed", "cost", "peak_memory", "candidate_evaluations", "expanded",
               "generated", "mst_calls", "frontier_peak", "regenerations", "k",
               "repetition", "reference"}
_FLOAT_FIELDS = {"gap_percent", "elapsed_seconds"}
_BOOL_FIELDS = {"fallback_route"}
_NULLABLE_TEXT = {"subset", "tour", "scale", "variant", "reference_source"}


def _all_columns(rows):
    base = [k for k in RunResult("x", "x").row().keys()]
    extra = [c for c in EXTRA_COLUMNS if any(c in r for r in rows)]
    otros = sorted({k for r in rows for k in r} - set(base) - set(extra))
    return base + extra + otros


def save_rows_csv(results, path):
    """Guarda una fila por ejecucion (tour/subset/parameters como texto)."""
    rows = [r.row() if isinstance(r, RunResult) else dict(r) for r in results]
    cols = _all_columns(rows)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c) for c in cols})
    return path


def load_rows_csv(path):
    """Lee el CSV y restituye tipos (int, float, bool, None). El resultado es
    igual a `[r.row() for r in results]` de lo que se guardo."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            row = {}
            for c, v in raw.items():
                if v == "" or v is None:
                    row[c] = None if (c in _INT_FIELDS or c in _FLOAT_FIELDS
                                      or c in _NULLABLE_TEXT) else ""
                elif c in _INT_FIELDS:
                    row[c] = int(v)
                elif c in _FLOAT_FIELDS:
                    row[c] = float(v)
                elif c in _BOOL_FIELDS:
                    row[c] = (v == "True")
                else:
                    row[c] = v
            rows.append(row)
    return rows


def save_results_json(results, path):
    """Guarda los RunResult COMPLETOS (con trace y extras): las curvas de
    convergencia salen de aqui, el CSV plano no las contiene."""
    def limpio(o):
        if isinstance(o, dict):
            return {str(k): limpio(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [limpio(v) for v in o]
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            return None
        return o
    data = []
    for r in results:
        d = dict(r.__dict__)
        d["subset"] = None if r.subset is None else list(r.subset)
        data.append(limpio(d))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def load_results_json(path):
    """Reconstruye RunResult (trace como lista de tuplas) con sus columnas extra."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for d in data:
        d = dict(d)
        d["trace"] = [tuple(p) for p in d.get("trace", [])]
        if d.get("subset") is not None:
            d["subset"] = tuple(d["subset"])
        campos = RunResult.__dataclass_fields__
        r = RunResult(**{k: v for k, v in d.items() if k in campos})
        for k, v in d.items():
            if k not in campos:
                setattr(r, k, v)
        out.append(r)
    return out


# --- Resumen (seccion 15) -------------------------------------------------------------
def _rows(results):
    return [r.row() if isinstance(r, RunResult) else r for r in results]


def _stats(vals):
    if not vals:
        return None, None, None
    sd = statistics.stdev(vals) if len(vals) > 1 else None   # muestral (n-1)
    return statistics.median(vals), statistics.mean(vals), sd


def summarize(results):
    """Resumen por (instancia, algoritmo). Acepta RunResult o filas de CSV.

    * Las filas con variant=="origin" (prueba de invarianza) se excluyen.
    * `planned` = ejecuciones previstas (repetition 1 de cada semilla/caso): el
      denominador SIEMPRE se informa; `valid` = las que devolvieron ruta.
    * Costo y gap se calculan solo sobre ejecuciones con ruta (None = N/A).
    * El tiempo usa todas las repeticiones de tiempo; `censored` cuenta paradas por
      limite de tiempo/expansiones/memoria."""
    grupos = {}
    for r in _rows(results):
        if r.get("variant") == "origin":
            continue
        grupos.setdefault((r["instance"], r["algorithm"]), []).append(r)
    orden = {a: i for i, a in enumerate(ALGORITHMS)}
    out = []
    for (inst, alg) in sorted(grupos, key=lambda x: (x[0], orden.get(x[1], 99))):
        todas = grupos[(inst, alg)]
        previstas = [r for r in todas if (r.get("repetition") or 1) == 1]
        validas = [r for r in previstas if r.get("tour") is not None]
        costos = [r["cost"] for r in validas if r.get("cost") is not None]
        gaps = [r["gap_percent"] for r in validas if r.get("gap_percent") is not None]
        cmed, cmean, csd = _stats(costos)
        gmed, gmean, gsd = _stats(gaps)
        ref = next((r["reference"] for r in previstas if r.get("reference") is not None), None)
        aciertos = [r for r in validas if ref is not None and r["cost"] == ref]
        motivos = Counter(r.get("stop_reason", "") for r in previstas)
        dominante = sorted(motivos.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if motivos else None
        out.append({
            "instance": inst, "algorithm": alg,
            "planned": len(previstas), "valid": len(validas),
            "censored": sum(1 for r in previstas if r.get("stop_reason") in LIMIT_REASONS),
            "best_cost": min(costos) if costos else None,
            "cost_median": cmed, "cost_mean": cmean, "cost_std": csd,
            "gap_median": gmed, "gap_mean": gmean, "gap_std": gsd,
            "time_median": statistics.median([r["elapsed_seconds"] for r in todas
                                              if r.get("elapsed_seconds") is not None])
            if todas else None,
            "match_rate": (len(aciertos) / len(validas)) if (ref is not None and validas) else None,
            "predominant_reason": dominante,
            "peak_memory_max": max((r.get("peak_memory") or 0) for r in todas),
            "reference": ref,
        })
    return out


def _fmt(x, nd=2):
    if x is None:
        return "N/A"
    if isinstance(x, float):
        return "{0:.{1}f}".format(x, nd)
    return str(x)


def _fmt_bytes(b):
    if b is None:
        return "N/A"
    if b == 0:
        return "no medida"          # el solver no reporto memoria (p. ej. metodos locales)
    if b >= 1024 ** 2:
        return "{0:.1f} MiB".format(b / 1024 ** 2)
    if b >= 1024:
        return "{0:.1f} KiB".format(b / 1024)
    return "{0} B".format(b)


def table_methods(summary, instance):
    """Plantilla 15.1 (por instancia): una fila por metodo, siempre los 6 metodos."""
    por_alg = {s["algorithm"]: s for s in summary if s["instance"] == instance}
    lineas = ["| Método | Repeticiones válidas/previstas | Mejor costo | Gap mediano % | "
              "Tiempo mediano s | Memoria máxima | Motivo predominante |",
              "|---|---|---|---|---|---|---|"]
    for alg in ALGORITHMS:
        s = por_alg.get(alg)
        if s is None:
            lineas.append("| {0} | — | — | — | — | — | — |".format(TABLE_LABELS[alg]))
            continue
        censura = " (censuradas: {0})".format(s["censored"]) if s["censored"] else ""
        lineas.append("| {0} | {1}/{2}{3} | {4} | {5} | {6} | {7} | {8} |".format(
            TABLE_LABELS[alg], s["valid"], s["planned"], censura, _fmt(s["best_cost"]),
            _fmt(s["gap_median"], 3), _fmt(s["time_median"], 4),
            _fmt_bytes(s["peak_memory_max"]), s["predominant_reason"] or "N/A"))
    return "\n".join(lineas)


def table_subinstances(results):
    """Plantilla 15.1 para subinstancias: nodos seleccionados, optimo certificado,
    expansiones y memoria de A* y RBFS (marca 'interrumpido' si hubo censura)."""
    casos = {}
    for r in _rows(results):
        if r.get("subset") is None or r["algorithm"] not in EXACT_ALGORITHMS:
            continue
        if r.get("variant") == "origin" or (r.get("repetition") or 1) != 1:
            continue
        casos.setdefault(r["instance"], {})[r["algorithm"]] = r
    lineas = ["| Instancia | Nodos seleccionados | k | Óptimo certificado | "
              "Expansiones A* | Expansiones RBFS | Memoria A* | Memoria RBFS |",
              "|---|---|---|---|---|---|---|---|"]
    for nombre in sorted(casos, key=lambda n: (n.split("[")[0], casos[n][next(iter(casos[n]))].get("k") or 0)):
        a, b = casos[nombre].get("A*+MST"), casos[nombre].get("RBFS+MST")
        ref = next((x for x in (a, b) if x is not None and x.get("reference") is not None), None)
        ejemplo = a or b

        def exp(x):
            if x is None:
                return "—"
            return "{0}{1}".format(x["expanded"], " (interrumpido)" if x.get("stop_reason") in LIMIT_REASONS else "")

        def mem(x):
            return "—" if x is None else _fmt_bytes(x.get("peak_memory"))
        optimo = "N/A" if ref is None else "{0} ({1})".format(ref["reference"], ref.get("reference_source"))
        lineas.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} |".format(
            nombre, ejemplo["subset"].replace(" ", ","), ejemplo.get("k"), optimo,
            exp(a), exp(b), mem(a), mem(b)))
    return "\n".join(lineas)


# --- Entorno (seccion A del cuaderno) --------------------------------------------------
def environment_report():
    """Diccionario con CPU, SO, Python, paquetes y herramienta de memoria."""
    from importlib import metadata
    paquetes = {}
    for p in ("numpy", "matplotlib", "pillow", "tsplib95", "ipykernel", "nbformat",
              "nbclient", "pytest", "psutil"):
        try:
            paquetes[p] = metadata.version(p)
        except Exception:
            paquetes[p] = "no instalado"
    cpu = platform.processor() or platform.machine()
    ram = None
    try:
        import psutil
        ram = psutil.virtual_memory().total
        fisicos = psutil.cpu_count(logical=False)
    except Exception:
        fisicos = None
    if "google.colab" in sys.modules:
        entorno = "Google Colab"
    elif "ipykernel" in sys.modules:
        entorno = "Jupyter (ipykernel)"
    else:
        entorno = "Python en consola / pytest"
    return {
        "cpu": cpu, "nucleos_logicos": os.cpu_count(), "nucleos_fisicos": fisicos,
        "ram_total_bytes": ram,
        "sistema_operativo": "{0} {1} ({2})".format(platform.system(), platform.release(),
                                                    platform.version()),
        "python": platform.python_version(), "implementacion": platform.python_implementation(),
        "entorno": entorno, "paquetes": paquetes,
        "resolucion_reloj": time.get_clock_info("perf_counter").resolution,
        "memoria": ("tracemalloc: mide solo asignaciones de Python, de forma INCREMENTAL "
                    "respecto al inicio del solver; no es la memoria del proceso completo "
                    "(no incluye la matriz D cargada antes ni memoria de extensiones en C)."),
    }


def format_environment(report=None):
    """Version en Markdown de `environment_report()`."""
    r = report or environment_report()
    lineas = ["| Elemento | Valor |", "|---|---|",
              "| CPU | {0} ({1} núcleos lógicos, {2} físicos) |".format(
                  r["cpu"], r["nucleos_logicos"], _fmt(r["nucleos_fisicos"])),
              "| RAM total | {0} |".format(_fmt_bytes(r["ram_total_bytes"])),
              "| Sistema operativo | {0} |".format(r["sistema_operativo"]),
              "| Python | {0} {1} |".format(r["implementacion"], r["python"]),
              "| Entorno | {0} |".format(r["entorno"]),
              "| Reloj | perf_counter, resolución {0:.1e} s |".format(r["resolucion_reloj"]),
              "| Memoria | {0} |".format(r["memoria"])]
    for p, v in r["paquetes"].items():
        lineas.append("| {0} | {1} |".format(p, v))
    return "\n".join(lineas)
