"""Pruebas de vecindad 2-opt, Hill Climbing y Simulated Annealing (seccion 13)."""
import itertools
import math
import random

import pytest

from tests.oraculo import brute_force, closed_cost
from tsp.datos import TSPInstance, load_by_name
from tsp.hc import hill_climbing, hill_climbing_restarts
from tsp.modelo import (STOP_COOLED, STOP_EVALS, STOP_LOCAL_OPT, STOP_TIME, Budget,
                        is_valid_tour, make_rngs, random_tour, tour_cost)
from tsp.sa import calibrate_t0, simulated_annealing
from tsp.vecindad import (count_valid_pairs, is_valid_pair, random_valid_pair,
                          swap_delta, swap_move, two_opt_apply,
                          two_opt_apply_inplace, two_opt_delta, valid_pairs)


@pytest.fixture(scope="module")
def gr17():
    return load_by_name("gr17")


@pytest.fixture(scope="module")
def burma14():
    return load_by_name("burma14")


@pytest.fixture(scope="module")
def berlin52():
    return load_by_name("berlin52")


@pytest.fixture(scope="module")
def eil51():
    return load_by_name("eil51")


def neighbours_improve(inst, route):
    """True si ALGUN vecino 2-opt mejora, recalculando el costo COMPLETO con el
    oraculo independiente (sin usar delta)."""
    base = closed_cost(inst.D, route)
    return any(closed_cost(inst.D, two_opt_apply(route, i, j)) < base
               for i, j in valid_pairs(inst.n))


def small_inst(n, seed=0):
    rng = random.Random(seed)
    pts = [(rng.random(), rng.random()) for _ in range(n)]
    D = [[0 if a == b else int(1000 * math.dist(pts[a], pts[b])) + 1 for b in range(n)]
         for a in range(n)]
    return TSPInstance("rnd{0}".format(n), list(range(1, n + 1)), D, None, "EXPLICIT", None)


# ------------------------------------------------------------------ vecindad
@pytest.mark.parametrize("n", [4, 5, 6, 7, 8, 10, 14, 17, 52])
def test_numero_de_pares_validos(n):
    pares = list(valid_pairs(n))
    assert len(pares) == n * (n - 3) // 2 == count_valid_pairs(n)
    assert len(set(pares)) == len(pares)
    # definicion directa del enunciado: 0<=i<j<n, j!=i+1, (i,j)!=(0,n-1)
    directo = [(i, j) for i in range(n) for j in range(n)
               if i < j and j != i + 1 and (i, j) != (0, n - 1)]
    assert sorted(pares) == sorted(directo)
    assert all(is_valid_pair(n, i, j) for i, j in pares)
    assert not is_valid_pair(n, 0, n - 1)


def test_delta_igual_diferencia_de_costos_en_miles_de_movimientos(berlin52):
    rng = random.Random(7)
    D, n = berlin52.D, berlin52.n
    for _ in range(3000):
        r = random_tour(n, rng)
        i, j = random_valid_pair(n, rng)
        delta = two_opt_delta(D, r, i, j)
        assert delta == tour_cost(D, two_opt_apply(r, i, j)) - tour_cost(D, r)
        assert delta == closed_cost(D, two_opt_apply(r, i, j)) - closed_cost(D, r)


@pytest.mark.parametrize("name", ["burma14", "gr17"])
def test_delta_en_todos_los_pares_incluida_arista_de_cierre(name):
    inst = load_by_name(name)
    rng = random.Random(3)
    visto_cierre = 0
    for _ in range(20):
        r = random_tour(inst.n, rng)
        c0 = tour_cost(inst.D, r)
        for i, j in valid_pairs(inst.n):
            if j == inst.n - 1:                 # d = route[0]: arista de cierre
                visto_cierre += 1
            assert two_opt_delta(inst.D, r, i, j) == tour_cost(inst.D, two_opt_apply(r, i, j)) - c0
    assert visto_cierre > 0


def test_movimientos_conservan_la_permutacion_y_el_origen(gr17):
    rng = random.Random(11)
    for _ in range(500):
        r = random_tour(gr17.n, rng, origin=0)
        antes = list(r)
        i, j = random_valid_pair(gr17.n, rng)
        c = two_opt_apply(r, i, j)
        assert r == antes                                   # la copia no toca la original
        assert is_valid_tour(c, gr17.n, 0) and c[0] == 0
        r2 = list(r)
        two_opt_apply_inplace(r2, i, j)
        assert r2 == c                                      # en sitio == copia
        assert is_valid_tour(r2, gr17.n, 0)
        a, b = rng.sample(range(1, gr17.n), 2)
        assert is_valid_tour(swap_move(r, a, b), gr17.n, 0)


def test_random_valid_pair_siempre_valido_y_uniforme():
    n = 7
    rng = random.Random(1)
    cuenta = {p: 0 for p in valid_pairs(n)}
    N = 14000
    for _ in range(N):
        p = random_valid_pair(n, rng)
        assert p in cuenta
        cuenta[p] += 1
    esperado = N / len(cuenta)
    assert all(abs(c - esperado) < 0.2 * esperado for c in cuenta.values())


def test_2opt_no_es_swap_ejemplo_concreto():
    # Ruta 0..6, pares i=1, j=5: 2-opt invierte las posiciones 2..5; swap intercambia
    # SOLO las ciudades de las posiciones 2 y 5.
    r = list(range(7))
    assert two_opt_apply(r, 1, 5) == [0, 1, 5, 4, 3, 2, 6]
    assert swap_move(r, 2, 5) == [0, 1, 5, 3, 4, 2, 6]
    assert two_opt_apply(r, 1, 5) != swap_move(r, 2, 5)

    def aristas(x):
        return {frozenset((x[k], x[(k + 1) % len(x)])) for k in range(len(x))}
    assert len(aristas(r) - aristas(two_opt_apply(r, 1, 5))) == 2   # 2-opt: 2 aristas
    assert len(aristas(r) - aristas(swap_move(r, 2, 5))) == 4       # swap: 4 aristas
    # con tres ciudades en el segmento, ambos coinciden (caso particular, no general)
    assert two_opt_apply(r, 1, 4) == swap_move(r, 2, 4)


def test_swap_delta_coincide_con_costo_completo(gr17):
    rng = random.Random(5)
    for _ in range(500):
        r = random_tour(gr17.n, rng)
        i, j = sorted(rng.sample(range(1, gr17.n), 2))
        assert swap_delta(gr17.D, r, i, j) == tour_cost(gr17.D, swap_move(r, i, j)) - tour_cost(gr17.D, r)


# ------------------------------------------------------------ Hill Climbing
@pytest.mark.parametrize("name", ["burma14", "gr17", "eil51"])
@pytest.mark.parametrize("strategy", ["best", "first"])
def test_hc_optimo_local_verificado_enumerando_el_vecindario(name, strategy):
    inst = load_by_name(name)
    for seed in range(3):
        rng_init, _ = make_rngs(seed)
        r0 = random_tour(inst.n, rng_init)
        res = hill_climbing(inst, r0, Budget(max_evals=10 ** 7), strategy=strategy)
        assert res.stop_reason == STOP_LOCAL_OPT
        res.validate(inst)
        assert not neighbours_improve(inst, res.tour)       # ningun vecino mejora
        assert res.algorithm == ("HC" if strategy == "best" else "HC-first")


def test_hc_nunca_empeora_y_solo_acepta_mejoras_estrictas(gr17):
    rng_init, _ = make_rngs(4)
    r0 = random_tour(gr17.n, rng_init)
    res = hill_climbing(gr17, r0, Budget(max_evals=10 ** 6), keep_history=True)
    hist = res.extras["route_history"]
    costos = [c for _, c, _ in hist]
    assert all(b < a for a, b in zip(costos, costos[1:]))    # estrictamente decreciente
    assert res.cost <= tour_cost(gr17.D, r0)
    assert res.extras["improvements"] == len(hist) - 1


def test_hc_no_modifica_la_ruta_inicial(gr17):
    rng_init, _ = make_rngs(1)
    r0 = random_tour(gr17.n, rng_init)
    copia = list(r0)
    hill_climbing(gr17, r0, Budget(max_evals=5000))
    assert r0 == copia


@pytest.mark.parametrize("limite", [0, 1, 7, 100, 119, 120, 1234])
@pytest.mark.parametrize("strategy", ["best", "first"])
def test_hc_presupuesto_exacto_y_ruta_valida(gr17, limite, strategy):
    rng_init, _ = make_rngs(2)
    r0 = random_tour(gr17.n, rng_init)
    res = hill_climbing(gr17, r0, Budget(max_evals=limite), strategy=strategy)
    assert res.candidate_evaluations <= limite
    res.validate(gr17)
    if res.stop_reason != STOP_LOCAL_OPT:                    # interrumpido: no afirma optimo local
        assert res.stop_reason == STOP_EVALS
        assert res.candidate_evaluations == limite
    if limite == 0:
        assert res.tour == r0 and res.stop_reason == STOP_EVALS


def test_hc_interrumpido_no_afirma_optimo_local(eil51):
    rng_init, _ = make_rngs(0)
    r0 = random_tour(eil51.n, rng_init)
    res = hill_climbing(eil51, r0, Budget(max_evals=300))
    assert res.stop_reason == STOP_EVALS
    assert res.optimality_status != "PROVEN_OPTIMAL"
    assert is_valid_tour(res.tour, eil51.n, 0)


def test_hc_limite_de_tiempo_devuelve_ruta_valida(gr17):
    rng_init, _ = make_rngs(0)
    r0 = random_tour(gr17.n, rng_init)
    res = hill_climbing(gr17, r0, Budget(max_seconds=0.0))
    assert res.stop_reason == STOP_TIME
    res.validate(gr17)


def test_hc_cuenta_cada_delta_una_evaluacion(gr17):
    # Un optimo local verificado por una pasada completa cuesta exactamente n(n-3)/2.
    rng_init, _ = make_rngs(0)
    r0 = random_tour(gr17.n, rng_init)
    local = hill_climbing(gr17, r0, Budget(max_evals=10 ** 6))
    otra = hill_climbing(gr17, local.tour, Budget(max_evals=10 ** 6))
    assert otra.candidate_evaluations == count_valid_pairs(gr17.n)
    assert otra.stop_reason == STOP_LOCAL_OPT and otra.tour == local.tour


def test_hc_reinicios_presupuesto_global_y_mejor_ruta(gr17):
    rng_init, _ = make_rngs(0)
    res = hill_climbing_restarts(gr17, rng_init, Budget(max_evals=5000))
    assert res.algorithm == "HC-restarts"
    assert res.candidate_evaluations <= 5000
    assert res.extras["restarts"] >= 2
    res.validate(gr17)
    assert res.cost <= min(res.extras["local_optima_costs"])
    assert len(res.extras["local_optima_costs"]) in (res.extras["restarts"], res.extras["restarts"] - 1)
    assert res.stop_reason == STOP_EVALS


def test_hc_reinicios_primer_reinicio_es_la_ruta_inicial_controlada(gr17):
    # Con presupuesto 0 devuelve exactamente random_tour(n, rng_init): el mismo que
    # recibirian HC de una ruta y SA (comparacion controlada).
    a, _ = make_rngs(9)
    b, _ = make_rngs(9)
    res = hill_climbing_restarts(gr17, a, Budget(max_evals=0))
    assert res.tour == random_tour(gr17.n, b)
    assert res.candidate_evaluations == 0 and res.stop_reason == STOP_EVALS


def test_hc_reinicios_exige_un_limite(gr17):
    with pytest.raises(ValueError):
        hill_climbing_restarts(gr17, random.Random(0), Budget())


def test_hc_reinicios_alcanza_el_optimo_en_subinstancia_pequena(gr17):
    sub = gr17.subinstance(8)
    optimo, _, _ = brute_force(sub.D)
    res = hill_climbing_restarts(sub, random.Random(5), Budget(max_evals=20000))
    assert res.cost == optimo
    # y nunca baja del optimo exhaustivo
    for s in range(5):
        r = hill_climbing(sub, random_tour(sub.n, random.Random(s)), Budget(max_evals=10 ** 6))
        assert r.cost >= optimo


# --------------------------------------------------------------- calibracion
def test_calibrate_t0_formula_y_evaluaciones(gr17):
    rng_init, _ = make_rngs(0)
    r = random_tour(gr17.n, rng_init)
    p0 = 0.8
    T0, used = calibrate_t0(gr17, r, random.Random(42), p0, samples=200)
    assert used == 200
    # reconstruccion independiente con el mismo generador
    rr = random.Random(42)
    deltas = []
    for _ in range(200):
        i, j = random_valid_pair(gr17.n, rr)
        deltas.append(tour_cost(gr17.D, two_opt_apply(r, i, j)) - tour_cost(gr17.D, r))
    pos = sorted(d for d in deltas if d > 0)
    m = len(pos)
    med = pos[m // 2] if m % 2 else (pos[m // 2 - 1] + pos[m // 2]) / 2
    assert T0 == pytest.approx(-med / math.log(p0))
    assert T0 > 0
    # a mayor p0 mayor T0
    T_alto, _ = calibrate_t0(gr17, r, random.Random(42), 0.95)
    T_bajo, _ = calibrate_t0(gr17, r, random.Random(42), 0.2)
    assert T_alto > T0 > T_bajo


def test_calibrate_t0_sin_deltas_positivos_usa_alternativa():
    n = 6
    D = [[0 if a == b else 5 for b in range(n)] for a in range(n)]    # todos los deltas son 0
    inst = TSPInstance("plano", list(range(1, n + 1)), D, None, "EXPLICIT", None)
    T0, used = calibrate_t0(inst, list(range(n)), random.Random(0), 0.5, samples=50)
    assert used == 50
    assert T0 == pytest.approx(5 / math.log(2))        # mediana de pesos de aristas / ln 2
    with pytest.raises(ValueError):
        calibrate_t0(inst, list(range(n)), random.Random(0), 1.0)


# ----------------------------------------------------------------------- SA
def run_sa(inst, seed, max_evals, T0, Tmin=1e-3, alpha=0.95, steps=100, **kw):
    rng_init, rng = make_rngs(seed)
    r0 = random_tour(inst.n, rng_init)
    return r0, simulated_annealing(inst, r0, Budget(max_evals=max_evals), rng, T0, Tmin,
                                   alpha, steps, **kw)


def test_sa_mejor_distinta_de_la_actual_con_temperatura_alta(gr17):
    # T enorme: casi todo se acepta, la ruta actual divaga y termina PEOR que la
    # mejor observada. Debe devolverse la mejor, no la actual.
    r0, res = run_sa(gr17, 3, 3000, T0=1e9, Tmin=1e8, alpha=0.999, steps=100, keep_history=True)
    cur = res.extras["final_current_route"]
    assert res.extras["final_current_cost"] == tour_cost(gr17.D, cur)
    assert res.tour != cur
    assert res.cost < res.extras["final_current_cost"]
    assert res.cost == min(c for _, c, _ in res.extras["route_history"])
    assert res.cost <= tour_cost(gr17.D, r0)
    res.validate(gr17)
    assert res.extras["accepted_worse"] > 0


def test_sa_la_mejor_es_copia_independiente_de_la_actual(gr17):
    # Si la "mejor" fuera un alias de la actual, cambiaria sin querer: se comprueba
    # que el costo de la ruta devuelta coincide con el costo informado.
    for seed in range(5):
        _, res = run_sa(gr17, seed, 2000, T0=1e6, Tmin=1e5, alpha=0.99, steps=50)
        assert tour_cost(gr17.D, res.tour) == res.cost


def test_sa_criterio_de_metropolis_en_los_extremos(gr17):
    _, caliente = run_sa(gr17, 1, 4000, T0=1e9, Tmin=1e8, alpha=0.999, steps=100)
    assert caliente.extras["accepted_worse"] / caliente.extras["proposed_worse"] > 0.99
    _, frio = run_sa(gr17, 1, 4000, T0=1e-6, Tmin=1e-7, alpha=0.999, steps=100)
    assert frio.extras["accepted_worse"] == 0


def test_sa_con_T0_muy_baja_se_comporta_como_hc(gr17):
    # T0 ~ 0: exp(-delta/T) = 0 para todo delta > 0, solo se aceptan delta <= 0:
    # es un descenso (con propuestas aleatorias y aceptando empates). Con muchas
    # propuestas por vecino termina en un optimo local, como HC.
    r0, res = run_sa(gr17, 2, 20000, T0=1e-9, Tmin=1e-10, alpha=0.999, steps=1000, keep_history=True)
    assert res.extras["accepted_worse"] == 0
    assert res.extras["final_current_cost"] == res.cost            # actual == mejor
    assert res.tour == res.extras["final_current_route"]
    cur = res.extras["current_cost"]
    assert all(b <= a for a, b in zip(cur, cur[1:]))                # nunca sube
    assert res.cost <= tour_cost(gr17.D, r0)
    assert not neighbours_improve(gr17, res.tour)                    # optimo local


def test_sa_presupuesto_exacto_con_calibracion(gr17):
    rng_init, rng = make_rngs(0)
    r0 = random_tour(gr17.n, rng_init)
    T0, used = calibrate_t0(gr17, r0, rng, 0.8, samples=200)
    for limite in (200, 201, 777, 1500):
        res = simulated_annealing(gr17, r0, Budget(max_evals=limite), random.Random(1), T0, 1e-3,
                                  0.97, 50, initial_evals=used)
        assert res.candidate_evaluations <= limite
        assert res.candidate_evaluations == limite              # no se enfria tan rapido
        assert res.stop_reason == STOP_EVALS
        res.validate(gr17)


def test_sa_termina_cooled_dentro_del_presupuesto(burma14):
    # bloques: ln(Tmin/T0)/ln(alpha) enfriamientos * steps
    r0, res = run_sa(burma14, 0, 10 ** 6, T0=100.0, Tmin=1.0, alpha=0.9, steps=20)
    assert res.stop_reason == STOP_COOLED
    bloques = math.ceil(math.log(1.0 / 100.0) / math.log(0.9))
    assert res.candidate_evaluations == bloques * 20
    assert res.extras["final_temperature"] <= 1.0
    res.validate(burma14)


def test_sa_limite_de_tiempo_devuelve_ruta_valida(gr17):
    rng_init, rng = make_rngs(0)
    r0 = random_tour(gr17.n, rng_init)
    res = simulated_annealing(gr17, r0, Budget(max_seconds=0.0), rng, 100.0, 1.0, 0.9, 10)
    assert res.stop_reason == STOP_TIME and res.tour == r0
    res.validate(gr17)


def test_sa_reproducible_con_la_misma_semilla(gr17):
    def corrida():
        r0, res = run_sa(gr17, 5, 3000, T0=50.0, alpha=0.97, steps=50, keep_history=True)
        return (res.tour, res.cost, [(e, c) for e, c, _ in res.trace], res.extras["temperature"],
                res.extras["current_cost"], res.extras["accept_rate_worse"],
                [(e, c) for _, c, e in res.extras["route_history"]])
    assert corrida() == corrida()


def test_hc_y_restarts_reproducibles(gr17):
    def hc():
        a, _ = make_rngs(3)
        return hill_climbing_restarts(gr17, a, Budget(max_evals=4000))
    x, y = hc(), hc()
    assert (x.tour, x.cost, x.extras["local_optima_costs"]) == (y.tour, y.cost, y.extras["local_optima_costs"])
    assert [(e, c) for e, c, _ in x.trace] == [(e, c) for e, c, _ in y.trace]


def test_sa_series_acotadas_y_alineadas(berlin52):
    _, res = run_sa(berlin52, 0, 30000, T0=500.0, Tmin=1e-3, alpha=0.995, steps=10, window=10)
    e = res.extras
    n = len(e["series_evals"])
    assert 0 < n <= 2000 + 1
    assert len(e["temperature"]) == len(e["current_cost"]) == len(e["accept_rate_worse"]) == n
    assert all(x is None or 0.0 <= x <= 1.0 for x in e["accept_rate_worse"])
    assert all(b >= a for a, b in zip(e["series_evals"], e["series_evals"][1:]))
    assert all(b <= a + 1e-9 for a, b in zip(e["temperature"], e["temperature"][1:]))


def test_sa_parametros_invalidos(gr17):
    r0 = list(range(gr17.n))
    for kw in ({"T0": 0}, {"Tmin": 0}, {"alpha": 1.0}, {"alpha": 0.0}, {"steps": 0}):
        args = dict(T0=10.0, Tmin=1.0, alpha=0.9, steps=5)
        args.update(kw)
        with pytest.raises(ValueError):
            simulated_annealing(gr17, r0, Budget(max_evals=10), random.Random(0), **args)


# ------------------------------------------------- trace, historia, contrato
def corridas(gr17, berlin52):
    rng_init, rng = make_rngs(0)
    r0 = random_tour(berlin52.n, rng_init)
    yield hill_climbing(berlin52, r0, Budget(max_evals=3000))
    yield hill_climbing(berlin52, r0, Budget(max_evals=10 ** 6), strategy="first")
    yield hill_climbing_restarts(berlin52, make_rngs(0)[0], Budget(max_evals=6000))
    T0, used = calibrate_t0(berlin52, r0, random.Random(1), 0.8)
    yield simulated_annealing(berlin52, r0, Budget(max_evals=6000), rng, T0, 1.0, 0.97, 50,
                              initial_evals=used)


def test_trace_monotono_y_coherente(gr17, berlin52):
    for res in corridas(gr17, berlin52):
        t = res.trace
        assert len(t) >= 2
        ev = [x[0] for x in t]
        co = [x[1] for x in t]
        sec = [x[2] for x in t]
        assert all(b >= a for a, b in zip(ev, ev[1:]))               # evaluaciones no decrecen
        assert all(b <= a for a, b in zip(co, co[1:]))               # mejor costo no sube
        assert all(b >= a for a, b in zip(sec, sec[1:]))
        assert co[-1] == res.cost and ev[-1] == res.candidate_evaluations
        res.validate(berlin52)


def test_keep_history_coherente_hc_y_sa(berlin52):
    rng_init, rng = make_rngs(2)
    r0 = random_tour(berlin52.n, rng_init)
    for res in (hill_climbing(berlin52, r0, Budget(max_evals=4000), keep_history=True),
                simulated_annealing(berlin52, r0, Budget(max_evals=4000), rng, 200.0, 1.0, 0.97, 40,
                                    keep_history=True)):
        h = res.extras["route_history"]
        assert h[0][0] == r0 and h[0][2] == 0                         # primer cuadro: ruta inicial
        evs = [e for _, _, e in h]
        assert all(b >= a for a, b in zip(evs, evs[1:]))
        for ruta, costo, _ in h:
            assert is_valid_tour(ruta, berlin52.n, 0)
            assert costo == tour_cost(berlin52.D, ruta)
        assert h[-1][0] == res.tour and h[-1][1] == res.cost
        assert [c for _, c, _ in h] == sorted((c for _, c, _ in h), reverse=True)
    # sin keep_history no se guarda nada
    assert "route_history" not in hill_climbing(berlin52, r0, Budget(max_evals=100)).extras


def test_misma_ruta_inicial_para_hc_y_sa(gr17):
    rng_init, rng = make_rngs(8)
    r0 = random_tour(gr17.n, rng_init)
    hc = hill_climbing(gr17, r0, Budget(max_evals=500))
    sa = simulated_annealing(gr17, r0, Budget(max_evals=500), rng, 30.0, 1.0, 0.95, 20)
    assert hc.trace[0][1] == sa.trace[0][1] == tour_cost(gr17.D, r0)
    assert hc.trace[0][0] == sa.trace[0][0] == 0
    assert hc.candidate_evaluations == sa.candidate_evaluations == 500


def test_sa_nunca_peor_que_el_inicio_y_cota_de_oraculo(gr17):
    sub = gr17.subinstance(8)
    optimo, _, _ = brute_force(sub.D)
    for seed in range(5):
        r0, res = run_sa(sub, seed, 5000, T0=200.0, alpha=0.95, steps=20)
        assert optimo <= res.cost <= tour_cost(sub.D, r0)
