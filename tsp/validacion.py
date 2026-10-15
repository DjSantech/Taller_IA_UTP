# -*- coding: utf-8 -*-
"""Bateria de validacion de la seccion 13, ejecutable DENTRO del cuaderno.

Cada fila de la tabla del enunciado es una funcion `_check_*` que lanza
AssertionError si la propiedad falla y devuelve un texto con la evidencia si pasa.
Los oraculos (enumeracion, Kruskal, clave de estado equivocada) estan escritos
aparte de los solvers para que un error compartido no se cancele. La suite
completa con mas casos vive en `tests/` (pytest); esta es la parte visible.
"""
import heapq
import itertools
import random

from tsp.modelo import (Budget, STOP_EVALS, STOP_EXPANSIONS, OPT_NO_ROUTE, OPT_PROVEN,
                        is_valid_tour, make_rngs, random_tour, tour_cost, tour_problems)
from tsp.mst import heuristic_mst, mst_cost, mst_edges
from tsp.astar import astar
from tsp.rbfs import rbfs
from tsp.vecindad import two_opt_delta, valid_pairs
from tsp.hc import hill_climbing
from tsp.sa import simulated_annealing
from tsp.ga import _invert_segment, _ox, genetic_algorithm


# --- Oraculos independientes -------------------------------------------------------
class _Inst:
    """Instancia minima para alimentar a los solvers con una matriz arbitraria."""

    def __init__(self, D, name="matriz"):
        self.D = tuple(tuple(f) for f in D)
        self.n = len(D)
        self.name = name
        self.node_ids = tuple(range(1, self.n + 1))
        self.parent = None
        self.optimum = None
        self.coords = None
        self.weight_type = "EXPLICIT"


def _random_matrix(n, seed, hi=20):
    rng = random.Random(seed)
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            D[i][j] = D[j][i] = rng.randint(1, hi)
    return D


def _brute(D, origin=0):
    """Costo optimo por enumeracion de todas las rutas (solo n pequeno)."""
    n = len(D)
    resto = [c for c in range(n) if c != origin]
    mejor = None
    for p in itertools.permutations(resto):
        r = (origin,) + p
        c = sum(D[r[i]][r[(i + 1) % n]] for i in range(n))
        if mejor is None or c < mejor:
            mejor = c
    return mejor


def _best_completion(D, origin, prefix):
    """Costo restante OPTIMO desde el ultimo nodo del prefijo (enumera continuaciones)."""
    pend = [c for c in range(len(D)) if c not in prefix]
    last = prefix[-1]
    if not pend:
        return D[last][origin]
    mejor = None
    for p in itertools.permutations(pend):
        ruta = (last,) + p + (origin,)
        c = sum(D[ruta[i]][ruta[i + 1]] for i in range(len(ruta) - 1))
        if mejor is None or c < mejor:
            mejor = c
    return mejor


def _kruskal(D, nodes):
    nodes = list(nodes)
    padre = {v: v for v in nodes}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x
    aristas = sorted((D[a][b], a, b) for a, b in itertools.combinations(nodes, 2))
    total = 0
    for w, a, b in aristas:
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[ra] = rb
            total += w
    return total


# Contraejemplo de la actividad de la seccion 5 (n = 5, origen 0): las rutas parciales
# X = 0,1,3 (pendientes {2,4}, g = 2) e Y = 0,1,2,3 (pendientes {4}, g = 3) terminan en
# la MISMA ciudad 3. X es mas barata hasta ahi, pero el optimo (5) solo sale de Y.
_CONTRA_A = [[0, 1, 10, 10, 1], [1, 0, 1, 1, 10], [10, 1, 0, 1, 10],
             [10, 1, 1, 0, 1], [1, 10, 10, 1, 0]]
# Otra matriz (pesos 1..9) donde la variante incorrecta se queda con la frontera vacia.
_CONTRA_B = [[0, 7, 7, 1, 5], [7, 0, 9, 8, 7], [7, 9, 0, 5, 8],
             [1, 8, 5, 0, 6], [5, 7, 8, 6, 0]]


def _astar_clave_incorrecta(D, origin=0):
    """A* identico al real salvo la clave de estado, que aqui es (ultima ciudad,
    cerrado) y OLVIDA el conjunto de pendientes: el error de la pagina TSP Solve.
    Existe unicamente para demostrar que pierde el optimo (o la ruta completa)."""
    n = len(D)
    todas = frozenset(range(n)) - {origin}
    mejor = {(origin, False): 0}
    heap = [(heuristic_mst(D, origin, origin, todas, False), 0, 0, origin, todas, False)]
    cuenta = 1
    while heap:
        _, _, g, last, rem, cerrado = heapq.heappop(heap)
        if g > mejor[(last, cerrado)]:
            continue
        if cerrado:
            return g
        if not rem:
            hijos = [(origin, rem, True, g + D[last][origin])]
        else:
            hijos = [(v, rem - {v}, False, g + D[last][v]) for v in sorted(rem)]
        for v, nr, cer, ng in hijos:
            clave = (v, cer)                      # <- el error: ignora `nr`
            if ng < mejor.get(clave, float("inf")):
                mejor[clave] = ng
                h = 0 if cer else heuristic_mst(D, origin, v, nr, False)
                heapq.heappush(heap, (ng + h, h, cuenta, v, nr, cer))
                cuenta += 1
    return None


# --- Comprobaciones (una por fila de la tabla 13) ------------------------------------
def _check_ruta_invalida():
    for r in ([0, 1, 1, 3, 4], [0, 1, 2, 3], [0, 1, 2, 3, 9], [1, 0, 2, 3, 4]):
        assert tour_problems(r, 5, origin=0), r
    assert not tour_problems([0, 3, 1, 4, 2], 5, origin=0)
    return "duplicada, omitida, fuera de rango y origen incorrecto se rechazan; una permutacion valida pasa"


def _check_costo_con_cierre(inst):
    rng = random.Random(7)
    for _ in range(200):
        r = random_tour(inst.n, rng)
        indep = sum(inst.D[r[i]][r[(i + 1) % inst.n]] for i in range(inst.n))
        assert tour_cost(inst.D, r) == indep
    return "200 rutas aleatorias de {0}: tour_cost == suma independiente con cierre".format(inst.name)


def _check_mst(inst):
    D = inst.D
    assert mst_cost(D, []) == 0 and mst_cost(D, [3]) == 0
    assert mst_edges(D, []) == [] and mst_edges(D, [3]) == []
    rng = random.Random(3)
    for tam in (2, 3, 5, 8, 12):
        for _ in range(20):
            U = rng.sample(range(inst.n), tam)
            aristas = mst_edges(D, U)
            assert len(aristas) == tam - 1
            vistos = {U[0]}
            for _ in range(tam):                  # conexo: se alcanza todo U desde U[0]
                for a, b, _w in aristas:
                    if a in vistos or b in vistos:
                        vistos.update((a, b))
            assert vistos == set(U)
            assert sum(w for _, _, w in aristas) == mst_cost(D, U) == _kruskal(D, U)
    return "|U| = 0 y 1 dan 0; para |U| en {2,3,5,8,12} (100 conjuntos) hay |U|-1 aristas, es conexo y su peso == Prim == Kruskal"


def _check_heuristica(inst):
    sub = inst.subinstance(7)
    casos = [("{0}[k=7]".format(inst.name), sub.D), ("aleatoria-7", _random_matrix(7, 11))]
    total = 0
    consistente = True
    for nombre, D in casos:
        n = len(D)
        for largo in range(1, n):
            for resto in itertools.permutations(range(1, n), largo - 1):
                prefijo = (0,) + resto
                pend = [c for c in range(n) if c not in prefijo]
                g = sum(D[prefijo[i]][prefijo[i + 1]] for i in range(len(prefijo) - 1))
                h = heuristic_mst(D, 0, prefijo[-1], pend, False)
                assert h <= _best_completion(D, 0, prefijo), (nombre, prefijo)
                total += 1
                for v in pend:                    # consistencia h(n) <= c(n,n') + h(n')
                    h2 = heuristic_mst(D, 0, v, [c for c in pend if c != v], False)
                    if h > D[prefijo[-1]][v] + h2:
                        consistente = False
    return ("h <= residual optimo enumerado en {0} prefijos de 2 casos de 7 ciudades. "
            "Consistencia (h(n) <= c + h(n')) {1} en esos casos".format(
                total, "se cumple" if consistente else "NO se cumple siempre (ver apunte 5)"))


def _check_astar_exacto(inst):
    pruebas = 0
    for k in (6, 8):
        sub = inst.subinstance(k)
        r = astar(sub)
        assert r.optimality_status == OPT_PROVEN and r.cost == _brute(sub.D) and is_valid_tour(r.tour, k, 0)
        pruebas += 1
    for s in range(15):
        D = _random_matrix(7, s)
        r = astar(_Inst(D))
        assert r.cost == _brute(D)
        pruebas += 1
    return "{0} casos (subinstancias k=6,8 y 15 matrices aleatorias de 7): A* == enumeracion exhaustiva".format(pruebas)


def _check_clave_de_estado():
    D = _CONTRA_A
    X, Y = [0, 1, 3], [0, 1, 2, 3]
    gX = D[0][1] + D[1][3]
    gY = D[0][1] + D[1][2] + D[2][3]
    totX, totY = gX + _best_completion(D, 0, X), gY + _best_completion(D, 0, Y)
    assert X[-1] == Y[-1] and gX < gY and totY < totX and totY == _brute(D)
    detalle = ["rutas {0} y {1} terminan en la ciudad 3 con g = {2} < {3}, pero el mejor total "
               "por la primera es {4} y por la segunda {5} (el optimo)".format(X, Y, gX, gY, totX, totY)]
    for nombre, M in (("A", _CONTRA_A), ("B", _CONTRA_B)):
        opt = _brute(M)
        mal = _astar_clave_incorrecta(M)
        assert mal is None or mal > opt, nombre
        assert astar(_Inst(M)).cost == opt
        detalle.append("matriz {0}: clave = ultima ciudad -> {1} (optimo {2}); clave completa -> {2}".format(
            nombre, "sin ruta" if mal is None else mal, opt))
    return "; ".join(detalle)


def _check_rbfs():
    detalle = []
    D2 = [[0, 5], [5, 0]]                            # un solo hijo en cada nivel
    assert rbfs(_Inst(D2)).cost == 10
    detalle.append("un hijo")
    D4 = [[0, 3, 3, 3], [3, 0, 3, 3], [3, 3, 0, 3], [3, 3, 3, 0]]   # todos empatan
    assert rbfs(_Inst(D4)).cost == _brute(D4) == 12
    detalle.append("empates")
    for s in range(15):
        D = _random_matrix(7, 100 + s)
        r = rbfs(_Inst(D))
        assert r.cost == _brute(D) and r.optimality_status == OPT_PROVEN
    detalle.append("15 matrices (limites y retrocesos)")
    r = rbfs(_Inst(_random_matrix(9, 5)), budget=Budget(max_expansions=3))
    assert r.tour is None and r.optimality_status == OPT_NO_ROUTE and r.stop_reason == STOP_EXPANSIONS
    detalle.append("agotamiento del presupuesto -> sin ruta, motivo EXPANSION_LIMIT")
    return "; ".join(detalle)


def _check_hc_optimo_local(inst):
    rng, _ = make_rngs(1)
    r = hill_climbing(inst, random_tour(inst.n, rng), Budget(max_evals=10 ** 6))
    assert r.stop_reason == "LOCAL_OPTIMUM"
    pares = list(valid_pairs(inst.n))
    mejor = min(two_opt_delta(inst.D, r.tour, i, j) for i, j in pares)
    assert mejor >= 0
    return "{0}: tras HC se enumeraron los {1} vecinos 2-opt; el mejor delta es {2} >= 0".format(
        inst.name, len(pares), mejor)


def _check_sa_mejor_vs_actual(inst):
    for semilla in range(30):
        init, algo = make_rngs(semilla)
        ruta = random_tour(inst.n, init)
        r = simulated_annealing(inst, ruta, Budget(max_evals=3000), algo, 1e6, 1e5, 0.99, 1000)
        r.validate(inst)
        actual = r.extras["final_current_cost"]
        assert r.cost <= actual
        if r.cost < actual:
            return ("semilla {0} con T alta: costo actual final {1} > mejor observada {2}; "
                    "SA devuelve la mejor".format(semilla, actual, r.cost))
    raise AssertionError("no se observo la diferencia mejor/actual")


def _check_ox_inversion():
    rng = random.Random(0)
    n = 0
    for tam in (2, 3, 6, 11):
        genes = list(range(tam))
        for _ in range(300):
            p1, p2 = rng.sample(genes, tam), rng.sample(genes, tam)
            for left, right in ((0, 0), (0, tam - 1), (tam - 1, tam - 1), (0, tam // 2),
                                tuple(sorted((rng.randrange(tam), rng.randrange(tam))))):
                assert sorted(_ox(p1, p2, left, right)) == genes
                assert sorted(_invert_segment(p1, left, right)) == genes
                n += 2
    # Actividad manual de 12.1: segmento de posiciones 2 a 4 (1-based) = indices 1..3.
    # Hijo a mano: [_, C, D, E, _, _]; se rellena desde la posicion 5 con los genes de
    # parent2 leidos desde su posicion 5 (F, D, E, B, G, C) sin los ya presentes: F, B, G.
    assert _ox(list("BCDEFG"), list("EBGCFD"), 1, 3) == list("GCDEFB")
    return ("{0} operaciones con cortes frontera: toda ciudad aparece exactamente una vez; "
            "la actividad manual da [G,C,D,E,F,B]".format(n))


def _check_presupuesto(inst):
    r = astar(inst, budget=Budget(max_expansions=5))
    assert r.tour is None and r.optimality_status == OPT_NO_ROUTE and r.stop_reason == STOP_EXPANSIONS
    init, algo = make_rngs(0)
    hc = hill_climbing(inst, random_tour(inst.n, init), Budget(max_evals=25))
    assert hc.stop_reason == STOP_EVALS and hc.candidate_evaluations <= 25 and is_valid_tour(hc.tour, inst.n, 0)
    ga = genetic_algorithm(inst, Budget(max_evals=500), algo, population_size=40)
    assert ga.candidate_evaluations <= 500 and is_valid_tour(ga.tour, inst.n, 0)
    return ("A* con 5 expansiones: sin ruta y EXPANSION_LIMIT; HC con 25 evaluaciones usa {0} y devuelve ruta valida; "
            "GA con 500 usa {1} y devuelve ruta valida".format(hc.candidate_evaluations, ga.candidate_evaluations))


def run_validation_suite(instances):
    """Ejecuta todas las comprobaciones; devuelve [(elemento, caso, ok, detalle)]."""
    berlin, gr17 = instances["berlin52"], instances["gr17"]
    plan = [
        ("Ruta", "Ciudad duplicada u omitida", _check_ruta_invalida, ()),
        ("Costo", "Ruta completa con cierre", _check_costo_con_cierre, (berlin,)),
        ("MST", "Cero, uno y varios pendientes", _check_mst, (berlin,)),
        ("Heurística", "Prefijos de casos de 7 ciudades", _check_heuristica, (instances["eil51"],)),
        ("A*", "Subinstancias pequeñas vs. enumeración", _check_astar_exacto, (instances["att48"],)),
        ("A*", "Dos conjuntos pendientes distintos no se fusionan", _check_clave_de_estado, ()),
        ("RBFS", "Un hijo, empate, límite y agotamiento", _check_rbfs, ()),
        ("HC", "Vecindario completo sin mejora", _check_hc_optimo_local, (gr17,)),
        ("SA", "Mejor ruta distinta de la actual", _check_sa_mejor_vs_actual, (gr17,)),
        ("OX e inversión", "Cortes frontera, muchas semillas", _check_ox_inversion, ()),
        ("Presupuesto", "Interrupción forzada", _check_presupuesto, (gr17,)),
    ]
    filas = []
    for elemento, caso, funcion, args in plan:
        try:
            filas.append((elemento, caso, True, funcion(*args)))
        except AssertionError as e:
            filas.append((elemento, caso, False, "FALLÓ: {0!r}".format(e)))
    return filas


def format_validation(filas):
    out = ["| Elemento | Caso exigido | Resultado | Evidencia |", "|---|---|---|---|"]
    for elemento, caso, ok, detalle in filas:
        out.append("| {0} | {1} | {2} | {3} |".format(elemento, caso, "✔" if ok else "✘", detalle))
    return "\n".join(out)
