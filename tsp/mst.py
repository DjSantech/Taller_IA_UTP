# -*- coding: utf-8 -*-
"""Arbol de expansion minima (MST) y heuristica de A*/RBFS (secciones 6, 6.1).

Por que un MST: es una RELAJACION del TSP. Quita la exigencia de grado dos y de
ciclo unico, y por eso nunca cuesta mas que el mejor camino que recorre los mismos
nodos. Se calcula en O(|U|^2) con matriz densa (Prim con "mejor costo de conexion"
por ciudad), no en O(|U|^3) como el Prim conceptual que reexplora todas las
aristas de corte en cada paso.

Las ciudades son POSICIONES 0..n-1 de la matriz D (ver tsp.datos).
"""


def mst_cost(D, nodes):
    """Costo del MST del subgrafo inducido por `nodes` (iterable de posiciones
    DISTINTAS). |U| = 0 o 1 -> 0 (definicion del enunciado).

    Prim denso: `best[j]` es el menor peso de conectar la ciudad pendiente j con
    lo ya conectado; al anadir una ciudad solo se actualiza esa lista (O(|U|))
    y hay |U|-1 anadidos, de ahi el O(|U|^2)."""
    rest = list(nodes)
    m = len(rest)
    if m <= 1:
        return 0
    first = rest.pop()
    row = D[first]
    best = [row[v] for v in rest]
    total = 0
    while rest:
        # indice de la ciudad mas barata de conectar (primer minimo: determinista)
        k = 0
        bk = best[0]
        for j in range(1, len(best)):
            if best[j] < bk:
                bk = best[j]
                k = j
        total += bk
        v = rest[k]
        # eliminacion O(1) intercambiando con el ultimo
        rest[k] = rest[-1]
        best[k] = best[-1]
        rest.pop()
        best.pop()
        row = D[v]
        for j in range(len(rest)):
            w = row[rest[j]]
            if w < best[j]:
                best[j] = w
    return total


def mst_edges(D, nodes):
    """Aristas (a, b, peso) de un MST, con el mismo Prim pero recordando de que
    ciudad viene cada mejor conexion. Existe para VALIDAR que es un arbol
    (|U|-1 aristas, conexo, sin ciclos) y que su peso coincide con `mst_cost`."""
    rest = list(nodes)
    if len(rest) <= 1:
        return []
    first = rest.pop()
    best = [D[first][v] for v in rest]
    src = [first] * len(rest)
    edges = []
    while rest:
        k = 0
        for j in range(1, len(best)):
            if best[j] < best[k]:
                k = j
        v = rest[k]
        edges.append((src[k], v, best[k]))
        rest[k] = rest[-1]
        best[k] = best[-1]
        src[k] = src[-1]
        rest.pop()
        best.pop()
        src.pop()
        for j in range(len(rest)):
            w = D[v][rest[j]]
            if w < best[j]:
                best[j] = w
                src[j] = v
    return edges


def heuristic_mst(D, origin, last, remaining, closed):
    """h(v, U) de la seccion 6.

        0                                   si el ciclo esta cerrado
        d(v, s)                             si U vacio y falta cerrar
        MST(U) + min_u d(v,u) + min_u d(u,s) en otro caso

    `remaining` es un iterable de posiciones pendientes (U). Con |U| = 1 la
    formula es EXACTA: d(v,u) + 0 + d(u,s). En la raiz las dos conexiones
    minimas pueden elegir la misma ciudad: sigue siendo una relajacion valida,
    solo menos ajustada."""
    if closed:
        return 0
    rem = list(remaining)
    if not rem:
        return D[last][origin]
    row_last = D[last]
    return (mst_cost(D, rem)
            + min(row_last[u] for u in rem)
            + min(D[u][origin] for u in rem))


def heuristic_zero(D, origin, last, remaining, closed):
    """h = 0: convierte A* en costo uniforme. Sirve de linea base para medir
    cuanto ahorra la cota MST. (Mismos argumentos que heuristic_mst.)"""
    return 0
