# -*- coding: utf-8 -*-
"""Pruebas del protocolo experimental y de las graficas.

La mayoria usa solvers FALSOS inyectables (parametro `solvers`), de modo que el
protocolo se prueba aunque los algoritmos reales no existan. Las pruebas de
integracion con los solvers reales se omiten (skip) si falta el modulo.
"""
import importlib.util
import random

import matplotlib
matplotlib.use("Agg")                    # solo en las pruebas: sin ventanas
import matplotlib.pyplot as plt
import pytest

from tsp.datos import load_by_name
from tsp.modelo import (RunResult, tour_cost, random_tour, STOP_EVALS, STOP_TIME, STOP_GENERATIONS,
                        STOP_COOLED, STOP_LOCAL_OPT, STOP_OPTIMAL, OPT_PROVEN, OPT_NO_ROUTE)
from tsp import experimentos as ex
from tsp import graficas as gf
from tests.oraculo import brute_force


@pytest.fixture(scope="module")
def gr17():
    return load_by_name("gr17")


@pytest.fixture(scope="module")
def burma():
    return load_by_name("burma14")        # trae coordenadas (dibujo geografico)


# --- Solvers falsos (mismas firmas que el contrato) ---------------------------------
def _climb(inst, route, rng, n_evals, history=None):
    """Busqueda local minima: n_evals movimientos 2-opt aleatorios, acepta mejoras."""
    route = list(route)
    cost = tour_cost(inst.D, route)
    trace = [(0, cost, 0.0)]
    for e in range(1, n_evals + 1):
        i, j = sorted(rng.sample(range(1, inst.n), 2))
        cand = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
        c = tour_cost(inst.D, cand)
        if c < cost:
            route, cost = cand, c
            trace.append((e, cost, 0.001 * e))
            if history is not None:
                history.append((list(route), cost, e))
    trace.append((n_evals, cost, 0.001 * n_evals))
    return route, cost, trace


def _res(inst, name, route, cost, trace, evals, stop, extras=None):
    return RunResult(instance=inst.name, algorithm=name, tour=route, cost=cost,
                     candidate_evaluations=evals, stop_reason=stop, trace=trace,
                     extras=extras or {})


def stub_hc(inst, initial_route, budget, strategy="best", keep_history=False):
    budget.start()
    h = [(list(initial_route), tour_cost(inst.D, initial_route), 0)] if keep_history else None
    n = min(budget.max_evals or 100, 150)
    r, c, tr = _climb(inst, initial_route, random.Random(sum(initial_route[:5])), n, h)
    ext = {"route_history": h} if keep_history else {}
    return _res(inst, "HC", r, c, tr, n, STOP_LOCAL_OPT, ext)


def stub_hcr(inst, rng_init, budget, strategy="best"):
    budget.start()
    r0 = random_tour(inst.n, rng_init)
    n = min(budget.max_evals or 100, 150)
    r, c, tr = _climb(inst, r0, random.Random(7), n)
    return _res(inst, "HC-restarts", r, c, tr, n, STOP_EVALS)


def stub_calibrate(inst, route, rng, p0, samples=200):
    return 5.0 + rng.random(), 7


def stub_sa(inst, initial_route, budget, rng, T0, Tmin, alpha, steps, keep_history=False,
            window=500):
    budget.start()
    h = [(list(initial_route), tour_cost(inst.D, initial_route), 0)] if keep_history else None
    n = min(budget.max_evals or 100, 200)
    r, c, tr = _climb(inst, initial_route, rng, n, h)
    ext = {"temperature": [T0 * alpha ** i for i in range(10)],
           "current_cost": [c + 10 - i for i in range(10)],
           "accept_rate_worse": [max(0.0, 0.5 - 0.05 * i) for i in range(10)], "window": window}
    if keep_history:
        ext["route_history"] = h
    return _res(inst, "SA", r, c, tr, n, STOP_COOLED, ext)


def stub_ga(inst, budget, rng, population_size=80, elite_count=2, pc=0.9, pm=0.3,
            tournament_size=3, origin=0):
    budget.start()
    pop = [random_tour(inst.n, rng, origin) for _ in range(population_size)]
    costs = sorted(tour_cost(inst.D, p) for p in pop)
    best = min(pop, key=lambda p: tour_cost(inst.D, p))
    ext = {"gen_evals": [population_size * (g + 1) for g in range(5)],
           "best": [costs[0]] * 5, "median": [costs[len(costs) // 2]] * 5,
           "mean": [sum(costs) / len(costs)] * 5, "unique_fraction": [1.0, .9, .8, .7, .6],
           "edge_diversity": [.9, .8, .7, .6, .5]}
    return _res(inst, "GA", best, costs[0], [(population_size, costs[0], 0.01)],
                population_size, STOP_GENERATIONS, ext)


def _stub_exact(name):
    def solver(inst, origin=0, budget=None, heuristic="mst"):
        budget.start()
        if inst.n > 9:                                   # simula censura por limite
            return RunResult(instance=inst.name, algorithm=name, tour=None, cost=None,
                             expanded=100000, stop_reason=STOP_TIME, optimality_status=OPT_NO_ROUTE,
                             trace=[(0, None, 0.0)])
        cost, route, _ = brute_force(inst.D, origin)
        return RunResult(instance=inst.name, algorithm=name, tour=route, cost=cost, expanded=11,
                         stop_reason=STOP_OPTIMAL, optimality_status=OPT_PROVEN,
                         peak_memory=2048, trace=[(0, cost, 0.0)])
    return solver


STUBS = {"astar": _stub_exact("A*+MST"), "rbfs": _stub_exact("RBFS+MST"),
         "hill_climbing": stub_hc, "hill_climbing_restarts": stub_hcr,
         "calibrate_t0": stub_calibrate, "simulated_annealing": stub_sa,
         "genetic_algorithm": stub_ga}


def _cfg():
    c = ex.frozen_copy()
    c["scale_a"] = dict(c["scale_a"], max_evals=300)
    c["scale_b"] = dict(c["scale_b"], max_evals=300)
    return c


# --- Pruebas con solvers falsos --------------------------------------------------------
@pytest.mark.parametrize("alg", ["HC", "HC-restarts", "SA", "GA"])
def test_reproducibilidad_misma_semilla(gr17, alg):
    a = ex.run_one(alg, gr17, seed=3, config=_cfg(), solvers=STUBS)
    b = ex.run_one(alg, gr17, seed=3, config=_cfg(), solvers=STUBS)
    c = ex.run_one(alg, gr17, seed=4, config=_cfg(), solvers=STUBS)
    # los segundos varian entre corridas; evaluaciones y costos no
    sin_t = lambda r: [(e, c) for e, c, _ in r.trace]
    assert (a.tour, a.cost, sin_t(a)) == (b.tour, b.cost, sin_t(b))
    assert a.tour != c.tour or a.cost != c.cost or alg == "HC"


def test_misma_ruta_inicial_hc_y_sa(gr17):
    h = ex.run_one("HC", gr17, seed=5, config=_cfg(), solvers=STUBS)
    s = ex.run_one("SA", gr17, seed=5, config=_cfg(), solvers=STUBS)
    assert h.extras["initial_route"] == s.extras["initial_route"]
    assert ex.run_one("SA", gr17, seed=6, config=_cfg(), solvers=STUBS
                      ).extras["initial_route"] != s.extras["initial_route"]


def test_sa_cuenta_la_calibracion(gr17):
    s = ex.run_one("SA", gr17, seed=1, config=_cfg(), solvers=STUBS)
    assert s.extras["calibration_evals"] == 7
    assert s.candidate_evaluations == 200 + 7          # trabajo del solver + calibracion
    assert s.trace[0][0] == 7                          # la traza incluye el desplazamiento
    assert s.parameters["calibration_evals"] == 7 and s.elapsed_seconds > 0


def test_auditerror_ante_gap_negativo(gr17):
    with pytest.raises(ex.AuditError, match="GAP NEGATIVO"):
        ex.run_one("GA", gr17, seed=0, config=_cfg(), solvers=STUBS, reference=10 ** 9)


def test_auditerror_ante_ruta_invalida(gr17):
    def mala(inst, budget, rng, **kw):
        r = _res(inst, "GA", [0, 1, 1] + list(range(3, inst.n)), 5, [], 1, STOP_GENERATIONS)
        return r
    with pytest.raises(ex.AuditError, match="invalida"):
        ex.run_one("GA", gr17, seed=0, config=_cfg(), solvers=dict(STUBS, genetic_algorithm=mala))


def test_gap_none_sin_referencia_en_subinstancia(gr17):
    sub, _ = ex.select_subinstance(gr17, 8)
    r = ex.run_one("GA", sub, seed=0, config=_cfg(), solvers=STUBS)
    assert r.gap_percent is None and r.subset == tuple(sub.node_ids)
    full = ex.run_one("GA", gr17, seed=0, config=_cfg(), solvers=STUBS)
    assert full.gap_percent >= 0 and full.reference == 2085


def test_subinstancia_registra_nodos(gr17):
    sub, nodos = ex.select_subinstance(gr17, 6)
    assert nodos == tuple(gr17.node_ids[:6]) == (1, 2, 3, 4, 5, 6)
    assert [[gr17.D[i][j] for j in range(6)] for i in range(6)] == [list(f) for f in sub.D]


def test_escala_a_resumen_con_censurados(gr17):
    res = ex.run_scale_a([gr17], ks=(6, 8, 12), seeds=range(3), config=_cfg(), solvers=STUBS)
    # exactos: k=6 y 8 se certifican; k=12 queda censurado por limite (sin ruta)
    s = {(x["instance"], x["algorithm"]): x for x in ex.summarize(res)}
    a12 = s[("gr17[k=12]", "A*+MST")]
    assert (a12["planned"], a12["valid"], a12["censored"]) == (1, 0, 1)
    assert a12["best_cost"] is None and a12["gap_median"] is None
    a6 = s[("gr17[k=6]", "A*+MST")]
    assert (a6["planned"], a6["valid"], a6["censored"]) == (1, 1, 0) and a6["match_rate"] == 1.0
    # aproximados: denominador = 3 semillas; gap frente al optimo certificado (k<=10)
    h = s[("gr17[k=8]", "HC")]
    assert h["planned"] == 3 and h["valid"] == 3 and h["gap_median"] >= 0
    assert h["cost_std"] is not None and h["reference"] is not None
    # k=12 no tiene certificado: gap N/A para los aproximados
    assert s[("gr17[k=12]", "SA")]["gap_median"] is None
    # la fila de "origen distinto" no entra al resumen
    assert any(r.variant == "origin" for r in res)
    assert all(x["planned"] in (1, 3) for x in s.values())


def test_invarianza_del_origen(gr17):
    res = ex.run_scale_a([gr17], ks=(6,), seeds=range(1), config=_cfg(), solvers=STUBS)
    por = [r for r in res if r.variant == "origin"]
    assert len(por) == 2 and all(r.tour[0] == 5 for r in por)
    assert {r.cost for r in res if r.algorithm in ex.EXACT_ALGORITHMS} == {por[0].cost}

    def rota(inst, origin=0, budget=None, heuristic="mst"):
        r = STUBS["astar"](inst, origin, budget, heuristic)
        if origin != 0:
            # intercambia dos ciudades hasta que el costo cambie (ruta valida pero peor)
            base = list(r.tour)
            hecho = False
            for i in range(1, inst.n):
                for j in range(i + 1, inst.n):
                    t = list(base)
                    t[i], t[j] = t[j], t[i]
                    if tour_cost(inst.D, t) != r.cost:
                        r.tour, r.cost, hecho = t, tour_cost(inst.D, t), True
                        break
                if hecho:
                    break
            r.optimality_status = OPT_PROVEN
        return r
    with pytest.raises(ex.AuditError):
        ex.run_scale_a([gr17], ks=(6,), seeds=range(1), config=_cfg(),
                       solvers=dict(STUBS, astar=rota))


def test_orden_determinista_y_progreso(gr17):
    avisos = []
    a = ex.run_scale_b([gr17], seeds=range(2), config=_cfg(), solvers=STUBS,
                       progress=lambda i, n, d: avisos.append((i, n)))
    b = ex.run_scale_b([gr17], seeds=range(2), config=_cfg(), solvers=STUBS)
    assert [(r.algorithm, r.seed, r.cost) for r in a] == [(r.algorithm, r.seed, r.cost) for r in b]
    assert [r.algorithm for r in a] == ["A*+MST", "RBFS+MST", "HC", "HC", "HC-restarts",
                                        "HC-restarts", "SA", "SA", "GA", "GA"]
    assert avisos[-1] == (10, 10)
    assert all(r.scale == "B" and r.k == 17 for r in a)
    with pytest.raises(ValueError):
        ex.run_scale_b([gr17], seeds=range(1), config=_cfg(), solvers=STUBS, workers=2)


def test_ida_y_vuelta_csv_y_json(gr17, tmp_path):
    res = ex.run_scale_a([gr17], ks=(6, 12), seeds=range(2), config=_cfg(), solvers=STUBS)
    p = tmp_path / "r.csv"
    ex.save_rows_csv(res, p)
    cargadas = ex.load_rows_csv(p)
    assert cargadas == [r.row() for r in res]
    # el resumen de las filas cargadas coincide con el de los objetos
    assert ex.summarize(cargadas) == ex.summarize(res)
    j = tmp_path / "r.json"
    ex.save_results_json(res, j)
    de_json = ex.load_results_json(j)
    assert [r.row() for r in de_json] == [r.row() for r in res]
    assert de_json[3].trace == [tuple(t) for t in res[3].trace]


def test_tablas_markdown(gr17):
    res = ex.run_scale_b([gr17], seeds=range(2), config=_cfg(), solvers=STUBS)
    t = ex.table_methods(ex.summarize(res), "gr17")
    assert t.count("\n") == 7 and "HC reinicios" in t and "GA básico" in t and "2/2" in t
    resa = ex.run_scale_a([gr17], ks=(6, 12), seeds=range(1), config=_cfg(), solvers=STUBS)
    ts = ex.table_subinstances(resa)
    assert "gr17[k=6]" in ts and "1,2,3,4,5,6" in ts and "(interrumpido)" in ts


def test_held_karp_coincide_con_fuerza_bruta(gr17):
    sub, _ = ex.select_subinstance(gr17, 8)
    assert ex.exact_optimum_dp(sub.D) == brute_force(sub.D)[0]


def test_assert_frozen_y_entorno():
    assert ex.assert_frozen()                    # FROZEN real: ya calibrado y congelado
    c = ex.frozen_copy()
    c["sa"]["calibrated"] = False                # parametros provisionales: se rechazan
    with pytest.raises(ex.AuditError):
        ex.assert_frozen(c)
    c["sa"]["calibrated"] = True
    assert ex.assert_frozen(c)
    rep = ex.environment_report()
    assert rep["python"] and rep["paquetes"]["numpy"] and "tracemalloc" in rep["memoria"]
    assert "Sistema operativo" in ex.format_environment(rep)


# --- Graficas con datos sinteticos ----------------------------------------------------------
def _sinteticos(inst):
    out = []
    rng = random.Random(0)
    for alg, fin in (("HC", 1500), ("SA", 3000), ("GA", 2400)):
        for s in range(5):
            c, tr = 3000, [(0, 3000, 0.0)]
            for e in range(1, fin, 150):
                c -= rng.randint(0, 40)
                tr.append((e, c, e * 1e-4))
            tr.append((fin, c, fin * 1e-4))
            r = RunResult(instance=inst.name, algorithm=alg, seed=s, tour=list(range(inst.n)),
                          cost=c, gap_percent=100.0 * (c - 2085) / 2085, trace=tr,
                          candidate_evaluations=fin)
            out.append(r)
    return out


def test_graficas_convergencia_y_cajas(gr17):
    res = _sinteticos(gr17)
    g, M, fines = gf.step_curves(res[:5], "evaluations")
    assert M.shape[0] == 5 and (M[:, -1] > 0).all()
    f1 = gf.plot_convergence(res, "evaluations", instance="gr17", reference=2085)
    f2 = gf.plot_convergence_both(res, instance="gr17")
    f3 = gf.plot_gap_boxes(res)
    assert all(hasattr(f, "savefig") for f in (f1, f2, f3))
    plt.close("all")


def test_funcion_escalonada_no_interpola():
    r = RunResult("x", "HC", trace=[(0, 10, 0.0), (5, 6, 0.1), (9, 3, 0.2)])
    g, M, fines = gf.step_curves([r], "evaluations", grid=[0, 4, 5, 8, 9, 12])
    assert list(M[0]) == [10, 10, 6, 6, 3, 3] and fines[0] == 9


def test_graficas_exactos_y_series(gr17):
    filas = []
    for k, cen in ((6, False), (8, False), (12, True)):
        for alg in ex.EXACT_ALGORITHMS:
            r = RunResult("gr17[k={0}]".format(k), alg, elapsed_seconds=0.01 * k ** 2,
                          peak_memory=1024 * k, expanded=10 * k,
                          stop_reason=STOP_TIME if cen else STOP_OPTIMAL)
            r.k, r.variant, r.repetition = k, "main", 1
            filas.append(r)
    f = gf.plot_exact_scaling(filas + [r.row() for r in filas])
    sa = stub_sa(gr17, list(range(17)), type("B", (), {"max_evals": 100, "start": lambda s: s})(),
                 random.Random(1), 10.0, 0.01, 0.97, 10)
    sa.seed = 1
    f2 = gf.plot_sa(sa)
    assert "ventana de 500" in f2.axes[2].get_ylabel()
    f3 = gf.plot_ga(stub_ga(gr17, type("B", (), {"max_evals": 100, "start": lambda s: s})(),
                            random.Random(2)))
    assert all(hasattr(x, "savefig") for x in (f, f2, f3))
    with pytest.raises(ValueError):
        gf.plot_sa(RunResult("x", "SA"))
    plt.close("all")


def test_rutas_con_y_sin_coordenadas(gr17, burma):
    ruta = list(range(gr17.n))
    f = gf.plot_routes(gr17, ruta, ruta[::-1][-1:] + ruta[:-1][::-1], "SA")
    assert len(f.axes) == 4                          # 3 paneles + barra de color (sin coords)
    assert "esquemática" in f.axes[0].get_xlabel()
    g = gf.plot_routes(burma, list(range(burma.n)), list(range(burma.n)))
    assert len(g.axes) == 2
    plt.close("all")


def test_animacion_gif(gr17, burma, tmp_path):
    inst = burma
    rng = random.Random(0)
    h = [(random_tour(inst.n, rng), 0, e) for e in range(0, 100, 10)]
    h = [(r, tour_cost(inst.D, r), e) for r, _, e in h]
    gif = tmp_path / "a.gif"
    frames = gf.animate_improvements(inst, h, "SA", path_gif=str(gif), max_frames=4)
    assert len(frames) == 4 and gif.stat().st_size > 0
    from PIL import Image
    assert Image.open(gif).n_frames == 4
    assert gf.animate_improvements(gr17, h[:2], "HC")      # sin coordenadas: circular
    assert hasattr(gf.show_frames(frames), "savefig")
    with pytest.raises(ValueError):
        gf.animate_improvements(inst, [], "SA")
    plt.close("all")


# --- Integracion con los solvers reales (se omite si falta algun modulo) ---------------------
_REALES = all(importlib.util.find_spec("tsp." + m) is not None
              for m in ("mst", "astar", "rbfs", "vecindad", "hc", "sa", "ga"))


@pytest.mark.skipif(not _REALES, reason="faltan modulos reales de solvers")
def test_integracion_seis_metodos_gr17(gr17):
    import time
    cfg = ex.frozen_copy()
    cfg["exact"] = dict(cfg["exact"], max_seconds=2.0, max_expansions=3000)
    cfg["scale_b"] = dict(cfg["scale_b"], max_evals=600, max_seconds=3.0, sa_steps=10)
    t0 = time.perf_counter()
    res = ex.run_scale_b([gr17], seeds=range(2), config=cfg)
    assert time.perf_counter() - t0 < 20
    assert {r.algorithm for r in res} >= {"A*+MST", "RBFS+MST", "HC", "HC-restarts", "SA", "GA"}
    for r in res:
        assert r.elapsed_seconds > 0 and r.scale == "B"
        r.validate(gr17)
        if r.algorithm in ex.APPROX_ALGORITHMS:
            assert r.gap_percent >= 0 and r.candidate_evaluations <= 600 + 50
    # reproducibilidad con los solvers reales (los tiempos pueden variar; costos no)
    otra = ex.run_scale_b([gr17], seeds=range(2), config=cfg, algorithms=ex.APPROX_ALGORITHMS)
    mias = [r for r in res if r.algorithm in ex.APPROX_ALGORITHMS]
    assert [(r.algorithm, r.cost, r.tour) for r in mias] == [(r.algorithm, r.cost, r.tour) for r in otra]
    h = next(r for r in res if r.algorithm == "HC" and r.seed == 0)
    s = next(r for r in res if r.algorithm == "SA" and r.seed == 0)
    assert h.extras["initial_route"] == s.extras["initial_route"]


@pytest.mark.skipif(not _REALES, reason="faltan modulos reales de solvers")
def test_integracion_escala_a_corta(gr17):
    cfg = ex.frozen_copy()
    cfg["scale_a"] = dict(cfg["scale_a"], max_evals=300, max_seconds=2.0, sa_steps=5)
    res = ex.run_scale_a([gr17], ks=(6, 8), seeds=range(2), config=cfg)
    for r in res:
        if r.algorithm in ex.EXACT_ALGORITHMS and r.variant == "main":
            assert r.optimality_status == OPT_PROVEN and r.gap_percent == 0.0
        if r.gap_percent is not None:
            assert r.gap_percent >= 0
