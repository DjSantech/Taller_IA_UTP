# -*- coding: utf-8 -*-
"""Pruebas del algoritmo memetico (GA + 2-opt)."""
import pytest

from tsp.datos import load_by_name
from tsp.ga import genetic_algorithm
from tsp.memetico import memetic_algorithm
from tsp.modelo import STOP_EVALS, Budget, make_rngs, tour_cost


def _run(name, evals, seed=0, **kw):
    inst = load_by_name(name)
    _, rng = make_rngs(seed)
    return inst, memetic_algorithm(inst, Budget(max_evals=evals), rng, **kw)


def test_ruta_valida_costo_coherente_y_algoritmo():
    inst, res = _run("burma14", 4000)
    assert res.validate(inst) and res.algorithm == "GA+2opt"
    assert res.cost == tour_cost(inst.D, res.tour)


@pytest.mark.parametrize("evals", [1, 5, 39, 40, 200, 1500, 4321])
def test_nunca_excede_el_presupuesto(evals):
    inst, res = _run("gr17", evals, population_size=10)
    assert res.candidate_evaluations <= evals
    res.validate(inst)


def test_se_agota_el_presupuesto_exactamente():
    """La busqueda local consume hasta el ultimo delta disponible."""
    _, res = _run("eil51", 3000)
    assert res.candidate_evaluations == 3000 and res.stop_reason == STOP_EVALS


def test_trabajo_de_busqueda_local_esta_contado_y_desglosado():
    _, res = _run("gr17", 5000)
    ex = res.extras
    assert res.candidate_evaluations == ex["child_evals"] + ex["ls_evals"]
    assert ex["ls_evals"] > 0 and ex["ls_moves"] > 0


def test_ls_max_evals_limita_por_hijo():
    _, res = _run("gr17", 5000, ls_max_evals=5)
    assert res.extras["ls_evals"] <= 5 * res.extras["child_evals"]


def test_elitismo_y_reproducibilidad():
    _, a = _run("burma14", 3000, seed=2)
    _, b = _run("burma14", 3000, seed=2)
    assert a.tour == b.tour and a.extras["best"] == b.extras["best"]
    best = a.extras["best"]
    assert all(y <= x for x, y in zip(best, best[1:]))


def test_memetico_supera_al_ga_basico_con_el_mismo_presupuesto():
    """No es una garantia teorica; se comprueba sobre eil51 con 3 semillas y el
    mismo presupuesto de evaluaciones (la ventaja viene de la busqueda local)."""
    inst = load_by_name("eil51")
    ga, mem = [], []
    for s in range(3):
        _, rng = make_rngs(s)
        ga.append(genetic_algorithm(inst, Budget(max_evals=20000), rng).cost)
        _, rng = make_rngs(s)
        mem.append(memetic_algorithm(inst, Budget(max_evals=20000), rng).cost)
    print("\nGA:", ga, "GA+2opt:", mem)
    assert sorted(mem)[1] < sorted(ga)[1]            # mediana


def test_limites_invalidos():
    inst = load_by_name("gr17")
    _, rng = make_rngs(0)
    with pytest.raises(ValueError):
        memetic_algorithm(inst, Budget(), rng)
    with pytest.raises(ValueError):
        memetic_algorithm(inst, Budget(max_evals=10), rng, elite_count=99)
