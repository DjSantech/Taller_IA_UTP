"""Oraculo exhaustivo SOLO PARA PRUEBAS (seccion 13): enumera todas las rutas.
Escrito aparte de los solvers para que un error compartido no se cancele."""
import itertools


def closed_cost(D, route):
    """Costo del ciclo cerrado, recalculado aqui (independiente de tsp.modelo)."""
    return sum(D[route[i]][route[(i + 1) % len(route)]] for i in range(len(route)))


def all_tours(n, origin=0):
    resto = [c for c in range(n) if c != origin]
    for p in itertools.permutations(resto):
        yield [origin] + list(p)


def brute_force(D, origin=0):
    """(costo_optimo, una_ruta_optima, numero_de_rutas_optimas). Solo n <= 10."""
    n = len(D)
    mejor, ruta, cuenta = None, None, 0
    for r in all_tours(n, origin):
        c = closed_cost(D, r)
        if mejor is None or c < mejor:
            mejor, ruta, cuenta = c, r, 1
        elif c == mejor:
            cuenta += 1
    return mejor, ruta, cuenta


def best_completion_cost(D, origin, prefix):
    """Costo restante OPTIMO desde el ultimo nodo del prefijo, visitando los
    pendientes y volviendo al origen (sirve para validar la admisibilidad de h)."""
    n = len(D)
    last = prefix[-1]
    pend = [c for c in range(n) if c not in prefix]
    if not pend:
        return D[last][origin]
    mejor = None
    for p in itertools.permutations(pend):
        ruta = [last] + list(p) + [origin]
        c = sum(D[ruta[i]][ruta[i + 1]] for i in range(len(ruta) - 1))
        if mejor is None or c < mejor:
            mejor = c
    return mejor
