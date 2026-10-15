# -*- coding: utf-8 -*-
"""Pruebas de MST, heuristica, A* y RBFS (tabla de la seccion 13 del enunciado).

El oraculo (tests/oraculo.py) esta escrito aparte de los solvers: enumera todas
las rutas con su propio calculo de costo, para que un error compartido no se cancele.
"""
import heapq
import itertools
import math
import random

import pytest

from oraculo import best_completion_cost, brute_force, closed_cost
from tsp.astar import (SearchNode, astar, make_heuristic, make_root, mask_cities,
                       route_of, successors)
from tsp.datos import TSPInstance, load_by_name
from tsp.modelo import (Budget, OPT_NO_ROUTE, OPT_PROVEN, STOP_EXHAUSTED,
                        STOP_EXPANSIONS, STOP_MEMORY, STOP_OPTIMAL, STOP_TIME,
                        is_valid_tour, tour_cost)
from tsp.mst import heuristic_mst, heuristic_zero, mst_cost, mst_edges
from tsp.rbfs import _FAILURE, _FOUND, _INF, _RBFSRun, rbfs

REAL = ["att48", "berlin52", "brazil58", "gr48", "gr17", "burma14", "eil51"]

# Microcaso 6.2 (A..E = 0..4)
MICRO = [[0, 4, 6, 7, 3],
         [4, 0, 2, 5, 6],
         [6, 2, 0, 3, 4],
         [7, 5, 3, 0, 2],
         [3, 6, 4, 2, 0]]


# ---------------------------------------------------------------------------
# utilidades de prueba
# ---------------------------------------------------------------------------
def make_inst(D, name="test"):
    n = len(D)
    return TSPInstance(name, list(range(1, n + 1)), D, None, "EXPLICIT", None)


def random_matrix(n, rng, lo=1, hi=25):
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            D[i][j] = D[j][i] = rng.randint(lo, hi)
    return D


def euclid_matrix(n, rng):
    pts = [(rng.randint(0, 50), rng.randint(0, 50)) for _ in range(n)]
    return [[int(math.hypot(a[0] - b[0], a[1] - b[1]) + 0.5) for b in pts] for a in pts]


def all_prefixes(n, origin=0):
    """Todos los prefijos de ruta que empiezan en el origen (incluye el trivial)."""
    pila = [[origin]]
    while pila:
        p = pila.pop()
        yield p
        for v in range(n):
            if v not in p:
                pila.append(p + [v])


def kruskal_cost(D, nodes):
    """MST independiente (Kruskal con union-find) para contrastar con Prim."""
    nodes = list(nodes)
    aristas = sorted((D[a][b], a, b) for a, b in itertools.combinations(nodes, 2))
    padre = {v: v for v in nodes}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x
    total = 0
    for w, a, b in aristas:
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[ra] = rb
            total += w
    return total


def mask_of(cities):
    m = 0
    for c in cities:
        m |= 1 << c
    return m


# ---------------------------------------------------------------------------
# MST
# ---------------------------------------------------------------------------
def test_mst_fronteras_cero_uno_dos():
    assert mst_cost(MICRO, []) == 0
    assert mst_cost(MICRO, [3]) == 0
    assert mst_cost(MICRO, [1, 4]) == MICRO[1][4]
    assert mst_edges(MICRO, []) == []
    assert mst_edges(MICRO, [2]) == []


def test_mst_microcaso_U_CDE_cuesta_5():
    # enunciado 6.2: U = {C,D,E} -> aristas D-E (2) y C-D (3)
    assert mst_cost(MICRO, [2, 3, 4]) == 5
    pesos = sorted(w for _, _, w in mst_edges(MICRO, [2, 3, 4]))
    assert pesos == [2, 3]


@pytest.mark.parametrize("seed", range(40))
def test_mst_es_arbol_y_coincide_con_kruskal(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 12)
    D = random_matrix(n, rng, lo=0, hi=15)       # con ceros y empates
    nodes = rng.sample(range(n), rng.randint(2, n))
    edges = mst_edges(D, nodes)
    assert len(edges) == len(nodes) - 1           # un arbol tiene |U|-1 aristas
    # conexo y sin ciclos: union-find nunca une dos veces lo ya unido
    padre = {v: v for v in nodes}

    def raiz(x):
        while padre[x] != x:
            x = padre[x]
        return x
    for a, b, w in edges:
        assert a in padre and b in padre and w == D[a][b]
        ra, rb = raiz(a), raiz(b)
        assert ra != rb, "ciclo en el MST"
        padre[ra] = rb
    assert len({raiz(v) for v in nodes}) == 1     # una sola componente
    total = sum(w for _, _, w in edges)
    assert total == mst_cost(D, nodes) == kruskal_cost(D, nodes)


# ---------------------------------------------------------------------------
# Heuristica: casos de la formula
# ---------------------------------------------------------------------------
def test_heuristica_casos_de_la_formula():
    # cerrado -> 0
    assert heuristic_mst(MICRO, 0, 0, [], True) == 0
    assert heuristic_mst(MICRO, 0, 0, [1, 2], True) == 0
    # sin pendientes -> d(v, s)
    assert heuristic_mst(MICRO, 0, 3, [], False) == MICRO[3][0] == 7
    # un pendiente -> EXACTO d(v,u) + d(u,s)
    assert heuristic_mst(MICRO, 0, 3, [4], False) == MICRO[3][4] + MICRO[4][0] == 5
    # microcaso: prefijo A->B tiene h = 5 + 2 + 3 = 10
    assert heuristic_mst(MICRO, 0, 1, [2, 3, 4], False) == 10
    assert heuristic_zero(MICRO, 0, 1, [2, 3, 4], False) == 0


def test_heuristica_raiz_con_la_misma_ciudad_en_ambas_conexiones():
    # raiz del microcaso: MST{B,C,D,E}=7, min d(A,u)=3 (E) y min d(u,A)=3 (E): la
    # misma ciudad sirve a las dos conexiones; sigue siendo cota valida (13 <= 14)
    assert heuristic_mst(MICRO, 0, 0, [1, 2, 3, 4], False) == 13


# ---------------------------------------------------------------------------
# Microcaso 6.2
# ---------------------------------------------------------------------------
def test_microcaso_hijos_de_la_raiz():
    inst = make_inst(MICRO, "micro")
    h, _ = make_heuristic(inst.D, 0, "mst")
    root = make_root(5, 0)
    hijos = {c.last: (c.g, h(c.last, c.remaining, c.closed)) for c in
             successors(inst.D, 0, root)}
    # calculado A MANO en la guia (Etapa 3):  ciudad: (g, h)
    assert hijos == {1: (4, 10), 2: (6, 12), 3: (7, 11), 4: (3, 11)}
    f = {c: g + hh for c, (g, hh) in hijos.items()}
    assert f == {1: 14, 2: 18, 3: 18, 4: 14}       # empate B y E en f = 14


def test_microcaso_optimo_por_enumeracion_y_por_los_solvers():
    costo, ruta, cuenta = brute_force(MICRO)
    assert costo == 14 and cuenta == 2 and ruta in ([0, 1, 2, 3, 4], [0, 4, 3, 2, 1])
    inst = make_inst(MICRO, "micro")
    for solver in (astar, rbfs):
        r = solver(inst)
        assert r.cost == 14 and r.optimality_status == OPT_PROVEN
        assert r.tour == [0, 1, 2, 3, 4]            # el desempate elige B (h menor)


def test_microcaso_desempate_determinista_elige_B_antes_que_E():
    # B y E empatan en f=14; B tiene h=10 (menor) y E h=11: A* expande B primero
    log = []
    astar(make_inst(MICRO), log=log)
    assert log[0][:4] == (0, 13, 13, 0)             # raiz: g=0 h=13 f=13
    assert log[1][3] == 1                           # segunda expansion: B (posicion 1)


# ---------------------------------------------------------------------------
# Admisibilidad y consistencia sobre TODOS los prefijos
# ---------------------------------------------------------------------------
def _casos_h():
    casos = []
    for s in range(6):
        rng = random.Random(100 + s)
        casos.append(("rand", random_matrix(rng.choice([6, 7]), rng)))
    for s in range(4):
        rng = random.Random(200 + s)
        casos.append(("euc", euclid_matrix(rng.choice([6, 7]), rng)))
    casos.append(("rand8", random_matrix(8, random.Random(300))))
    casos.append(("micro", MICRO))
    for nombre in ("att48", "gr17", "burma14"):
        casos.append((nombre + "[k=7]", load_by_name(nombre).subinstance(7).D))
    return casos


def test_admisibilidad_sobre_todos_los_prefijos():
    revisados = 0
    for etiqueta, D in _casos_h():
        n = len(D)
        for p in all_prefixes(n):
            rem = [c for c in range(n) if c not in p]
            h = heuristic_mst(D, 0, p[-1], rem, False)
            real = best_completion_cost(D, 0, p)       # residual OPTIMO enumerado
            assert h <= real, (etiqueta, p, h, real)
            if len(rem) <= 1:
                assert h == real                        # con <=1 pendiente h es exacta
            revisados += 1
    assert revisados > 20000


def test_consistencia_h_n_menor_o_igual_c_mas_h_hijo():
    """Resultado: la heuristica MST ES consistente en este modelo (sin necesitar
    desigualdad triangular). Demostracion en estudio/Etapa5_teoria.txt:
    MST(U) <= MST(U-w) + min_u d(w,u), min_u d(v,u) <= d(v,w), min d(u,s) sobre U <=
    sobre U-w. Aqui se comprueba por enumeracion y se cuentan violaciones."""
    violaciones, revisadas = [], 0
    for etiqueta, D in _casos_h():
        n = len(D)
        for p in all_prefixes(n):
            rem = [c for c in range(n) if c not in p]
            h = heuristic_mst(D, 0, p[-1], rem, False)
            if not rem:      # ultimo paso: cerrar el ciclo
                hijo = (D[p[-1]][0], 0)
                if h > hijo[0] + hijo[1]:
                    violaciones.append((etiqueta, p, "cierre"))
                revisadas += 1
                continue
            for v in rem:
                c = D[p[-1]][v]
                h2 = heuristic_mst(D, 0, v, [u for u in rem if u != v], False)
                revisadas += 1
                if h > c + h2:
                    violaciones.append((etiqueta, p, v, h, c, h2))
    print("\nCONSISTENCIA: transiciones revisadas={0} violaciones={1}"
          .format(revisadas, len(violaciones)))
    assert violaciones == [], violaciones[:3]


def test_con_h_consistente_g_mas_h_no_decrece_a_lo_largo_de_una_ruta():
    """Corolario ESTATICO de la consistencia: g+h(hijo) >= g+h(padre). OJO: esto NO
    vuelve inutil el max() de RBFS; despues de un retroceso el f RESPALDADO del
    nodo supera a su g+h y el max se lo transmite a los hijos regenerados (ver
    test_rbfs_el_maximo_transmite_el_valor_respaldado)."""
    for etiqueta, D in _casos_h()[:8]:
        n = len(D)
        h, _ = make_heuristic(D, 0, "mst")
        # DFS exhaustivo sobre los nodos del modelo (n <= 7: pocos miles de nodos)
        pila = [make_root(n, 0)]
        while pila:
            nodo = pila.pop()
            nodo.f = nodo.g + h(nodo.last, nodo.remaining, nodo.closed)
            for c in successors(D, 0, nodo):
                assert c.g + h(c.last, c.remaining, c.closed) >= nodo.f, etiqueta
                pila.append(c)


# ---------------------------------------------------------------------------
# Modelo de estados
# ---------------------------------------------------------------------------
def test_sucesores_cierre_y_meta():
    D = MICRO
    raiz = make_root(5, 0)
    assert raiz.last == 0 and mask_cities(raiz.remaining) == [1, 2, 3, 4]
    assert not raiz.closed and raiz.g == 0
    assert len(successors(D, 0, raiz)) == 4
    # nodo sin pendientes pero no cerrado: NO es meta; un unico sucesor que cierra
    nodo = SearchNode(4, 0, 12, None, False)
    hijos = successors(D, 0, nodo)
    assert len(hijos) == 1 and hijos[0].closed and hijos[0].last == 0
    assert hijos[0].g == 12 + D[4][0]
    assert successors(D, 0, hijos[0]) == []          # el cerrado no tiene sucesores
    # la clave distingue closed y pendientes
    assert nodo.key() != hijos[0].key()


def test_ruta_invalida_se_rechaza_duplicado_y_omision():
    assert not is_valid_tour([0, 1, 1, 3, 4], 5, 0)      # duplicada
    assert not is_valid_tour([0, 1, 2, 3], 5, 0)         # omitida
    assert is_valid_tour([0, 1, 2, 3, 4], 5, 0)


# ---------------------------------------------------------------------------
# A* y RBFS contra enumeracion exhaustiva
# ---------------------------------------------------------------------------
def _matrices_aleatorias():
    for s in range(24):
        rng = random.Random(7000 + s)
        n = 4 + s % 5                                  # n = 4..8
        lo, hi = (0, 4) if s % 4 == 3 else (1, 30)     # cada 4a con muchos empates
        yield "rand{0}-n{1}".format(s, n), random_matrix(n, rng, lo, hi)


@pytest.mark.parametrize("etiqueta,D", list(_matrices_aleatorias()))
def test_astar_y_rbfs_igualan_la_enumeracion_en_matrices_aleatorias(etiqueta, D):
    inst = make_inst(D)
    optimo = brute_force(D)[0]
    for solver in (astar, rbfs):
        r = solver(inst)
        r.validate(inst)
        assert r.cost == optimo, (etiqueta, solver.__name__)
        assert r.cost == closed_cost(D, r.tour)         # oraculo independiente
        assert r.stop_reason == STOP_OPTIMAL and r.optimality_status == OPT_PROVEN


@pytest.mark.parametrize("nombre", REAL)
@pytest.mark.parametrize("k", [6, 8])
def test_astar_y_rbfs_igualan_la_enumeracion_en_subinstancias_reales(nombre, k):
    sub = load_by_name(nombre).subinstance(k)
    optimo = brute_force(sub.D)[0]
    for solver in (astar, rbfs):
        r = solver(sub)
        r.validate(sub)
        assert r.cost == optimo


def test_h0_y_mst_dan_el_mismo_costo_pero_mst_expande_menos():
    estrictos = 0
    for nombre in ("att48", "berlin52", "brazil58", "gr48"):
        sub = load_by_name(nombre).subinstance(9)
        a_mst = astar(sub, heuristic="mst")
        a_cero = astar(sub, heuristic="zero")
        assert a_mst.cost == a_cero.cost
        assert a_mst.algorithm == "A*+MST" and a_cero.algorithm == "A*(h=0)"
        assert a_cero.mst_calls == 0 and a_mst.mst_calls > 0
        assert a_mst.expanded <= a_cero.expanded
        estrictos += a_mst.expanded < a_cero.expanded
    assert estrictos >= 3
    for s in range(5):
        D = random_matrix(8, random.Random(900 + s))
        assert astar(make_inst(D), heuristic="mst").cost == \
            astar(make_inst(D), heuristic="zero").cost == brute_force(D)[0]


@pytest.mark.parametrize("nombre", ["att48", "gr17", "burma14", "berlin52"])
def test_invarianza_del_costo_al_cambiar_el_origen(nombre):
    sub = load_by_name(nombre).subinstance(7)
    optimo = brute_force(sub.D)[0]
    for origen in range(sub.n):
        for solver in (astar, rbfs):
            r = solver(sub, origin=origen)
            assert r.cost == optimo
            assert r.tour[0] == origen and is_valid_tour(r.tour, sub.n, origen)
            assert r.cost == tour_cost(sub.D, r.tour)


# ---------------------------------------------------------------------------
# Estados repetidos: fusionar por la ultima ciudad pierde el optimo
# ---------------------------------------------------------------------------
# Contraejemplo A (dos rutas parciales concretas, n = 5, origen 0):
#   X = 0,1,3  (pendientes {2,4})   Y = 0,1,2,3 (pendientes {4})   misma ultima ciudad 3.
#   g(X) = 2 < g(Y) = 3, asi que "conservar el de menor g por ciudad" se queda con X
#   y descarta Y... pero el optimo (5) solo se alcanza continuando desde Y.
CONTRA_A = [[0, 1, 10, 10, 1],
            [1, 0, 1, 1, 10],
            [10, 1, 0, 1, 10],
            [10, 1, 1, 0, 1],
            [1, 10, 10, 1, 0]]
# Contraejemplo B: matriz (semilla 0, n = 5, pesos 1..9) donde la variante con clave
# incorrecta NO ENCUENTRA NINGUNA RUTA (queda la frontera vacia) aunque existe una.
CONTRA_B = [[0, 7, 7, 1, 5],
            [7, 0, 9, 8, 7],
            [7, 9, 0, 5, 8],
            [1, 8, 5, 0, 6],
            [5, 7, 8, 6, 0]]


def _astar_clave_incorrecta(D, origin=0):
    """SOLO PARA ESTA PRUEBA: A* identico al real salvo la clave de estado, que
    aqui es (ultima ciudad, closed) y olvida el conjunto de pendientes."""
    n = len(D)
    h, _ = make_heuristic(D, origin, "mst")
    raiz = make_root(n, origin)
    raiz.h = h(raiz.last, raiz.remaining, False)
    raiz.f = raiz.h
    mejor = {(raiz.last, False): 0}
    cont = 0
    abierta = [(raiz.f, raiz.h, cont, raiz)]
    while abierta:
        _, _, _, nodo = heapq.heappop(abierta)
        if nodo.g > mejor[(nodo.last, nodo.closed)]:
            continue
        if nodo.closed:
            return nodo
        for hijo in successors(D, origin, nodo):
            k = (hijo.last, hijo.closed)          # <-- el error
            if hijo.g < mejor.get(k, float("inf")):
                mejor[k] = hijo.g
                hijo.h = h(hijo.last, hijo.remaining, hijo.closed)
                hijo.f = hijo.g + hijo.h
                cont += 1
                heapq.heappush(abierta, (hijo.f, hijo.h, cont, hijo))
    return None


def test_dos_rutas_parciales_misma_ciudad_final_no_se_pueden_fusionar():
    D = CONTRA_A
    X, Y = [0, 1, 3], [0, 1, 2, 3]
    gX, gY = D[0][1] + D[1][3], D[0][1] + D[1][2] + D[2][3]
    assert (gX, gY) == (2, 3) and X[-1] == Y[-1]
    # pendientes distintos -> continuaciones distintas
    assert set(range(5)) - set(X) == {2, 4} and set(range(5)) - set(Y) == {4}
    totalX = gX + best_completion_cost(D, 0, X)
    totalY = gY + best_completion_cost(D, 0, Y)
    assert totalX == 14 and totalY == 5              # X es mas barata hasta aqui, no al final
    assert totalY == brute_force(D)[0]               # el optimo SOLO sale de Y
    # y las claves correctas NO las fusionan
    nx = SearchNode(3, mask_of({2, 4}), gX, None, False)
    ny = SearchNode(3, mask_of({4}), gY, None, False)
    assert nx.key() != ny.key()


def test_a_star_con_clave_solo_por_ciudad_pierde_el_optimo_y_el_real_no():
    for D in (CONTRA_A, CONTRA_B):
        optimo = brute_force(D)[0]
        malo = _astar_clave_incorrecta(D)
        real = astar(make_inst(D))
        assert real.cost == optimo                     # el A* correcto sigue acertando
        assert malo is None or malo.g > optimo         # el incorrecto falla
    assert _astar_clave_incorrecta(CONTRA_B) is None   # ni siquiera halla una ruta


def test_devolver_el_primer_nodo_sin_pendientes_sin_cobrar_el_retorno_es_incorrecto():
    # pregunta 4 de la discusion: la meta es `closed`, no `remaining == 0`
    D = CONTRA_A
    inst = make_inst(D)
    r = astar(inst)
    # el costo correcto incluye el regreso: 5 = 1+1+1+1 + d(4,0)=1
    assert r.cost == tour_cost(D, r.tour) == 5
    sin_retorno = sum(D[r.tour[i]][r.tour[i + 1]] for i in range(len(r.tour) - 1))
    assert sin_retorno < r.cost


# ---------------------------------------------------------------------------
# A*: cota superior opcional, contadores, entradas obsoletas
# ---------------------------------------------------------------------------
def test_astar_con_cota_superior_certifica_o_agota():
    sub = load_by_name("berlin52").subinstance(9)
    base = astar(sub)
    justa = astar(sub, upper_bound=base.cost)          # cota = costo de una ruta real
    assert justa.cost == base.cost and justa.optimality_status == OPT_PROVEN
    assert justa.extras["pruned_by_upper_bound"] > 0
    assert justa.expanded <= base.expanded
    floja = astar(sub, upper_bound=base.cost * 10)
    assert floja.cost == base.cost
    # cota por debajo del optimo: no existe ruta <= cota; NO se afirma optimalidad
    baja = astar(sub, upper_bound=base.cost - 1)
    assert baja.tour is None and baja.optimality_status == OPT_NO_ROUTE
    assert baja.stop_reason == STOP_EXHAUSTED and "ub_certificate" in baja.extras


def test_astar_registra_contadores_y_entradas_obsoletas():
    sub = load_by_name("att48").subinstance(10)
    r = astar(sub)
    assert r.expanded > 0 and r.generated >= r.expanded and r.mst_calls > 0
    assert r.frontier_peak >= 1 and r.peak_memory > 0
    assert r.extras["obsolete_pops"] >= 0 and r.extras["pushes"] >= r.expanded
    # el A* reabre/mejora estados: bestG nunca guarda un g mayor al de la ruta final
    assert r.cost == tour_cost(sub.D, r.tour)


def test_astar_mejora_g_de_un_estado_ya_visto_y_descarta_la_entrada_vieja():
    # n = 4: llegar a {2,3} con last=1 por 0-2-3-1? Se verifica via contadores en
    # una matriz con pesos que violan la triangular (llegadas caras primero).
    hallado = False
    for s in range(200):
        D = random_matrix(7, random.Random(s))
        r = astar(make_inst(D), heuristic="zero")
        if r.extras["obsolete_pops"] > 0:
            hallado = True
            assert r.cost == brute_force(D)[0]
            break
    assert hallado


# ---------------------------------------------------------------------------
# RBFS: un hijo, empate, limite, agotamiento, interrupcion
# ---------------------------------------------------------------------------
def _run(inst, origin=0, audit=True):
    h, st = make_heuristic(inst.D, origin, "mst")
    b = Budget(max_seconds=10).start()

    class _M:
        def current_bytes(self):
            return 0
    run = _RBFSRun(inst.D, origin, h, b, _M(), audit, None)
    raiz = make_root(inst.n, origin)
    raiz.h = h(raiz.last, raiz.remaining, False)
    raiz.f = raiz.g + raiz.h
    return run, raiz


def test_rbfs_un_solo_hijo_n2():
    D = [[0, 5], [5, 0]]
    inst = make_inst(D)
    r = rbfs(inst)
    assert r.tour == [0, 1] and r.cost == 10 and r.optimality_status == OPT_PROVEN
    # raiz -> (1) -> cerrado: 2 expansiones, cada una con UN hijo (alternativa = inf)
    assert r.expanded == 2 and r.generated == 2 and r.regenerations == 0
    assert r.extras["max_depth"] == 2


def test_rbfs_n1_solo_el_origen():
    inst = make_inst([[0]])
    r = rbfs(inst)
    assert r.tour == [0] and r.cost == 0
    assert astar(inst).tour == [0]


def test_rbfs_empate_se_resuelve_por_h_y_luego_por_orden_de_generacion():
    log = []
    rbfs(make_inst(MICRO), log=log)
    # (profundidad, ciudad, f, limite): tras la raiz se baja a B (pos 1), no a E (pos 4),
    # aunque ambos tienen f = 14; B tiene h menor.
    assert log[0] == (0, 0, 13, _INF)
    assert log[1][:2] == (1, 1) and log[1][2] == 14
    # el limite que recibe B es la f de la alternativa (E = 14)
    assert log[1][3] == 14
    # empate total (misma f y misma h): gana la ciudad de menor posicion
    D = [[0, 2, 2, 2], [2, 0, 2, 2], [2, 2, 0, 2], [2, 2, 2, 0]]
    log2 = []
    r = rbfs(make_inst(D), log=log2)
    assert r.tour == [0, 1, 2, 3] and log2[1][1] == 1


def test_rbfs_limite_menor_que_la_mejor_f_devuelve_fracaso_con_f_respaldada():
    inst = make_inst(MICRO)
    run, raiz = _run(inst)
    estado, f_resp = run.rbfs(raiz, 13, 0)          # limite 13 < f de todos los hijos (14)
    assert estado == _FAILURE and f_resp == 14      # devuelve la mejor f (>limite) para el padre
    assert run.expanded == 1                        # solo se expandio la raiz


def test_rbfs_agotamiento_de_subarbol_respalda_el_valor_correcto():
    # con limite = optimo - 1 el subarbol entero se agota: FAILURE con f = optimo (14),
    # y no hay interrupcion (el presupuesto sigue vivo)
    inst = make_inst(MICRO)
    run, raiz = _run(inst)
    estado, f_resp = run.rbfs(raiz, 13, 0)
    assert (estado, f_resp) == (_FAILURE, 14) and run.stop is None
    # con limite = infinito se encuentra la meta y su f es el optimo
    run2, raiz2 = _run(inst)
    estado2, f2 = run2.rbfs(raiz2, _INF, 0)
    assert estado2 == _FOUND and f2 == 14 and route_of(run2.found) == [0, 1, 2, 3, 4]


def test_rbfs_retrocede_y_regenera_subarboles_en_un_caso_real():
    sub = load_by_name("att48").subinstance(8)
    r = rbfs(sub)
    assert r.cost == brute_force(sub.D)[0]
    assert r.regenerations > 0                       # RBFS recalcula subarboles
    assert r.extras["max_depth"] == sub.n            # n extensiones/cierre: profundidad n
    assert r.extras["calls"] >= r.expanded
    # memoria lineal en profundidad: nodos retenidos <= suma de hijos en la pila
    assert r.extras["retained_peak"] <= sub.n * sub.n
    # sin auditoria: cota inferior de las regeneraciones
    r2 = rbfs(sub, audit=False)
    assert r2.cost == r.cost and r2.expanded == r.expanded
    assert r2.regenerations <= r.regenerations
    assert r2.extras["regeneration_mode"] == "lower_bound_no_audit"
    assert r2.extras["audit_entries"] == 0 and r.extras["audit_entries"] > 0


def test_rbfs_el_maximo_transmite_el_valor_respaldado():
    # sin retrocesos ni regeneraciones el max nunca actua (f = g+h, y g+h no decrece)
    sin = rbfs(load_by_name("gr48").subinstance(6))
    assert sin.regenerations == 0 and sin.extras["raised_by_max"] == 0
    assert rbfs(make_inst(MICRO)).extras["raised_by_max"] == 0
    # con regeneraciones, los hijos regenerados heredan el f respaldado del padre
    con = rbfs(load_by_name("att48").subinstance(8))
    assert con.regenerations > 0 and con.extras["raised_by_max"] > 0


def test_rbfs_y_astar_explican_la_misma_cota_mst_calls_positivos():
    sub = load_by_name("gr17").subinstance(8)
    a, b = astar(sub), rbfs(sub)
    assert a.cost == b.cost
    assert a.mst_calls > 0 and b.mst_calls > a.mst_calls   # RBFS recomputa mas MST


# ---------------------------------------------------------------------------
# Presupuesto: interrupcion forzada (tabla 13: motivo correcto y ausencia explicita)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("solver", [astar, rbfs])
def test_interrupcion_por_expansiones(solver):
    inst = load_by_name("att48").subinstance(10)
    r = solver(inst, budget=Budget(max_expansions=7, max_seconds=60))
    assert r.stop_reason == STOP_EXPANSIONS and r.expanded == 7
    assert r.tour is None and r.cost is None and r.gap_percent is None
    assert r.optimality_status == OPT_NO_ROUTE
    r.validate(inst)                                   # contrato: ausencia explicita


@pytest.mark.parametrize("solver", [astar, rbfs])
def test_interrupcion_por_tiempo(solver):
    inst = load_by_name("berlin52")
    r = solver(inst, budget=Budget(max_seconds=0.0, max_expansions=10 ** 6))
    assert r.stop_reason == STOP_TIME and r.tour is None
    assert r.optimality_status == OPT_NO_ROUTE


@pytest.mark.parametrize("solver", [astar, rbfs])
def test_interrupcion_por_memoria(solver):
    inst = load_by_name("berlin52")
    r = solver(inst, budget=Budget(max_seconds=30, max_expansions=10 ** 6,
                                   max_memory_bytes=1000))
    # la memoria se revisa cada 256 expansiones: se detecta en la primera revision
    # posterior a superar 1000 bytes
    assert r.stop_reason == STOP_MEMORY and r.tour is None
    assert r.expanded <= 600


def test_presupuesto_por_defecto_son_los_limites_propuestos():
    from tsp.astar import default_budget
    b = default_budget()
    assert (b.max_seconds, b.max_expansions, b.max_memory_bytes) == (30, 100000, 256 * 1024 * 1024)


def test_un_resultado_interrumpido_nunca_se_llama_optimo():
    inst = load_by_name("gr48")
    for solver in (astar, rbfs):
        r = solver(inst, budget=Budget(max_expansions=50, max_seconds=30))
        assert r.optimality_status != OPT_PROVEN and r.stop_reason != STOP_OPTIMAL
        assert r.stop_reason != STOP_EXHAUSTED
