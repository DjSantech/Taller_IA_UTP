# -*- coding: utf-8 -*-
"""RBFS (seccion 8): mejor-primero recursivo de memoria lineal en la profundidad.

Reutiliza EXACTAMENTE el modelo de estados y la cota MST de tsp.astar
(`SearchNode`, `successors`, `make_heuristic`, `route_of`): asi la comparacion
A* vs RBFS mide la estrategia de busqueda y no una cota distinta.

Version de ARBOL: no hay conjunto de visitados ni `bestG`. No hace falta para
evitar ciclos (cada extension quita una pendiente y el ultimo paso cierra), pero
significa que dos caminos distintos al mismo estado se exploran por separado.
"""
from tsp.astar import (MEM_CHECK_EVERY, SearchNode, _NullMeter, _algorithm_name,
                       default_budget, make_heuristic, make_root, mask_cities,
                       route_of, successors)
from tsp.modelo import (MemoryMeter, RunResult, tour_cost, STOP_OPTIMAL,
                        STOP_EXHAUSTED, OPT_PROVEN, OPT_NO_ROUTE)

_FOUND = "FOUND"
_FAILURE = "FAILURE"
_INTERRUPTED = "INTERRUPTED"
_INF = float("inf")


class _RBFSRun:
    """Estado de UNA ejecucion: contadores de la seccion 8.1 y presupuesto.

    Definiciones de instrumentacion (declaradas en el informe):
      expanded     veces que se llama a `successors` para un nodo no cerrado.
      calls        llamadas a la funcion recursiva RBFS (incluye nodos cerrados).
      max_depth    profundidad maxima alcanzada (raiz = 0; el nodo cerrado = n).
      retained     registros de nodo vivos a la vez: la raiz mas las listas de
                   hijos de cada marco de la pila. `retained_peak` es su maximo.
      regenerations
         audit=True  (EXACTO): expansiones de un nodo que ya se habia expandido
                     antes. Un nodo se identifica por su CAMINO desde la raiz
                     (no por su estado: dos caminos distintos al mismo estado
                     NO son regeneracion, son ramas distintas del arbol). El
                     registro de auditoria es un set de hashes de 64 bits de esos
                     caminos: cuesta memoria O(nodos distintos expandidos), que NO
                     es parte del algoritmo; por eso se puede apagar (audit=False)
                     y comparar el pico de memoria con y sin el.
         audit=False (COTA INFERIOR): solo se cuenta cuando se vuelve a expandir
                     el MISMO registro que sigue vivo en la lista de hijos de su
                     padre (se detecta con un set local por marco, O(b)). No ve las
                     regeneraciones de nodos nuevos que estaban dentro de un
                     subarbol ya descartado.
    """

    def __init__(self, D, origin, h_fn, budget, meter, audit, log):
        self.D = D
        self.origin = origin
        self.h = h_fn
        self.budget = budget
        self.meter = meter
        self.audit = audit
        self.log = log
        self.expanded = self.generated = self.calls = 0
        self.max_depth = 0
        self.retained = 1                    # la raiz
        self.retained_peak = 1
        self.regenerations = 0
        self.reexpanded_same_record = 0
        self.raised_by_max = 0               # hijos cuyo f subio por el max()
        self.audit_set = set()
        self.found = None
        self.stop = None
        self._mem = 0
        self._next_mem_check = 0

    def _check(self):
        if self.expanded >= self._next_mem_check:
            self._mem = self.meter.current_bytes()
            self._next_mem_check = self.expanded + MEM_CHECK_EVERY
        return self.budget.check(expansions=self.expanded, memory_bytes=self._mem)

    @staticmethod
    def _path_hash(node):
        cities = []
        while node is not None:
            cities.append(node.last)
            node = node.parent
        return hash(tuple(cities))

    def rbfs(self, node, limit, depth):
        self.calls += 1
        if depth > self.max_depth:
            self.max_depth = depth
        # Presupuesto global: si vence, se PROPAGA INTERRUPTED hacia la raiz.
        stop = self._check()
        if stop is not None:
            self.stop = stop
            return _INTERRUPTED, limit
        if self.log is not None:
            self.log.append((depth, node.last, node.f, limit))
        if node.closed:
            self.found = node
            return _FOUND, node.f

        if self.audit:
            ph = self._path_hash(node)
            if ph in self.audit_set:
                self.regenerations += 1
            else:
                self.audit_set.add(ph)
        self.expanded += 1
        children = successors(self.D, self.origin, node)
        if not children:
            return _FAILURE, _INF
        self.generated += len(children)
        self.retained += len(children)
        if self.retained > self.retained_peak:
            self.retained_peak = self.retained
        try:
            # child.f = max(g + h, node.f): el valor respaldado del padre es una
            # cota inferior valida para todo su subarbol; el maximo evita que f
            # "baje" por una h inconsistente y rompa el orden de exploracion.
            for c in children:
                c.h = self.h(c.last, c.remaining, c.closed)
                c.f = max(c.g + c.h, node.f)
                if c.f > c.g + c.h:
                    self.raised_by_max += 1
            seen_here = set()
            while True:
                # sort() de Python es ESTABLE: a igual (f, h) queda el generado
                # primero (ciudad de menor posicion). Menor h = mas avanzado.
                children.sort(key=_order_key)
                best = children[0]
                if best.f == _INF or best.f > limit:
                    return _FAILURE, best.f
                alternative = children[1].f if len(children) > 1 else _INF
                if id(best) in seen_here:
                    self.reexpanded_same_record += 1
                    if not self.audit:
                        self.regenerations += 1
                seen_here.add(id(best))
                status, backed = self.rbfs(best, min(limit, alternative), depth + 1)
                if status == _INTERRUPTED:
                    return _INTERRUPTED, limit
                best.f = backed
                if status == _FOUND:
                    return _FOUND, best.f
        finally:
            self.retained -= len(children)


def _order_key(c):
    return (c.f, c.h)


def rbfs(inst, origin=0, budget=None, heuristic="mst", audit=True,
         measure_memory=True, log=None):
    """RBFS exacto sobre rutas parciales (mismo modelo y cota que `astar`).

    Interrupcion por presupuesto: tour = None, cost = None, optimality_status =
    NO_ROUTE y stop_reason = motivo del Budget. NO es un fracaso definitivo ni
    se usa ningun f respaldado como certificado de brecha.
    `audit`: ver _RBFSRun (registro de regeneraciones exacto, con costo de
    memoria propio). `log`: lista opcional con (profundidad, ciudad, f, limite)
    por llamada, para trazas didacticas."""
    if budget is None:
        budget = default_budget()
    D = inst.D
    h_fn, hstats = make_heuristic(D, origin, heuristic)
    budget.start()
    meter_cls = MemoryMeter if measure_memory else _NullMeter
    with meter_cls() as meter:
        run = _RBFSRun(D, origin, h_fn, budget, meter, audit, log)
        root = make_root(inst.n, origin)
        root.h = h_fn(root.last, root.remaining, root.closed)
        root.f = root.g + root.h
        status, _ = run.rbfs(root, _INF, 0)
        audit_entries = len(run.audit_set)

    res = RunResult(instance=inst.name, algorithm=_algorithm_name("RBFS", heuristic),
                    parameters={"origin": origin, "heuristic": heuristic,
                                "audit": audit, "mem_check_every": MEM_CHECK_EVERY,
                                "measure_memory": measure_memory})
    res.elapsed_seconds = budget.elapsed()
    res.peak_memory = meter.peak_bytes
    res.expanded = run.expanded
    res.generated = run.generated
    res.mst_calls = hstats["mst_calls"]
    res.regenerations = run.regenerations
    res.extras = {"calls": run.calls, "max_depth": run.max_depth,
                  "retained_peak": run.retained_peak,
                  "regeneration_mode": "exact_audit" if audit else "lower_bound_no_audit",
                  "reexpanded_same_record": run.reexpanded_same_record,
                  "raised_by_max": run.raised_by_max,
                  "audit_entries": audit_entries}
    if status == _FOUND:
        res.tour = route_of(run.found)
        res.cost = run.found.g
        assert res.cost == tour_cost(D, res.tour)
        res.stop_reason = STOP_OPTIMAL
        res.optimality_status = OPT_PROVEN
    else:
        res.tour = None
        res.cost = None
        res.optimality_status = OPT_NO_ROUTE
        # INTERRUPTED -> motivo del Budget; FAILURE en la raiz (no deberia pasar)
        res.stop_reason = run.stop if status == _INTERRUPTED else STOP_EXHAUSTED
    return res
