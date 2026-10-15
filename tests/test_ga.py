# -*- coding: utf-8 -*-
"""Pruebas del algoritmo genetico (tabla de la seccion 13: OX e inversion,
presupuesto) y de sus garantias: elitismo, reproducibilidad y diversidad."""
import random

import pytest

from tsp.datos import TSPInstance, load_by_name
from tsp.ga import (_canonical, _edge_diversity, _invert_segment, _ox, _tournament,
                    _unique_fraction, genetic_algorithm)
from tsp.modelo import (STOP_EVALS, STOP_GENERATIONS, STOP_TIME, Budget, is_valid_tour,
                        make_rngs, tour_cost)


def _small_instance(n=9, seed=5):
    """Instancia simetrica sintetica (pesos enteros) para pruebas rapidas."""
    r = random.Random(seed)
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            D[i][j] = D[j][i] = r.randint(1, 50)
    return TSPInstance("sint{0}".format(n), range(1, n + 1), D, None, "EXPLICIT", None)


# ---------------------------------------------------------------- OX ----------
def test_ox_actividad_manual():
    """parent1=[B,C,D,E,F,G], parent2=[E,B,G,C,F,D], segmento 2..4 (desde 1)
    = indices 0-based 1..3.
    Segmento copiado de parent1: C,D,E en las posiciones 2,3,4.
    Posiciones vacias desde right+1 (pos 5): 5, 6, 1.
    Lectura de parent2 desde la pos 5: F, D, E, B, G, C.
    Se omiten D, E, C (ya estan); quedan F, B, G -> pos5=F, pos6=B, pos1=G.
    Hijo = [G,C,D,E,F,B]."""
    p1 = list("BCDEFG")
    p2 = list("EBGCFD")
    assert _ox(p1, p2, 1, 3) == list("GCDEFB")
    # Hijo simetrico OX(p2,p1) con el mismo corte (calculado a mano tambien):
    # segmento B,G,C; lectura de p1 desde pos 5: F,G,B,C,D,E; omite G,B,C;
    # F->pos5, D->pos6, E->pos1  => [E,B,G,C,F,D]
    assert _ox(p2, p1, 1, 3) == list("EBGCFD")


@pytest.mark.parametrize("length", [1, 2, 3, 7, 16])
def test_ox_es_permutacion_en_todos_los_cortes(length):
    r = random.Random(length)
    genes = list(range(1, length + 1))
    for _ in range(30):
        p1, p2 = r.sample(genes, length), r.sample(genes, length)
        for left in range(length):
            for right in range(left, length):      # incluye left=right, left=0,
                child = _ox(p1, p2, left, right)    # right=ultimo y segmento completo
                assert sorted(child) == genes
                assert child[left:right + 1] == p1[left:right + 1]


def test_ox_segmento_completo_copia_parent1():
    assert _ox([3, 1, 2], [2, 3, 1], 0, 2) == [3, 1, 2]


@pytest.mark.parametrize("seed", range(6))
def test_ox_miles_de_cruces_aleatorios(seed):
    r = random.Random(seed)
    genes = list(range(1, 21))
    for _ in range(2000):
        p1, p2 = r.sample(genes, 20), r.sample(genes, 20)
        left, right = sorted((r.randrange(20), r.randrange(20)))
        assert sorted(_ox(p1, p2, left, right)) == genes


# ------------------------------------------------------------ inversion -------
def test_inversion_casos_frontera():
    base = [1, 2, 3, 4, 5]
    assert _invert_segment(base, 0, 4) == [5, 4, 3, 2, 1]     # completo
    assert _invert_segment(base, 0, 1) == [2, 1, 3, 4, 5]     # left=0
    assert _invert_segment(base, 3, 4) == [1, 2, 3, 5, 4]     # right=ultimo
    assert _invert_segment(base, 2, 2) == base                # left=right
    assert base == [1, 2, 3, 4, 5]                            # no muta el original


@pytest.mark.parametrize("seed", range(5))
def test_inversion_miles_de_mutaciones(seed):
    r = random.Random(seed)
    genes = list(range(1, 30))
    for _ in range(2000):
        c = r.sample(genes, len(genes))
        i, j = sorted((r.randrange(len(c)), r.randrange(len(c))))
        assert sorted(_invert_segment(c, i, j)) == genes


# ------------------------------------------------------------- torneo ---------
def test_torneo_gana_el_menor_costo_y_desempata_por_muestreo():
    costs = [10, 20, 30, 5]
    rng = random.Random(0)
    assert all(_tournament(costs, rng, 4) == 3 for _ in range(20))   # todos compiten
    assert _tournament([7, 7, 7], rng, 3) in (0, 1, 2)


# ----------------------------------------------------------- diversidad -------
def test_unique_fraction_casos_conocidos():
    same = [[0, 1, 2, 3, 4]] * 5
    assert _unique_fraction(same) == pytest.approx(1 / 5)
    distinct = [[0, 1, 2, 3, 4], [0, 2, 1, 3, 4], [0, 1, 3, 2, 4], [0, 3, 1, 2, 4]]
    assert _unique_fraction(distinct) == 1.0
    # Una ruta y su inversa son el mismo ciclo.
    assert _unique_fraction([[0, 1, 2, 3, 4], [0, 4, 3, 2, 1]]) == pytest.approx(1 / 2)
    # Rotaciones tambien (el origen se lleva al inicio).
    assert _canonical([2, 3, 4, 0, 1], origin=0) == _canonical([0, 1, 2, 3, 4], origin=0)


def test_canonica_no_altera_el_costo():
    inst = _small_instance(8)
    r = random.Random(1)
    for _ in range(50):
        route = [0] + r.sample(range(1, 8), 7)
        canon = list(_canonical(route))
        assert tour_cost(inst.D, canon) == tour_cost(inst.D, route)


def test_edge_diversity():
    n = 5
    assert _edge_diversity([[0, 1, 2, 3, 4], [0, 4, 3, 2, 1]], n) == pytest.approx(5 / 10)
    assert 0 < _edge_diversity([[0, 1, 2, 3, 4], [0, 2, 4, 1, 3]], n) <= 1


# ---------------------------------------------------- algoritmo completo ------
def _run(inst, evals, seed=0, **kw):
    _, rng = make_rngs(seed)
    return genetic_algorithm(inst, Budget(max_evals=evals), rng, **kw)


def test_ruta_valida_y_costo_coherente():
    inst = load_by_name("burma14")
    res = _run(inst, 3000)
    assert res.validate(inst)
    assert res.algorithm == "GA" and res.tour[0] == 0
    assert res.cost == tour_cost(inst.D, res.tour)
    assert res.gap_percent >= 0
    # el ultimo punto de la traza es el final y coincide con el mejor
    assert res.trace[-1][1] == res.cost and res.trace[-1][0] == res.candidate_evaluations
    costs = [c for _, c, _ in res.trace[:-1]]     # el ultimo punto es el cierre
    assert all(b < a for a, b in zip(costs, costs[1:]))       # mejoras estrictas


@pytest.mark.parametrize("pop,elite", [(10, 1), (40, 2), (20, 0)])
def test_presupuesto_exacto_y_nunca_excedido(pop, elite):
    inst = _small_instance(9)
    for evals in (1, pop - 1, pop, pop + 5, 500, 1234):
        res = _run(inst, evals, population_size=pop, elite_count=elite, pm=0.0, pc=1.0)
        assert res.candidate_evaluations <= evals
        res.validate(inst)
    # Con pc=1 y pm=0 no hay copias heredadas: cada generacion cuesta pop-elite.
    res = _run(inst, 500, population_size=pop, elite_count=elite, pm=0.0, pc=1.0)
    gens = res.extras["generations"]
    assert res.candidate_evaluations == pop + gens * (pop - elite)
    assert res.stop_reason == STOP_EVALS
    # No cabia otra generacion completa:
    assert res.candidate_evaluations + (pop - elite) > 500
    assert res.extras["gen_evals"][0] == pop


def test_presupuesto_menor_que_la_poblacion_inicial():
    inst = _small_instance(9)
    res = _run(inst, 7, population_size=20)
    assert res.candidate_evaluations == 7 and res.stop_reason == STOP_EVALS
    res.validate(inst)                       # mejor de las 7 evaluadas
    res0 = _run(inst, 0, population_size=20)
    assert res0.tour is None and res0.candidate_evaluations == 0
    res0.validate(inst)


def test_limite_de_tiempo():
    inst = load_by_name("eil51")
    _, rng = make_rngs(0)
    res = genetic_algorithm(inst, Budget(max_seconds=0.05), rng)
    assert res.stop_reason == STOP_TIME
    res.validate(inst)


def test_limite_de_generaciones_y_sin_limite_rechazado():
    inst = _small_instance(9)
    _, rng = make_rngs(0)
    res = genetic_algorithm(inst, Budget(max_evals=10 ** 6), rng, population_size=10,
                            max_generations=4)
    assert res.stop_reason == STOP_GENERATIONS and res.extras["generations"] == 4
    with pytest.raises(ValueError):
        genetic_algorithm(inst, Budget(), rng)


def test_elitismo_el_mejor_nunca_empeora():
    inst = load_by_name("gr17")
    for seed in range(4):
        for elite in (1, 2):
            res = _run(inst, 6000, seed=seed, elite_count=elite, pm=0.5)
            best = res.extras["best"]
            assert all(b <= a for a, b in zip(best, best[1:]))
            assert best[-1] == res.cost


def test_sin_elitismo_puede_empeorar_la_poblacion():
    """Contraste: con elite_count=0 el mejor de la poblacion no esta protegido; el
    mejor global (best_so_far) si es monotono porque se conserva aparte."""
    inst = load_by_name("gr17")
    found = False
    for seed in range(10):
        res = _run(inst, 8000, seed=seed, elite_count=0, pm=0.9, population_size=20)
        b = res.extras["best"]
        found = found or any(y > x for x, y in zip(b, b[1:]))
        sf = res.extras["best_so_far"]
        assert all(y <= x for x, y in zip(sf, sf[1:]))
    assert found


def test_reproducibilidad_con_semilla():
    inst = load_by_name("burma14")
    a = _run(inst, 2000, seed=3)
    b = _run(inst, 2000, seed=3)
    c = _run(inst, 2000, seed=4)
    assert a.tour == b.tour and a.cost == b.cost
    assert a.extras["best"] == b.extras["best"]
    assert a.extras["unique_fraction"] == b.extras["unique_fraction"]
    assert (a.tour, a.extras["median"]) != (c.tour, c.extras["median"])


def test_extras_por_generacion_son_consistentes():
    inst = load_by_name("gr17")
    res = _run(inst, 3000)
    ex = res.extras
    L = len(ex["gen_evals"])
    for k in ("best", "median", "mean", "unique_fraction", "edge_diversity", "best_so_far"):
        assert len(ex[k]) == L
    assert all(b <= m for b, m in zip(ex["best"], ex["median"]))
    assert all(0 < u <= 1 and 0 < e <= 1 for u, e in zip(ex["unique_fraction"], ex["edge_diversity"]))
    assert ex["gen_evals"] == sorted(ex["gen_evals"])


def test_parametros_invalidos():
    inst = _small_instance(6)
    _, rng = make_rngs(0)
    for kw in (dict(population_size=1), dict(elite_count=80), dict(tournament_size=0),
               dict(tournament_size=99)):
        with pytest.raises(ValueError):
            genetic_algorithm(inst, Budget(max_evals=100), rng, **kw)


def test_otro_origen_es_valido():
    inst = _small_instance(9)
    _, rng = make_rngs(0)
    res = genetic_algorithm(inst, Budget(max_evals=800), rng, population_size=20, origin=4)
    assert res.tour[0] == 4 and is_valid_tour(res.tour, inst.n, 4)
    assert res.cost == tour_cost(inst.D, res.tour)


# ------------------------------------------- convergencia prematura -----------
def test_convergencia_prematura_vs_configuracion_sana():
    """Poblacion pequena, pm=0 y torneo grande pierden diversidad mucho mas rapido
    que la configuracion sana. Se compara la diversidad (fraccion unica y de
    aristas) tras el mismo presupuesto, promediando semillas."""
    inst = load_by_name("eil51")
    seeds = range(3)

    def finales(**kw):
        u, e, b = [], [], []
        for s in seeds:
            res = _run(inst, 6000, seed=s, **kw)
            u.append(res.extras["unique_fraction"][-1])
            e.append(res.extras["edge_diversity"][-1])
            b.append(res.cost)
        return sum(u) / len(u), sum(e) / len(e), sum(b) / len(b)

    prem = finales(population_size=12, tournament_size=12, pm=0.0, elite_count=2)
    sana = finales(population_size=80, tournament_size=3, pm=0.3, elite_count=2)
    print("\nprematura (unicos, aristas, costo):", prem)
    print("sana      (unicos, aristas, costo):", sana)
    assert prem[0] < 0.5 < sana[0]            # casi toda la poblacion es identica
    assert prem[1] < sana[1]
