# -*- coding: utf-8 -*-
"""Demostraciones rapidas para la sustentacion (segundos, no los 25 minutos del cuaderno).

Uso (desde la carpeta del proyecto):
    C:\\Users\\santi\\venvs\\ia-taller2\\Scripts\\python.exe tools\\demo_sustentacion.py          # todas
    C:\\Users\\santi\\venvs\\ia-taller2\\Scripts\\python.exe tools\\demo_sustentacion.py A D E    # solo esas

Cada demo imprime lo que hace y el resultado. Son las de la guia estudio/Etapa14_defensa.txt.
"""
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
sys.stdout.reconfigure(encoding="utf-8")

from tsp.datos import load_by_name
from tsp.modelo import Budget, make_rngs, random_tour, tour_cost
from tsp.astar import astar
from tsp.rbfs import rbfs
from tsp.vecindad import two_opt_delta, swap_delta, count_valid_pairs
from tsp.hc import hill_climbing
from tsp.ga import genetic_algorithm, _ox
from tsp.experimentos import frozen_copy, run_one


def titulo(t):
    print("\n" + "=" * 78 + "\n" + t + "\n" + "=" * 78)


def demo_A():
    titulo("A) A* con heuristica MST vs. h = 0 (berlin52, primeras 10 ciudades)")
    sub = load_by_name("berlin52").subinstance(10)
    a, z = astar(sub), astar(sub, heuristic="zero")
    print("A* + MST : costo {0}, expansiones {1}".format(a.cost, a.expanded))
    print("A* h = 0 : costo {0}, expansiones {1}  (= 1 + 9*2^8 = 2305: TODO el espacio)".format(z.cost, z.expanded))
    print("Mismo costo optimo; la cota MST evita expandir casi todo.")


def demo_B():
    titulo("B) Invarianza del costo optimo al cambiar el origen")
    sub = load_by_name("berlin52").subinstance(10)
    for o in (0, 4, 9):
        r = astar(sub, origin=o)
        print("origen {0}: costo {1}  ruta {2}".format(o, r.cost, r.tour))
    print("Si el costo cambiara con el origen, la clave de estado estaria mal (pagina TSP Solve).")


def demo_C():
    titulo("C) 2-opt vs. swap sobre la MISMA ruta (berlin52, par de posiciones (3, 10))")
    inst = load_by_name("berlin52")
    ruta = random_tour(inst.n, make_rngs(0)[0])
    print("costo de la ruta: {0}".format(tour_cost(inst.D, ruta)))
    print("delta 2-opt (3,10) = {0}   |   delta swap (3,10) = {1}".format(
        two_opt_delta(inst.D, ruta, 3, 10), swap_delta(inst.D, ruta, 3, 10)))
    print("Pares 2-opt validos con n=48: n(n-3)/2 = {0}; pares de swap: n(n-1)/2 = {1}".format(
        count_valid_pairs(48), 48 * 47 // 2))


def demo_D():
    titulo("D) Simulated Annealing: alpha calibrado (0.97) vs. alpha = 0.90 (eil51, optimo 426)")
    inst = load_by_name("eil51")
    for alpha in (0.97, 0.90):
        cfg = frozen_copy()
        cfg["sa"]["alpha"] = alpha
        r = run_one("SA", inst, seed=0, config=cfg, scale="B")
        print("alpha {0}: costo {1}, gap {2:.2f} %, propuestas por temperatura {3}, parada {4}".format(
            alpha, r.cost, r.gap_percent, r.parameters["steps"], r.stop_reason))


def demo_E():
    titulo("E) Convergencia prematura del GA (eil51, 6000 evaluaciones)")
    inst = load_by_name("eil51")
    for nombre, kw in (("prematuro (pob 12, torneo 12, pm 0)", dict(population_size=12, tournament_size=12, pm=0.0)),
                       ("sano (pob 80, torneo 3, pm 0.3)", dict(population_size=80, tournament_size=3, pm=0.3))):
        _, rng = make_rngs(0)
        r = genetic_algorithm(inst, Budget(max_evals=6000), rng, elite_count=2, **kw)
        print("{0}: costo {1}, individuos unicos {2:.3f}, diversidad de aristas {3:.3f}".format(
            nombre, r.cost, r.extras["unique_fraction"][-1], r.extras["edge_diversity"][-1]))


def demo_F():
    titulo("F) Hill Climbing: mejor mejora vs. primera mejora (berlin52, primeras 30 ciudades)")
    sub = load_by_name("berlin52").subinstance(30)
    for est in ("best", "first"):
        r = hill_climbing(sub, random_tour(sub.n, make_rngs(0)[0]), Budget(max_evals=30000), strategy=est)
        print("{0:5s}: costo {1}, evaluaciones {2}, parada {3}".format(est, r.cost, r.candidate_evaluations, r.stop_reason))


def demo_G():
    titulo("G) Por que importa el regreso al origen (ruta optima oficial de att48)")
    from tsp.datos import read_opt_tour
    inst = load_by_name("att48")
    ruta = read_opt_tour("datos/att48.opt.tour", inst)
    c = tour_cost(inst.D, ruta)
    print("costo cerrado {0} (= optimo oficial {1}); sin la arista de regreso: {2}".format(
        c, inst.optimum, c - inst.D[ruta[-1]][ruta[0]]))


def demo_H():
    titulo("H) A* contra RBFS: memoria contra recomputacion (att48, primeras 10 ciudades)")
    sub = load_by_name("att48").subinstance(10)
    for f in (astar, rbfs):
        t = time.perf_counter()
        r = f(sub)
        print("{0}: costo {1}, expansiones {2}, memoria {3:.1f} KiB, {4:.2f} s".format(
            r.algorithm, r.cost, r.expanded, r.peak_memory / 1024, time.perf_counter() - t))


def demo_I():
    titulo("I) Cruce OX de la actividad manual (seccion 12.1)")
    hijo = _ox(list("BCDEFG"), list("EBGCFD"), 1, 3)
    print("parent1 = B C D E F G | parent2 = E B G C F D | segmento posiciones 2 a 4")
    print("hijo    = " + " ".join(hijo) + "   (esperado: G C D E F B)")


DEMOS = {k[-1]: v for k, v in globals().items() if k.startswith("demo_")}

if __name__ == "__main__":
    elegidas = [a.upper() for a in sys.argv[1:]] or sorted(DEMOS)
    for letra in elegidas:
        DEMOS[letra]()
