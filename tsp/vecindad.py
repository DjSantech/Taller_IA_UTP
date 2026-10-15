# -*- coding: utf-8 -*-
"""Vecindad comun de HC y SA: movimiento 2-opt exacto (seccion 9).

Una ruta es `route[0..n-1]` con el origen fijo en la POSICION 0. Un movimiento
se identifica por un par de posiciones (i, j) con 0 <= i < j <= n-1, j >= i+2 y
(i, j) != (0, n-1). Las aristas que se reemplazan son
    (a, b) = (route[i], route[i+1])      y      (c, d) = (route[j], route[(j+1) % n])
y el movimiento invierte las posiciones i+1..j (ambas incluidas). Como i+1 >= 1,
el origen nunca se mueve. Para n >= 4 hay n(n-3)/2 pares validos.

Por que se excluye (0, n-1): las aristas (route[0], route[1]) y (route[n-1], route[0])
comparten la ciudad route[0]; son ADYACENTES, y "invertir" 1..n-1 solo daria la
misma ruta recorrida al reves (mismo ciclo, mismo costo).

La formula del delta supone matriz SIMETRICA (el segmento invertido se recorre
al reves y su costo interno no cambia). Con asimetria habria que recalcularlo.
"""


def valid_pairs(n):
    """Enumera TODOS los pares validos (i, j) en orden lexicografico."""
    for i in range(n - 2):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            yield i, j


def count_valid_pairs(n):
    """n(n-3)/2 para n >= 4; 0 si no hay pares (n < 4)."""
    return n * (n - 3) // 2 if n >= 4 else 0


def is_valid_pair(n, i, j):
    return 0 <= i < j < n and j >= i + 2 and not (i == 0 and j == n - 1)


def random_valid_pair(n, rng):
    """Par valido UNIFORME entre los n(n-3)/2 pares.

    Se sortean dos posiciones distintas (cada par no ordenado es igual de
    probable) y se rechaza el par si no es valido. Muestrear i y luego j en
    [i+2, n-1] NO seria uniforme (los i pequenos tienen mas opciones de j)."""
    if n < 4:
        raise ValueError("2-opt exige n >= 4")
    while True:
        i = rng.randrange(n)
        j = rng.randrange(n)
        if i > j:
            i, j = j, i
        if j >= i + 2 and not (i == 0 and j == n - 1):
            return i, j


def two_opt_delta(D, route, i, j):
    """Delta = d(a,c) + d(b,d) - d(a,b) - d(c,d). O(1), sin copiar la ruta."""
    n = len(route)
    a = route[i]
    b = route[i + 1]
    c = route[j]
    d = route[(j + 1) % n]
    return D[a][c] + D[b][d] - D[a][b] - D[c][d]


def two_opt_apply(route, i, j):
    """Devuelve una COPIA con las posiciones i+1..j invertidas (no toca `route`)."""
    candidate = list(route)
    candidate[i + 1:j + 1] = candidate[i + 1:j + 1][::-1]
    return candidate


def two_opt_apply_inplace(route, i, j):
    """Misma inversion pero sobre la propia lista (la usan HC y SA para no
    copiar en cada movimiento aceptado)."""
    route[i + 1:j + 1] = route[i + 1:j + 1][::-1]
    return route


def swap_move(route, i, j):
    """Intercambio de DOS CIUDADES en las posiciones i y j (copia). Solo para
    contrastar con 2-opt (seccion 6.2, punto 5): reemplaza hasta CUATRO aristas
    (las que rodean a cada ciudad) y no es un 2-opt. No se usa en los solvers."""
    candidate = list(route)
    candidate[i], candidate[j] = candidate[j], candidate[i]
    return candidate


def swap_delta(D, route, i, j):
    """Delta del swap calculado por diferencia de costos de las aristas
    afectadas (maneja el caso de posiciones adyacentes y el cierre)."""
    n = len(route)
    afectadas = set()
    for p in (i, j):
        afectadas.add((p - 1) % n)       # arista (p-1, p)
        afectadas.add(p)                 # arista (p, p+1)
    antes = sum(D[route[k]][route[(k + 1) % n]] for k in afectadas)
    nueva = swap_move(route, i, j)
    despues = sum(D[nueva[k]][nueva[(k + 1) % n]] for k in afectadas)
    return despues - antes
