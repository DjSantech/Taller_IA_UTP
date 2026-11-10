"""Seccion 7, apartados A y B: microproblema de la torre (AIMA caps. 3 y 3.5).

REGLAS SIMPLIFICADAS EXPLICITAS (no son posiciones legales de ajedrez):
tablero 8x8, una sola torre blanca, sin reyes, sin rival y sin turnos. Opcionalmente
hay casillas bloqueadas (obstaculos fijos que la torre no puede ocupar ni saltar).
No se usa python-chess: el movimiento se programa desde cero.

Formulacion AIMA
----------------
* Estado: la casilla de la torre, tupla de enteros (columna, fila) en 0..7
  (a1 = (0, 0), h8 = (7, 7)). Inmutable y hashable, como (fila, columna) en el
  Taller 1 (D-08 de aquel taller).
* Acciones: ("N"|"E"|"S"|"O", k): avanzar k >= 1 casillas en una direccion, sin
  salir del tablero ni atravesar u ocupar un obstaculo. ORDEN FIJO: direcciones
  N, E, S, O (el mismo del Taller 1) y, dentro de cada direccion, k creciente
  (o decreciente si `long_moves_first=True`). El orden NO cambia el costo optimo
  de UCS/A*, pero SI la ruta que devuelve DFS (y los desempates).
* Modelo de transicion: RESULT(s, (d, k)) = s + k * delta(d).
* Prueba objetivo: la torre esta en la casilla destino (h8 por omision).
* Costo de paso, dos modelos:
    - "unit":     c(s, a, s') = 1           (numero de movimientos)
    - "distance": c(s, a, s') = k           (casillas recorridas)
  LONGITUD de una ruta = numero de movimientos; COSTO = suma de c segun el modelo.
  Con costo unitario ambas coinciden; con costo por distancia no.

Heuristicas (seccion 7.B)
-------------------------
* `h_rook_lines` (la de la consigna): 0 en el destino, 1 si comparte fila o
  columna, 2 en otro caso. Admisible y consistente para costo UNITARIO (cota
  inferior del numero de movimientos de torre, aun con obstaculos).
* `h_manhattan`: |dc| + |df|. Admisible y consistente para costo por DISTANCIA
  (una torre avanza a lo sumo una unidad de Manhattan por casilla recorrida).
  Con costo UNITARIO NO es admisible: h(a1) = 14 y el costo real es 2.

Metricas (mismas convenciones que el Taller 1, D-19/D-20): prueba de objetivo al
EXTRAER; un nodo es "expandido" si se generan sus sucesores (el objetivo extraido
no se expande); "generado" = sucesor construido (la raiz no cuenta, los repetidos
descartados si); frontera maxima incluye entradas obsoletas de la cola de prioridad.
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field

ROOK_BOARD_SIZE = 8
ROOK_DIRECTIONS = {"N": (0, 1), "E": (1, 0), "S": (0, -1), "O": (-1, 0)}
ROOK_DEFAULT_ORDER = ("N", "E", "S", "O")
ROOK_COST_MODELS = ("unit", "distance")
_ROOK_FILES = "abcdefgh"


def rook_square(name: str) -> tuple[int, int]:
    """'a1' -> (0, 0); 'h8' -> (7, 7)."""
    name = name.strip().lower()
    col = _ROOK_FILES.index(name[0])
    row = int(name[1:]) - 1
    if not (0 <= col < ROOK_BOARD_SIZE and 0 <= row < ROOK_BOARD_SIZE):
        raise ValueError(f"casilla fuera del tablero: {name}")
    return (col, row)


def rook_square_name(sq: tuple[int, int]) -> str:
    """(0, 0) -> 'a1'."""
    return _ROOK_FILES[sq[0]] + str(sq[1] + 1)


@dataclass(frozen=True)
class RookProblem:
    """Problema de busqueda de la torre (formulacion AIMA de 5 componentes)."""

    start: tuple[int, int] = (0, 0)
    goal: tuple[int, int] = (7, 7)
    obstacles: frozenset = frozenset()
    cost_model: str = "unit"
    order: tuple = ROOK_DEFAULT_ORDER
    long_moves_first: bool = False

    def __post_init__(self):
        if self.cost_model not in ROOK_COST_MODELS:
            raise ValueError(f"modelo de costo desconocido: {self.cost_model}")
        if self.start in self.obstacles or self.goal in self.obstacles:
            raise ValueError("origen o destino sobre un obstaculo")
        if sorted(self.order) != sorted(ROOK_DIRECTIONS):
            raise ValueError("el orden debe ser una permutacion de N, E, S, O")

    def actions(self, state):
        """Acciones aplicables en `state`, en el orden documentado."""
        acts = []
        for d in self.order:
            dc, dr = ROOK_DIRECTIONS[d]
            ks = []
            c, r = state
            k = 0
            while True:
                c, r = c + dc, r + dr
                k += 1
                if not (0 <= c < ROOK_BOARD_SIZE and 0 <= r < ROOK_BOARD_SIZE):
                    break
                if (c, r) in self.obstacles:   # no puede ocupar ni saltar
                    break
                ks.append(k)
            if self.long_moves_first:
                ks.reverse()
            acts.extend((d, kk) for kk in ks)
        return acts

    def result(self, state, action):
        d, k = action
        dc, dr = ROOK_DIRECTIONS[d]
        return (state[0] + k * dc, state[1] + k * dr)

    def is_goal(self, state) -> bool:
        return state == self.goal

    def step_cost(self, state, action, next_state) -> int:
        return 1 if self.cost_model == "unit" else action[1]

    def with_cost(self, cost_model: str) -> "RookProblem":
        return RookProblem(self.start, self.goal, self.obstacles, cost_model,
                           self.order, self.long_moves_first)

    def is_valid_path(self, path) -> bool:
        """Cada paso es un movimiento de torre legal en las reglas simplificadas."""
        if not path or path[0] != self.start or path[-1] != self.goal:
            return False
        for a, b in zip(path, path[1:]):
            if a == b or (a[0] != b[0] and a[1] != b[1]):
                return False
            dc = (b[0] > a[0]) - (b[0] < a[0])
            dr = (b[1] > a[1]) - (b[1] < a[1])
            c, r = a
            while (c, r) != b:
                c, r = c + dc, r + dr
                if not (0 <= c < ROOK_BOARD_SIZE and 0 <= r < ROOK_BOARD_SIZE):
                    return False
                if (c, r) in self.obstacles:
                    return False
        return True


# --- heuristicas ------------------------------------------------------------
def h_rook_lines(state, goal) -> int:
    """Heuristica de la consigna: 0 en destino, 1 si comparte fila o columna, 2 si no."""
    if state == goal:
        return 0
    if state[0] == goal[0] or state[1] == goal[1]:
        return 1
    return 2


def h_manhattan(state, goal) -> int:
    """Distancia Manhattan |dc| + |df|."""
    return abs(state[0] - goal[0]) + abs(state[1] - goal[1])


def h_zero(state, goal) -> int:
    return 0


# --- resultados ---------------------------------------------------------------
def rook_path_costs(path) -> tuple[int, int]:
    """(costo unitario = numero de movimientos, costo por distancia = casillas recorridas)."""
    unit = max(len(path) - 1, 0)
    dist = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(path, path[1:]))
    return unit, dist


@dataclass
class RookSearchResult:
    algorithm: str
    cost_model: str
    path: list | None
    expanded: int = 0
    generated: int = 0
    max_frontier: int = 0
    expansion_order: list = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.path is not None

    @property
    def length(self) -> int:
        """Longitud = numero de movimientos (-1 si no hay ruta)."""
        return len(self.path) - 1 if self.path else -1

    @property
    def cost_unit(self) -> float:
        return rook_path_costs(self.path)[0] if self.path else float("inf")

    @property
    def cost_distance(self) -> float:
        return rook_path_costs(self.path)[1] if self.path else float("inf")

    @property
    def cost(self) -> float:
        """Costo segun el modelo con el que se busco."""
        return self.cost_unit if self.cost_model == "unit" else self.cost_distance

    def route_text(self) -> str:
        return " -> ".join(rook_square_name(s) for s in self.path) if self.path else "sin ruta"

    def row(self) -> dict:
        return {"algoritmo": self.algorithm, "modelo": self.cost_model,
                "ruta": self.route_text(), "longitud": self.length,
                "costo_unitario": self.cost_unit, "costo_distancia": self.cost_distance,
                "expandidos": self.expanded, "generados": self.generated,
                "frontera_max": self.max_frontier}


def _rook_rebuild(parents, state):
    path = [state]
    while parents[state] is not None:
        state = parents[state]
        path.append(state)
    path.reverse()
    return path


# --- busqueda no informada: BFS y DFS (nucleo comun, frontera inyectada) -------
def _rook_graph_search(problem: RookProblem, lifo: bool, name: str) -> RookSearchResult:
    """BFS (FIFO) o DFS (LIFO) en grafo, marcando al generar (Taller 1, D-17/D-19).

    En DFS los hijos se apilan en orden inverso para que el primero en salir sea el
    de la primera accion (Taller 1, D-18).
    """
    res = RookSearchResult(name, problem.cost_model, None)
    parents = {problem.start: None}
    frontier = deque([problem.start])
    res.max_frontier = 1
    while frontier:
        state = frontier.pop() if lifo else frontier.popleft()
        if problem.is_goal(state):
            res.path = _rook_rebuild(parents, state)
            return res
        res.expanded += 1
        res.expansion_order.append(state)
        children = []
        for action in problem.actions(state):
            child = problem.result(state, action)
            res.generated += 1
            if child not in parents:
                parents[child] = state
                children.append(child)
        frontier.extend(reversed(children) if lifo else children)
        res.max_frontier = max(res.max_frontier, len(frontier))
    return res


def rook_bfs(problem: RookProblem) -> RookSearchResult:
    """Busqueda en anchura: optima en LONGITUD (numero de movimientos)."""
    return _rook_graph_search(problem, lifo=False, name="BFS")


def rook_dfs(problem: RookProblem) -> RookSearchResult:
    """Busqueda en profundidad con control de repetidos: completa aqui (espacio
    finito, 64 estados) pero no optima; su ruta depende del orden de acciones."""
    return _rook_graph_search(problem, lifo=True, name="DFS")


# --- primero-el-mejor: UCS, A* y voraz --------------------------------------
def _rook_best_first(problem: RookProblem, kind: str, h, name: str) -> RookSearchResult:
    """BEST-FIRST-SEARCH de AIMA con eliminacion perezosa (Taller 1 D-21, Taller 2 A-04).

    Prioridades: UCS (g, orden); A* (g+h, h, orden); voraz (h, orden). `best_g`
    guarda el menor g conocido; una entrada con g mayor es obsoleta y se descarta
    al extraerla. Un hijo entra a la frontera solo si mejora `best_g`.
    """
    res = RookSearchResult(name, problem.cost_model, None)
    goal = problem.goal
    counter = 0

    def priority(g, s):
        hv = h(s, goal) if h is not None else 0
        if kind == "ucs":
            return (g, counter)
        if kind == "astar":
            return (g + hv, hv, counter)
        return (hv, counter)            # voraz

    best_g = {problem.start: 0}
    parents = {problem.start: None}
    frontier = [(priority(0, problem.start), 0, problem.start)]
    res.max_frontier = 1
    while frontier:
        _, g, state = heapq.heappop(frontier)
        if g > best_g[state]:
            continue                    # entrada obsoleta
        if problem.is_goal(state):
            res.path = _rook_rebuild(parents, state)
            return res
        res.expanded += 1
        res.expansion_order.append(state)
        for action in problem.actions(state):
            child = problem.result(state, action)
            res.generated += 1
            g2 = g + problem.step_cost(state, action, child)
            if child not in best_g or g2 < best_g[child]:
                best_g[child] = g2
                parents[child] = state
                counter += 1
                heapq.heappush(frontier, (priority(g2, child), g2, child))
        res.max_frontier = max(res.max_frontier, len(frontier))
    return res


def rook_ucs(problem: RookProblem) -> RookSearchResult:
    return _rook_best_first(problem, "ucs", None, "UCS")


def rook_astar(problem: RookProblem, h=None) -> RookSearchResult:
    """A* con la heuristica `h`; por omision la adecuada al modelo de costo."""
    h = h or rook_default_heuristic(problem.cost_model)
    return _rook_best_first(problem, "astar", h, f"A*({h.__name__})")


def rook_greedy(problem: RookProblem, h=None) -> RookSearchResult:
    """Voraz primero-el-mejor: ordena solo por h; no es optimo."""
    h = h or rook_default_heuristic(problem.cost_model)
    return _rook_best_first(problem, "greedy", h, f"Voraz({h.__name__})")


def rook_default_heuristic(cost_model: str):
    """Heuristica admisible adoptada para cada modelo de costo."""
    return h_rook_lines if cost_model == "unit" else h_manhattan


# --- verificacion exhaustiva de admisibilidad y consistencia ------------------
def rook_true_costs(problem: RookProblem) -> dict:
    """h*(s): costo optimo real de s al destino, para TODAS las casillas alcanzables.

    Dijkstra hacia atras desde el destino. Un movimiento de torre es reversible y
    cuesta lo mismo en ambos sentidos (mismas casillas recorridas), asi que el grafo
    inverso coincide con el directo. Es independiente de los buscadores evaluados
    (misma idea que en el Taller 1, D-07: no validar con lo que se valida).
    """
    dist = {problem.goal: 0}
    heap = [(0, problem.goal)]
    while heap:
        d, s = heapq.heappop(heap)
        if d > dist[s]:
            continue
        for a in problem.actions(s):
            t = problem.result(s, a)
            nd = d + problem.step_cost(s, a, t)
            if t not in dist or nd < dist[t]:
                dist[t] = nd
                heapq.heappush(heap, (nd, t))
    return dist


def rook_check_heuristic(problem: RookProblem, h) -> dict:
    """Comprueba admisibilidad (h <= h*) y consistencia (h(s) <= c + h(s')) en todo el espacio."""
    hstar = rook_true_costs(problem)
    goal = problem.goal
    not_admissible = [(s, h(s, goal), v) for s, v in sorted(hstar.items()) if h(s, goal) > v]
    inconsistent = []
    for s in hstar:
        for a in problem.actions(s):
            t = problem.result(s, a)
            if h(s, goal) > problem.step_cost(s, a, t) + h(t, goal):
                inconsistent.append((s, t))
    return {"states": len(hstar), "not_admissible": not_admissible,
            "inconsistent": len(inconsistent), "admissible": not not_admissible,
            "consistent": not inconsistent, "max_overestimate":
            max((hv - v for _, hv, v in not_admissible), default=0)}


# --- experimentos -------------------------------------------------------------
def rook_run_all(problem: RookProblem) -> list[RookSearchResult]:
    """BFS y DFS (no usan costo), UCS, A* y voraz con el modelo de `problem`."""
    out = [rook_bfs(problem), rook_dfs(problem), rook_ucs(problem),
           rook_astar(problem), rook_greedy(problem)]
    for r in out:
        r.cost_model = problem.cost_model
    return out


def rook_scenarios() -> dict:
    """Escenarios del informe: el de la consigna y variantes (otros extremos, obstaculos)."""
    return {
        "a1->h8": RookProblem(),
        "d4->h8": RookProblem(start=rook_square("d4")),
        "a1->h8 obstaculos": RookProblem(obstacles=ROOK_OBSTACLES_LENGTH_VS_COST),
    }


# Nueve obstaculos donde la ruta de MENOS MOVIMIENTOS no es la de MENOS CASILLAS:
# UCS unitario da 5 movimientos / 16 casillas; UCS por distancia, 7 movimientos /
# 14 casillas. Hallada con un muestreo aleatorio (random.Random(7), 4-14 obstaculos)
# y fijada aqui; las pruebas verifican la propiedad, no la busqueda.
ROOK_OBSTACLES_LENGTH_VS_COST = frozenset(
    rook_square(s) for s in ("a2", "b4", "c2", "d3", "d8", "e3", "f3", "g2", "h5"))


def rook_board_text(problem: RookProblem, path=None) -> str:
    """Tablero en texto: T origen, X destino, # obstaculo, * casilla de giro de la ruta."""
    turns = set(path[1:-1]) if path else set()
    lines = []
    for r in range(ROOK_BOARD_SIZE - 1, -1, -1):
        cells = []
        for c in range(ROOK_BOARD_SIZE):
            s = (c, r)
            ch = ("T" if s == problem.start else "X" if s == problem.goal else
                  "#" if s in problem.obstacles else "*" if s in turns else ".")
            cells.append(ch)
        lines.append(f"{r + 1} " + " ".join(cells))
    lines.append("  " + " ".join(_ROOK_FILES))
    return "\n".join(lines)


def rook_results_table(problem: RookProblem) -> list[dict]:
    """Filas con ambos modelos de costo para un escenario."""
    rows = []
    for model in ROOK_COST_MODELS:
        for r in rook_run_all(problem.with_cost(model)):
            rows.append(r.row())
    return rows


def rook_dfs_order_demo(problem: RookProblem | None = None) -> list[dict]:
    """La ruta de DFS depende del orden de las acciones (el costo optimo no)."""
    base = problem or RookProblem()
    variants = [("N,E,S,O; k creciente", ROOK_DEFAULT_ORDER, False),
                ("N,E,S,O; k decreciente", ROOK_DEFAULT_ORDER, True),
                ("E,N,O,S; k creciente", ("E", "N", "O", "S"), False),
                ("S,O,N,E; k creciente", ("S", "O", "N", "E"), False)]
    rows = []
    for label, order, longf in variants:
        p = RookProblem(base.start, base.goal, base.obstacles, base.cost_model, order, longf)
        r = rook_dfs(p)
        row = r.row()
        row["orden"] = label
        row["ucs_unit_cost"] = rook_ucs(p.with_cost("unit")).cost
        rows.append(row)
    return rows


def rook_unit_manhattan_counterexample() -> dict:
    """Manhattan con costo UNITARIO: sobreestima y A* deja de ser optimo.

    Busca, en un orden fijo y reproducible, un escenario con obstaculos donde
    A*(Manhattan) devuelve mas movimientos que BFS. Devuelve el primero encontrado.
    """
    unit = RookProblem()
    check = rook_check_heuristic(unit, h_manhattan)
    for prob in _rook_counterexample_candidates():
        opt = rook_bfs(prob)
        bad = rook_astar(prob, h_manhattan)
        if opt.found and bad.found and bad.length > opt.length:
            return {"problem": prob, "optimal": opt, "manhattan": bad,
                    "a1_h": h_manhattan(unit.start, unit.goal),
                    "a1_true": rook_true_costs(unit)[unit.start],
                    "violations_empty_board": len(check["not_admissible"])}
    return {"problem": None, "a1_h": h_manhattan(unit.start, unit.goal),
            "a1_true": rook_true_costs(unit)[unit.start],
            "violations_empty_board": len(check["not_admissible"])}


def _rook_counterexample_candidates():
    """Candidatos deterministas: muros horizontales con un hueco, de origen a1 a h8."""
    for row in range(1, 7):
        for gap in range(8):
            wall = frozenset((c, row) for c in range(8) if c != gap)
            yield RookProblem(obstacles=wall)


def plot_rook_expansions(table_by_scenario: dict, path: str | None = None):
    """Barras de nodos expandidos por algoritmo, escenario y modelo de costo.

    `table_by_scenario`: {nombre: filas de `rook_results_table`}. Devuelve la figura;
    si `path` se da, la guarda en PNG.
    """
    import matplotlib.pyplot as plt

    names = list(table_by_scenario)
    fig, axes = plt.subplots(1, len(ROOK_COST_MODELS), figsize=(12, 4.2), sharey=True)
    colors = ["#4C72B0", "#55A868", "#C44E52"]
    for ax, model in zip(axes, ROOK_COST_MODELS):
        algos = [r["algoritmo"] for r in table_by_scenario[names[0]] if r["modelo"] == model]
        width = 0.8 / len(names)
        for i, name in enumerate(names):
            rows = [r for r in table_by_scenario[name] if r["modelo"] == model]
            xs = [j + (i - (len(names) - 1) / 2) * width for j in range(len(algos))]
            bars = ax.bar(xs, [r["expandidos"] for r in rows], width,
                          label=name, color=colors[i % len(colors)])
            ax.bar_label(bars, fontsize=7)
        ax.set_xticks(range(len(algos)))
        ax.set_xticklabels(algos, rotation=20, fontsize=8)
        ax.set_title("costo unitario" if model == "unit" else "costo = casillas recorridas")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("nodos expandidos")
    axes[0].legend(fontsize=8)
    fig.suptitle("Microproblema de la torre: nodos expandidos por algoritmo")
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=130)
    return fig
