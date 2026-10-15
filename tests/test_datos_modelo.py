import itertools
import math

import pytest

from tsp.datos import OPTIMA, load_by_name, read_opt_tour
from tsp.modelo import (OPT_NO_ROUTE, STOP_EVALS, Budget, MemoryMeter, RunResult,
                        gap_percent, is_valid_tour, make_rngs, random_tour,
                        tour_cost, tour_problems)


def euc2d(a, b):                      # implementacion INDEPENDIENTE de la formula
    return int(math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) + 0.5)


def att(a, b):
    r = math.sqrt(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) / 10.0)
    t = int(r + 0.5)
    return t + 1 if t < r else t


@pytest.mark.parametrize("name", ["att48", "berlin52", "brazil58", "gr48", "gr17", "burma14", "eil51"])
def test_ficha_y_matriz(name):
    inst = load_by_name(name)
    assert inst.n == len(inst.D) == len(inst.node_ids)
    assert inst.optimum == OPTIMA[name]
    assert all(inst.D[i][i] == 0 for i in range(inst.n))


def test_berlin52_contra_formula_manual():
    inst = load_by_name("berlin52")
    c = inst.coords
    for i, j in itertools.combinations(range(inst.n), 2):
        assert inst.D[i][j] == euc2d(c[i], c[j])
    assert inst.D[0][1] == 666            # a mano: sqrt(540^2+390^2) = 666.1


def test_att48_contra_formula_manual():
    inst = load_by_name("att48")
    c = inst.coords
    for i, j in itertools.combinations(range(inst.n), 2):
        assert inst.D[i][j] == att(c[i], c[j])


def test_explicit_usa_pesos_del_archivo():
    assert load_by_name("gr48").weight_type == "EXPLICIT"
    assert load_by_name("brazil58").weight_type == "EXPLICIT"


@pytest.mark.parametrize("name", ["att48", "berlin52", "gr48"])
def test_tour_optimo_oficial_costo_exacto(name):
    inst = load_by_name(name)
    r = read_opt_tour("datos/{0}.opt.tour".format(name), inst)
    assert is_valid_tour(r, inst.n, 0)
    assert tour_cost(inst.D, r) == inst.optimum


def test_rutas_invalidas_se_rechazan():
    assert tour_problems([0, 1, 1, 3], 4)                  # duplicada
    assert tour_problems([0, 1, 3], 4)                     # omitida
    assert tour_problems([0, 1, 2, 4], 4)                  # fuera de rango
    assert tour_problems([1, 0, 2, 3], 4, origin=0)        # origen incorrecto
    assert not tour_problems([0, 2, 1, 3], 4, origin=0)


def test_costo_incluye_cierre():
    D = ((0, 1, 5), (1, 0, 2), (5, 2, 0))
    assert tour_cost(D, [0, 1, 2]) == 1 + 2 + 5


def test_subinstancia_conserva_pesos_originales():
    inst = load_by_name("att48")
    s = inst.subinstance(8)
    assert s.n == 8 and s.node_ids == inst.node_ids[:8] and s.optimum is None
    assert all(s.D[i][j] == inst.D[i][j] for i in range(8) for j in range(8))


def test_rngs_independientes_y_reproducibles():
    a1, b1 = make_rngs(3)
    a2, b2 = make_rngs(3)
    assert random_tour(10, a1) == random_tour(10, a2)
    assert [b1.random() for _ in range(3)] == [b2.random() for _ in range(3)]
    assert random_tour(10, make_rngs(3)[0]) != random_tour(10, make_rngs(4)[0])


def test_budget_gap_y_contrato():
    b = Budget(max_evals=5).start()
    assert b.check(evals=4) is None and b.check(evals=5) == STOP_EVALS
    assert gap_percent(110, 100) == pytest.approx(10.0) and gap_percent(None, 100) is None
    r = RunResult("x", "a", tour=None, optimality_status=OPT_NO_ROUTE)
    assert r.validate(load_by_name("gr17"))


def test_memory_meter():
    with MemoryMeter() as m:
        x = [list(range(1000)) for _ in range(100)]
        assert m.current_bytes() > 100_000
    assert m.peak_bytes >= 100_000
