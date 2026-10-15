# -*- coding: utf-8 -*-
"""Modelo comun (seccion 4): ruta, costo, presupuesto, aleatoriedad y contrato
de salida. NINGUN algoritmo duplica la logica de costo: todos usan `tour_cost`.

Una ruta es una lista/tuple de POSICIONES con el origen en la posicion 0 de la
lista; es una permutacion de 0..n-1 y el ciclo se cierra implicitamente:
    C(pi) = sum_{i=0}^{n-2} D[pi_i][pi_{i+1}] + D[pi_{n-1}][pi_0]
"""
import random
import time
import tracemalloc
from dataclasses import dataclass, field

# --- Motivos de parada (stop_reason) ------------------------------------------
STOP_OPTIMAL = "OPTIMAL"                # A*/RBFS: meta alcanzada con cota admisible
STOP_EXHAUSTED = "EXHAUSTED"            # espacio agotado sin meta (no deberia ocurrir)
STOP_TIME = "TIME_LIMIT"                # presupuesto de tiempo
STOP_EVALS = "EVAL_LIMIT"               # presupuesto de evaluaciones de candidatos
STOP_EXPANSIONS = "EXPANSION_LIMIT"     # presupuesto de expansiones (A*/RBFS)
STOP_MEMORY = "MEMORY_LIMIT"            # presupuesto de memoria incremental
STOP_LOCAL_OPT = "LOCAL_OPTIMUM"        # HC: ningun vecino mejora estrictamente
STOP_COOLED = "COOLED"                  # SA: T <= Tmin
STOP_GENERATIONS = "GENERATIONS_DONE"   # GA: se completaron las generaciones previstas

# --- Estado de optimalidad (optimality_status) ---------------------------------
OPT_PROVEN = "PROVEN_OPTIMAL"           # solo A*/RBFS al terminar sin interrupcion
OPT_NOT_PROVEN = "NOT_PROVEN"           # ruta valida sin certificado
OPT_NO_ROUTE = "NO_ROUTE"               # no hay ruta (exactos interrumpidos)


def tour_cost(D, route):
    """Costo del ciclo CERRADO. Unica implementacion de costo del proyecto."""
    n = len(route)
    total = 0
    for k in range(n - 1):
        total += D[route[k]][route[k + 1]]
    return total + D[route[n - 1]][route[0]]


def tour_problems(route, n, origin=None):
    """Lista de motivos por los que `route` NO es una ruta valida ([] si lo es)."""
    problemas = []
    if len(route) != n:
        problemas.append("longitud {0} distinta de n={1}".format(len(route), n))
    vistos = set()
    for c in route:
        if not isinstance(c, int) or not 0 <= c < n:
            problemas.append("ciudad fuera de rango: {0}".format(c))
        elif c in vistos:
            problemas.append("ciudad duplicada: {0}".format(c))
        vistos.add(c)
    faltan = set(range(n)) - vistos
    if faltan:
        problemas.append("ciudades omitidas: {0}".format(sorted(faltan)))
    if origin is not None and route and route[0] != origin:
        problemas.append("no empieza en el origen {0}".format(origin))
    return problemas


def is_valid_tour(route, n, origin=None):
    return not tour_problems(route, n, origin)


def gap_percent(cost, optimum):
    """gap(%) = 100 (C - C*)/C*. None si no hay ruta o no hay referencia."""
    if cost is None or optimum is None:
        return None
    return 100.0 * (cost - optimum) / optimum


def random_tour(n, rng, origin=0):
    """Permutacion aleatoria con el origen fijo en la posicion 0."""
    resto = [c for c in range(n) if c != origin]
    rng.shuffle(resto)
    return [origin] + resto


def make_rngs(seed):
    """Generadores INDEPENDIENTES: uno para la ruta inicial y uno para las
    decisiones del algoritmo. Se siembran con enteros (no con cadenas ni hash)
    para que sean reproducibles entre procesos y versiones."""
    return random.Random(1000003 * seed + 1), random.Random(1000003 * seed + 2)


class Budget:
    """Presupuesto de ejecucion. Se consulta con `check(...)`, que devuelve el
    motivo de parada si algun limite se agoto y None si se puede seguir.
    El tiempo se mide con perf_counter desde `start()`."""

    def __init__(self, max_evals=None, max_seconds=None, max_expansions=None,
                 max_memory_bytes=None):
        self.max_evals = max_evals
        self.max_seconds = max_seconds
        self.max_expansions = max_expansions
        self.max_memory_bytes = max_memory_bytes
        self.t0 = None

    def start(self):
        self.t0 = time.perf_counter()
        return self

    def elapsed(self):
        return 0.0 if self.t0 is None else time.perf_counter() - self.t0

    def check(self, evals=0, expansions=0, memory_bytes=0):
        if self.max_evals is not None and evals >= self.max_evals:
            return STOP_EVALS
        if self.max_expansions is not None and expansions >= self.max_expansions:
            return STOP_EXPANSIONS
        if self.max_memory_bytes is not None and memory_bytes >= self.max_memory_bytes:
            return STOP_MEMORY
        if self.max_seconds is not None and self.elapsed() >= self.max_seconds:
            return STOP_TIME
        return None


class MemoryMeter:
    """Memoria INCREMENTAL atribuible al solver, medida con tracemalloc: solo
    cuenta asignaciones de Python (no memoria del proceso completo ni de C).
    Uso:  with MemoryMeter() as m: ...;  m.peak_bytes  y  m.current_bytes()."""

    def __enter__(self):
        self._ya_activo = tracemalloc.is_tracing()
        if not self._ya_activo:
            tracemalloc.start()
        self._base, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        self.peak_bytes = 0
        return self

    def current_bytes(self):
        return max(0, tracemalloc.get_traced_memory()[0] - self._base)

    def __exit__(self, *exc):
        self.peak_bytes = max(0, tracemalloc.get_traced_memory()[1] - self._base)
        if not self._ya_activo:
            tracemalloc.stop()
        return False


@dataclass
class RunResult:
    """Contrato de salida (seccion 4 y tabla 15). Campos no aplicables: None/0."""
    instance: str
    algorithm: str
    seed: int = None
    parameters: dict = field(default_factory=dict)
    subset: tuple = None                # identificadores de la subinstancia
    tour: list = None                   # None = ausencia explicita de ruta
    cost: int = None
    gap_percent: float = None
    elapsed_seconds: float = 0.0
    peak_memory: int = 0                # bytes, tracemalloc (solo Python)
    candidate_evaluations: int = 0      # HC, SA, GA
    expanded: int = 0                   # A*, RBFS
    generated: int = 0
    mst_calls: int = 0
    frontier_peak: int = 0              # A*: maximo de |open|
    regenerations: int = 0              # RBFS: subarboles recalculados
    stop_reason: str = ""
    optimality_status: str = OPT_NOT_PROVEN
    fallback_route: bool = False        # True si la ruta es de respaldo, no descubierta
    trace: list = field(default_factory=list)   # [(evals, best_cost, seconds), ...]
    extras: dict = field(default_factory=dict)  # curvas especificas (SA, GA, RBFS...)

    def validate(self, inst, origin=0):
        """Comprueba el contrato: ruta valida y costo coherente con `tour_cost`."""
        if self.tour is None:
            assert self.cost is None and self.gap_percent is None
            assert self.optimality_status == OPT_NO_ROUTE
            return True
        assert is_valid_tour(self.tour, inst.n, origin), tour_problems(self.tour, inst.n, origin)
        assert self.cost == tour_cost(inst.D, self.tour)
        return True

    def row(self):
        """Fila plana para CSV (la ruta se guarda como texto)."""
        d = {k: v for k, v in self.__dict__.items() if k not in ("trace", "extras")}
        d["tour"] = None if self.tour is None else " ".join(map(str, self.tour))
        d["subset"] = None if self.subset is None else " ".join(map(str, self.subset))
        d["parameters"] = repr(sorted(self.parameters.items()))
        return d
