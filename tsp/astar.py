# -*- coding: utf-8 -*-
"""Modelo de rutas parciales (seccion 5) y A* con MST (seccion 7).

Este modulo tambien define el modelo y la cota que RBFS reutiliza (tsp.rbfs):
`SearchNode`, `make_root`, `successors`, `make_heuristic`, `route_of`.

Decision de representacion del estado: el conjunto de pendientes es una MASCARA
DE BITS (int) sobre las posiciones 0..n-1. Razones: (1) es inmutable y hashable,
asi que la clave `(last, remaining, closed)` es una tupla pequena; (2) quitar
una ciudad es `mask & ~(1 << v)`, O(1); (3) un `frozenset` de 50 ciudades pesa
cientos de bytes por nodo, un int de 58 bits pesa ~36: importa mucho al medir
la memoria de A* y RBFS. El bit del origen nunca se enciende (el origen es fijo).
"""
import heapq

from tsp.modelo import (Budget, MemoryMeter, RunResult, tour_cost,
                        STOP_OPTIMAL, STOP_EXHAUSTED, OPT_PROVEN, OPT_NO_ROUTE)
from tsp.mst import heuristic_mst

# Cada cuantas expansiones se mide la memoria incremental (tracemalloc). Medirla
# en cada expansion costaria mas que el propio algoritmo; el tiempo y las
# expansiones SI se revisan en cada iteracion. Consecuencia declarada: la memoria
# puede rebasar el limite hasta ~256 expansiones antes de detectarse.
MEM_CHECK_EVERY = 256


def default_budget():
    """Limites propuestos en la seccion 14: 30 s, 100000 expansiones, 256 MiB."""
    return Budget(max_seconds=30, max_expansions=100000,
                  max_memory_bytes=256 * 1024 * 1024)


# ---------------------------------------------------------------------------
# Modelo de estados (seccion 5)
# ---------------------------------------------------------------------------
class SearchNode:
    """Ruta parcial. `g` mide SOLO aristas ya recorridas (incluye el regreso al
    origen en el nodo cerrado). `parent` permite reconstruir la ruta sin copiar
    listas (registros inmutables encadenados). `f` y `h` los fija el solver."""
    __slots__ = ("last", "remaining", "g", "f", "h", "parent", "closed")

    def __init__(self, last, remaining, g, parent, closed):
        self.last = last
        self.remaining = remaining      # mascara de bits de ciudades pendientes
        self.g = g
        self.f = 0
        self.h = 0
        self.parent = parent
        self.closed = closed

    def key(self):
        """Clave de estado (last, remaining, closed) con el mismo origen fijo.
        Dos nodos con la misma clave tienen exactamente las mismas continuaciones,
        asi que basta conservar el de menor g."""
        return (self.last, self.remaining, self.closed)


def mask_cities(mask):
    """Posiciones de los bits encendidos de `mask`, en orden ascendente."""
    out = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


def make_root(n, origin=0):
    """Raiz: last = s, remaining = V - {s}, g = 0, closed = False."""
    full = ((1 << n) - 1) & ~(1 << origin)
    return SearchNode(origin, full, 0, None, False)


def successors(D, origin, node):
    """Sucesores de la seccion 5. Orden: ciudades por posicion ascendente
    (parte del desempate determinista). Sin pendientes: UN solo sucesor que
    regresa al origen y marca closed = True."""
    if node.closed:
        return []
    if node.remaining == 0:
        return [SearchNode(origin, 0, node.g + D[node.last][origin], node, True)]
    row = D[node.last]
    out = []
    mask = node.remaining
    while mask:
        low = mask & -mask
        v = low.bit_length() - 1
        mask ^= low
        out.append(SearchNode(v, node.remaining ^ low, node.g + row[v], node, False))
    return out


def route_of(node):
    """Ruta (posiciones, origen primero) de un nodo, siguiendo `parent`. El nodo
    cerrado repite el origen, que no se incluye (el ciclo se cierra implicito)."""
    cities = []
    while node is not None:
        if not node.closed:
            cities.append(node.last)
        node = node.parent
    cities.reverse()
    return cities


def make_heuristic(D, origin, name="mst"):
    """Devuelve (h, stats). h(last, remaining_mask, closed) -> int.
    stats['mst_calls'] cuenta cada calculo de MST (caso general de la formula).
    Se usa la MISMA funcion en A* y RBFS, asi la cota es identica."""
    stats = {"mst_calls": 0}
    if name == "zero":
        def h0(last, remaining, closed):
            return 0
        return h0, stats
    if name != "mst":
        raise ValueError("heuristica desconocida: {0!r}".format(name))

    def h(last, remaining, closed):
        if closed:
            return 0
        if remaining == 0:
            return D[last][origin]
        stats["mst_calls"] += 1
        return heuristic_mst(D, origin, last, mask_cities(remaining), False)
    return h, stats


def _algorithm_name(prefix, heuristic):
    if prefix == "A*":
        return "A*+MST" if heuristic == "mst" else "A*(h=0)"
    return "RBFS+MST" if heuristic == "mst" else "RBFS(h=0)"


class _NullMeter:
    """Sustituye a MemoryMeter cuando measure_memory=False (solo para medir la
    sobrecarga de tracemalloc; el limite de memoria deja de aplicarse)."""
    peak_bytes = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def current_bytes(self):
        return 0


# ---------------------------------------------------------------------------
# A* (seccion 7)
# ---------------------------------------------------------------------------
def astar(inst, origin=0, budget=None, heuristic="mst", upper_bound=None,
          measure_memory=True, log=None):
    """A* exacto sobre rutas parciales.

    Desempate DETERMINISTA de la cola: (f, h, contador). A igual f se prefiere
    menor h (= mayor g, nodo mas avanzado, y los nodos cerrados con h = 0 salen
    antes) y, si aun hay empate, el generado primero (FIFO). El contador evita
    ademas que heapq compare nodos. No se usa la profundidad como dominancia.

    Metas = nodos cerrados; la meta se comprueba al SACAR el nodo (no al
    generarlo), que es lo que da la optimalidad.

    `upper_bound` (opcional): costo de una ruta factible conocida. Se podan los
    hijos con g + h > upper_bound. Es seguro: h es admisible, asi que toda
    continuacion de un nodo podado cuesta mas que la cota. Certificacion:
      - si A* saca un nodo cerrado de costo c <= upper_bound, ningun nodo
        podado (todos con f > upper_bound >= c) ni abierto (f >= c) puede dar
        algo mejor: c es OPTIMO, sin importar si la cota era justa;
      - si la frontera se agota, NO existe ruta de costo <= upper_bound:
        stop_reason = EXHAUSTED y NO se afirma optimalidad (la ruta de la cota
        la aporta quien la dio, no A*); queda en extras['ub_certificate'].
    `log`: lista opcional; recibe (g, h, f, last, remaining_cities) por cada
    expansion (para trazas didacticas)."""
    if budget is None:
        budget = default_budget()
    D = inst.D
    n = inst.n
    h_fn, hstats = make_heuristic(D, origin, heuristic)
    budget.start()
    meter_cls = MemoryMeter if measure_memory else _NullMeter

    expanded = generated = obsolete = pruned_ub = discarded = pushes = 0
    frontier_peak = 0
    found = None
    stop = None
    counter = 0

    with meter_cls() as meter:
        root = make_root(n, origin)
        root.h = h_fn(root.last, root.remaining, root.closed)
        root.f = root.g + root.h
        best_g = {root.key(): 0}
        open_heap = []
        if upper_bound is None or root.f <= upper_bound:
            heapq.heappush(open_heap, (root.f, root.h, counter, root))
            counter += 1
            pushes += 1
            frontier_peak = 1
        else:
            pruned_ub += 1

        mem = 0
        next_mem_check = 0
        while open_heap:
            if expanded >= next_mem_check:
                mem = meter.current_bytes()
                next_mem_check = expanded + MEM_CHECK_EVERY
            stop = budget.check(expansions=expanded, memory_bytes=mem)
            if stop is not None:
                break
            _, _, _, node = heapq.heappop(open_heap)
            if node.g > best_g[node.key()]:
                obsolete += 1                   # entrada desactualizada
                continue
            if node.closed:
                found = node
                break
            expanded += 1
            if log is not None:
                log.append((node.g, node.h, node.f, node.last,
                            mask_cities(node.remaining)))
            for child in successors(D, origin, node):
                generated += 1
                key = child.key()
                if child.g < best_g.get(key, float("inf")):
                    child.h = h_fn(child.last, child.remaining, child.closed)
                    child.f = child.g + child.h
                    if upper_bound is not None and child.f > upper_bound:
                        pruned_ub += 1
                        continue
                    best_g[key] = child.g
                    heapq.heappush(open_heap, (child.f, child.h, counter, child))
                    counter += 1
                    pushes += 1
                else:
                    discarded += 1
            if len(open_heap) > frontier_peak:
                frontier_peak = len(open_heap)
        else:
            stop = STOP_EXHAUSTED if found is None else stop
        if found is not None:
            stop = STOP_OPTIMAL

    res = RunResult(instance=inst.name, algorithm=_algorithm_name("A*", heuristic),
                    parameters={"origin": origin, "heuristic": heuristic,
                                "upper_bound": upper_bound,
                                "mem_check_every": MEM_CHECK_EVERY,
                                "measure_memory": measure_memory})
    res.elapsed_seconds = budget.elapsed()
    res.peak_memory = meter.peak_bytes
    res.expanded = expanded
    res.generated = generated
    res.mst_calls = hstats["mst_calls"]
    res.frontier_peak = frontier_peak
    res.stop_reason = stop
    res.extras = {"obsolete_pops": obsolete, "pushes": pushes,
                  "discarded_by_bestG": discarded, "pruned_by_upper_bound": pruned_ub,
                  "states_seen": len(best_g)}
    if found is not None:
        res.tour = route_of(found)
        res.cost = found.g
        assert res.cost == tour_cost(D, res.tour)   # el g acumulado coincide con tour_cost
        res.optimality_status = OPT_PROVEN
    else:
        res.tour = None
        res.cost = None
        res.optimality_status = OPT_NO_ROUTE
        if stop == STOP_EXHAUSTED and upper_bound is not None:
            res.extras["ub_certificate"] = ("no existe ruta de costo <= {0}"
                                            .format(upper_bound))
    return res
