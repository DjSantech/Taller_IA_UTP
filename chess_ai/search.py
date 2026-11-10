"""Busqueda adversaria: minimax, alfa-beta y alfa-beta mejorado (AIMA cap. 5).

CONVENCION MAX/MIN (coherente con D-06)
    MAX = BLANCAS y MIN = NEGRAS, siempre, sobre valores desde blancas: la
    evaluacion E(s) y las utilidades terminales (`terminal_value_white`). Asi el
    codigo es el minimax de AIMA tal cual (dos ramas explicitas, no negamax) y un
    mismo numero significa lo mismo en cualquier nodo del arbol. El valor de la
    raiz se convierte al final a la perspectiva de quien decide con
    `perspective_sign(turno)`: eso es `Decision.score`. Cuando decide negras, la
    raiz es un nodo MIN y la jugada elegida minimiza E (= maximiza -E).

DEFINICIONES (identicas en minimax y alfa-beta, para que los numeros se comparen)
    * nodo  = cada llamada a la funcion recursiva sobre una posicion, incluida la
              raiz. Se cuenta al entrar, antes de mirar si es terminal.
    * hoja  = nodo donde se devuelve una utilidad terminal exacta (mate, ahogado,
              material insuficiente, regla de 50, repeticion triple segun
              `search_outcome`) o donde se aplica E porque la profundidad llego a 0.
              Toda hoja es nodo; un nodo interior no es hoja.
    * poda  = EVENTO de corte: en un nodo MAX el valor alcanzo `valor >= beta`
              (o en un nodo MIN `valor <= alfa`) y quedaban hermanos sin explorar.
              `SearchStats.cutoffs` cuenta eventos; ademas se cuenta aparte el
              numero de hijos omitidos (`pruned_children`). Si la condicion se
              cumple con el ultimo hijo no hay nada que podar y no se cuenta.
    * profundidad = plies que faltan por expandir; `ply` = distancia a la raiz
              (la usan los mates: ganar a distancia `ply` vale MATE_SCORE - ply).

ORDEN DE LAS COMPROBACIONES EN CADA NODO (pseudocodigo del enunciado)
    1. contar el nodo; 2. comprobar el plazo (solo si hay `Deadline`);
    3. terminal ANTES que corte de profundidad (D-07); 4. profundidad 0 -> E;
    5. expandir (orden natural de python-chess u ordenado), push/pop con
       try/finally para que el tablero quede intacto incluso si salta
       `SearchTimeout` u otra excepcion.

DESEMPATES
    En cada nodo se conserva el PRIMER hijo que alcanza el mejor valor (se
    reemplaza solo con `>` en MAX o `<` en MIN). Por eso minimax (orden natural)
    y alfa-beta ordenado pueden devolver jugadas distintas con el MISMO valor:
    el orden decide cual de las jugadas empatadas aparece primero.

PLAZO (solo el agente mejorado)
    Los agentes de profundidad fija ignoran `time_limit_s` (su objeto de estudio es
    el arbol completo; el controlador mide y registra el exceso, D-10). El
    mejorado crea un `Deadline` y lo consulta al ENTRAR a cada nodo: si vencio,
    lanza `SearchTimeout`, que deshace todos los push con los `finally` y llega a
    la profundizacion iterativa, que descarta la iteracion incompleta.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import NamedTuple

import chess

from chess_ai.contract import Decision, SearchStats
from chess_ai.environment import (Deadline, SearchTimeout, game_outcome, is_mate_score,
                                  perspective_sign, search_outcome, terminal_value_white)
from chess_ai.evaluation import DEFAULT_EVALUATOR

_SEARCH_INF = float("inf")
_SEARCH_MAX_PLY = 128
# Valores para ordenar capturas MVV-LVA (victima mas valiosa, atacante menos valioso).
_SEARCH_ORDER_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5,
                        chess.QUEEN: 9, chess.KING: 20}

# Pregunta 1 de la sustentacion: el voraz de un ply falla y minimax de profundidad 2
# encuentra la defensa. Blancas: Rg1, Dd1, Cd4, peones a2 b2 c2 f2 g2 h2. Negras: Rg8,
# Te8, peones a7 b7 c7 e5 f7 g7 h5. El peon e5 ATACA al caballo d4 y el peon h5 esta
# sin defensa. El voraz (= minimax de profundidad 1, una sola capa MAX) elige Dxh5:
# gana un peon (+1) y no mira la respuesta. Minimax de profundidad 2 ve que tras Dxh5
# negras juegan exd4 (el caballo vale 3.2) y prefiere poner el caballo a salvo (Cf5).
# Valores medidos con E0 (desde blancas): profundidad 1 -> Dxh5 = +786.7;
# profundidad 2 -> Dxh5 = +432.8 (tras exd4) frente a Cf5 = +673.4.
MINIMAX_DEFENSE_FEN = "4r1k1/ppp2pp1/8/4p2p/3N4/8/PPP2PPP/3Q2K1 w - - 0 1"
MINIMAX_DEFENSE_GREEDY_MOVE = "d1h5"                     # Dxh5?, deja el caballo colgado
# Retiradas que salvan el caballo (Cc6 y Ce6 no: las toman b7 y f7).
MINIMAX_DEFENSE_MOVES = ("d4f5", "d4b5", "d4b3", "d4f3", "d4e2")


@dataclass
class PruneEvent:
    """Una poda registrada (para trazarla a mano). Valores siempre desde blancas.

    * `node_type`: 'MAX' (juegan blancas, corta si valor >= beta) o 'MIN'
      (juegan negras, corta si valor <= alfa).
    * `path`: jugadas SAN desde la raiz hasta el nodo donde ocurrio la poda.
    * `alpha`, `beta`: ventana del nodo en el momento del corte.
    * `explored`: hijos ya explorados con el valor que devolvio cada uno.
    * `cause`: la jugada cuyo valor provoco el corte.
    * `pruned`: hermanos que no se exploraron.
    """
    ply: int
    depth: int
    node_type: str
    path: list
    fen: str
    alpha: float
    beta: float
    value: float
    cause: str
    explored: list = field(default_factory=list)
    pruned: list = field(default_factory=list)


def format_prune_event(ev: PruneEvent) -> str:
    """Texto legible de una poda: ruta, ventana, hijos explorados y omitidos."""
    ruta = " ".join(ev.path) if ev.path else "(raiz)"
    cond = "valor >= beta" if ev.node_type == "MAX" else "valor <= alfa"
    hijos = ", ".join(f"{san}={val:+.1f}" for san, val in ev.explored)
    return (f"[{ev.node_type} ply={ev.ply} prof={ev.depth}] ruta: {ruta}\n"
            f"  ventana alfa={ev.alpha:+.1f} beta={ev.beta:+.1f}; explorados: {hijos}\n"
            f"  corte por {ev.cause} ({cond}: {ev.value:+.1f}); "
            f"podados ({len(ev.pruned)}): {' '.join(ev.pruned)}")


class SearchContext:
    """Estado compartido por una busqueda: metricas, plazo, orden, PV y registro de podas.

    `pv[ply]` es la mejor linea encontrada desde el nodo del `ply` actual; `pv[0][0]`
    es la jugada de la raiz. `prev_pv` es la variante principal de la iteracion
    anterior (profundizacion iterativa) y se prueba primero en cada `ply`.
    """

    def __init__(self, evaluator=DEFAULT_EVALUATOR, deadline: Deadline | None = None,
                 ordering: bool = False, log_prunes: bool = False, max_log: int = 500,
                 quiescence: bool = False, root: chess.Board | None = None):
        self.evaluator = evaluator
        self.deadline = deadline
        self.ordering = ordering
        self.quiescence = quiescence
        self.stats = SearchStats()
        self.pruned_children = 0
        self.qnodes = 0
        self.sort_time = 0.0
        self.pv = [[] for _ in range(_SEARCH_MAX_PLY + 1)]
        self.prev_pv: list = []
        self.killers = [[] for _ in range(_SEARCH_MAX_PLY + 1)]
        self.prune_log = [] if log_prunes else None
        self.max_log = max_log
        self.root_board = root.copy(stack=False) if root is not None else None
        self.root_len = len(root.move_stack) if root is not None else 0


# ------------------------------------------------------------------ ordenacion
def _search_order_moves(board: chess.Board, ply: int, ctx: SearchContext) -> list:
    """Ordena las jugadas legales: PV previa > promociones > capturas MVV-LVA > killers > resto.

    Es un sort estable: entre jugadas del mismo grupo se conserva el orden de
    generacion de python-chess. El tiempo se acumula en `ctx.sort_time`.
    """
    t0 = time.perf_counter()
    pv_move = ctx.prev_pv[ply] if ply < len(ctx.prev_pv) else None
    killers = ctx.killers[ply] if ply <= _SEARCH_MAX_PLY else ()
    scored = []
    for move in board.legal_moves:
        if move == pv_move:
            s = 1_000_000
        elif move.promotion:
            s = 900_000 + _SEARCH_ORDER_VALUES[move.promotion]
        elif board.is_capture(move):
            victim = (chess.PAWN if board.is_en_passant(move)
                      else board.piece_type_at(move.to_square))
            attacker = board.piece_type_at(move.from_square)
            s = 500_000 + 100 * _SEARCH_ORDER_VALUES[victim] - _SEARCH_ORDER_VALUES[attacker]
        elif move in killers:
            s = 400_000 - killers.index(move)
        else:
            s = 0
        scored.append((s, move))
    scored.sort(key=lambda t: -t[0])
    ctx.sort_time += time.perf_counter() - t0
    return [m for _, m in scored]


def _search_store_killer(board: chess.Board, move: chess.Move, ply: int, ctx: SearchContext) -> None:
    """Jugada tranquila que produjo un corte: se recuerda (2 por ply) para probarla antes."""
    if ply > _SEARCH_MAX_PLY or move.promotion or board.is_capture(move):
        return
    ks = ctx.killers[ply]
    if move in ks:
        return
    ks.insert(0, move)
    del ks[2:]


def _search_path_san(board: chess.Board, ctx: SearchContext) -> list:
    replay = ctx.root_board.copy(stack=False)
    out = []
    for mv in board.move_stack[ctx.root_len:]:
        out.append(replay.san(mv))
        replay.push(mv)
    return out


def _search_log_cutoff(board, ctx, ply, depth, node_type, alpha, beta, value,
                       cause, explored, pruned) -> None:
    if ctx.prune_log is None or len(ctx.prune_log) >= ctx.max_log or ctx.root_board is None:
        return
    ctx.prune_log.append(PruneEvent(
        ply=ply, depth=depth, node_type=node_type, path=_search_path_san(board, ctx),
        fen=board.fen(), alpha=alpha, beta=beta, value=value, cause=board.san(cause),
        explored=[(board.san(m), v) for m, v in explored],
        pruned=[board.san(m) for m in pruned]))


# ------------------------------------------------------------------ minimax
def _search_minimax(board: chess.Board, depth: int, ply: int, ctx: SearchContext) -> float:
    """MINIMAX(estado, profundidad) con MAX = blancas y MIN = negras. Valor desde blancas."""
    ctx.stats.nodes += 1
    if ctx.deadline is not None:
        ctx.deadline.check()
    ctx.pv[ply] = []
    outcome = search_outcome(board)
    if outcome is not None:                      # terminal antes que corte
        ctx.stats.leaves += 1
        return terminal_value_white(outcome, ply)
    if depth <= 0:
        ctx.stats.leaves += 1
        return ctx.evaluator(board)
    moves = list(board.legal_moves)
    if board.turn == chess.WHITE:                # nodo MAX
        value = -_SEARCH_INF
        for move in moves:
            board.push(move)
            try:
                child = _search_minimax(board, depth - 1, ply + 1, ctx)
            finally:
                board.pop()
            if child > value:
                value = child
                ctx.pv[ply] = [move] + ctx.pv[ply + 1]
        return value
    value = _SEARCH_INF                          # nodo MIN
    for move in moves:
        board.push(move)
        try:
            child = _search_minimax(board, depth - 1, ply + 1, ctx)
        finally:
            board.pop()
        if child < value:
            value = child
            ctx.pv[ply] = [move] + ctx.pv[ply + 1]
    return value


# ------------------------------------------------------------------ alfa-beta
def _search_alphabeta(board: chess.Board, depth: int, ply: int, alpha: float, beta: float,
                      ctx: SearchContext) -> float:
    """ALFABETA(estado, profundidad, alfa, beta): mismo arbol y hojas que minimax, con poda.

    alfa = mejor valor ya garantizado para MAX en la ruta; beta = idem para MIN.
    Devuelve el valor exacto si cae dentro de (alfa, beta); si no, una cota
    (fail-soft) que basta para que el padre descarte esa rama. En la raiz la
    ventana es (-inf, +inf), asi que el valor de la raiz es EXACTO e igual al de
    minimax.
    """
    ctx.stats.nodes += 1
    if ctx.deadline is not None:
        ctx.deadline.check()
    ctx.pv[ply] = []
    outcome = search_outcome(board)
    if outcome is not None:
        ctx.stats.leaves += 1
        return terminal_value_white(outcome, ply)
    if depth <= 0:
        if ctx.quiescence:
            return _search_quiescence(board, ply, alpha, beta, ctx, entry=True)
        ctx.stats.leaves += 1
        return ctx.evaluator(board)
    moves = _search_order_moves(board, ply, ctx) if ctx.ordering else list(board.legal_moves)
    logging = ctx.prune_log is not None
    explored = [] if logging else None
    n = len(moves)
    if board.turn == chess.WHITE:                # nodo MAX
        value = -_SEARCH_INF
        for i, move in enumerate(moves):
            board.push(move)
            try:
                child = _search_alphabeta(board, depth - 1, ply + 1, alpha, beta, ctx)
            finally:
                board.pop()
            if logging:
                explored.append((move, child))
            if child > value:
                value = child
                ctx.pv[ply] = [move] + ctx.pv[ply + 1]
            if value >= beta:                    # MIN nunca dejara llegar aqui
                if i + 1 < n:
                    ctx.stats.cutoffs += 1
                    ctx.pruned_children += n - i - 1
                    if ctx.ordering:
                        _search_store_killer(board, move, ply, ctx)
                    if logging:
                        _search_log_cutoff(board, ctx, ply, depth, "MAX", alpha, beta, value,
                                           move, explored, moves[i + 1:])
                return value
            if value > alpha:
                alpha = value
        return value
    value = _SEARCH_INF                          # nodo MIN
    for i, move in enumerate(moves):
        board.push(move)
        try:
            child = _search_alphabeta(board, depth - 1, ply + 1, alpha, beta, ctx)
        finally:
            board.pop()
        if logging:
            explored.append((move, child))
        if child < value:
            value = child
            ctx.pv[ply] = [move] + ctx.pv[ply + 1]
        if value <= alpha:                       # MAX nunca dejara llegar aqui
            if i + 1 < n:
                ctx.stats.cutoffs += 1
                ctx.pruned_children += n - i - 1
                if ctx.ordering:
                    _search_store_killer(board, move, ply, ctx)
                if logging:
                    _search_log_cutoff(board, ctx, ply, depth, "MIN", alpha, beta, value,
                                       move, explored, moves[i + 1:])
            return value
        if value < beta:
            beta = value
    return value


def _search_quiescence(board: chess.Board, ply: int, alpha: float, beta: float,
                       ctx: SearchContext, entry: bool = False) -> float:
    """Busqueda de quietud (OPCIONAL, solo con quiescence=True en el mejorado).

    En la frontera no se aplica E de inmediato si hay capturas o promociones
    pendientes: el bando al turno puede "quedarse quieto" (stand pat = E) o
    seguir capturando. Cada llamada cuenta como nodo y como hoja (aplica E);
    `ctx.qnodes` cuenta aparte cuantos nodos son de quietud. ATENCION: con
    quietud el arbol ya no es el de profundidad fija, asi que sus valores no se
    comparan con minimax/alfa-beta sin quietud.
    """
    if not entry:                                # la entrada ya se conto en alfa-beta
        ctx.stats.nodes += 1
        ctx.qnodes += 1
        if ctx.deadline is not None:
            ctx.deadline.check()
        outcome = search_outcome(board)
        if outcome is not None:
            ctx.stats.leaves += 1
            return terminal_value_white(outcome, ply)
    ctx.pv[ply] = []
    ctx.stats.leaves += 1
    stand = ctx.evaluator(board)
    if ply >= _SEARCH_MAX_PLY - 1:
        return stand
    noisy = [m for m in _search_order_moves(board, ply, ctx)
             if m.promotion or board.is_capture(m)]
    if board.turn == chess.WHITE:
        value = stand
        if value >= beta:
            return value
        alpha = max(alpha, value)
        for move in noisy:
            board.push(move)
            try:
                child = _search_quiescence(board, ply + 1, alpha, beta, ctx)
            finally:
                board.pop()
            if child > value:
                value = child
            if value >= beta:
                return value
            alpha = max(alpha, value)
        return value
    value = stand
    if value <= alpha:
        return value
    beta = min(beta, value)
    for move in noisy:
        board.push(move)
        try:
            child = _search_quiescence(board, ply + 1, alpha, beta, ctx)
        finally:
            board.pop()
        if child < value:
            value = child
        if value <= alpha:
            return value
        beta = min(beta, value)
    return value


# ------------------------------------------------------------------ utilidades comunes
def _search_terminal_decision(board: chess.Board, start: float) -> Decision | None:
    """Si la PARTIDA ya termino (politica del taller, claim_draw=True) no hay decision nueva."""
    outcome = game_outcome(board)
    if outcome is None:
        return None
    stats = SearchStats(nodes=1, leaves=1, elapsed_s=time.perf_counter() - start)
    return Decision(None, perspective_sign(board.turn) * terminal_value_white(outcome, 0), stats)


def _search_fixed_depth(board: chess.Board, algorithm: str, depth: int, evaluator,
                        ordering: bool = False, log_prunes: bool = False,
                        max_log: int = 500) -> tuple:
    """Busqueda de profundidad fija desde la raiz. Devuelve (valor_blancas, jugada, ctx)."""
    if depth < 1:
        raise ValueError("la profundidad debe ser >= 1")
    if algorithm == "minimax":
        if ordering:
            raise ValueError("minimax se compara siempre en orden natural")
        ctx = SearchContext(evaluator)
        value = _search_minimax(board, depth, 0, ctx)
    elif algorithm in ("alphabeta", "alfabeta"):
        ctx = SearchContext(evaluator, ordering=ordering, log_prunes=log_prunes,
                            max_log=max_log, root=board if log_prunes else None)
        value = _search_alphabeta(board, depth, 0, -_SEARCH_INF, _SEARCH_INF, ctx)
    else:
        raise ValueError(f"algoritmo desconocido: {algorithm}")
    move = ctx.pv[0][0] if ctx.pv[0] else None
    ctx.stats.completed_depth = depth
    return value, move, ctx


class RootSearchResult(NamedTuple):
    """Resultado de `search_root`. `value` desde el jugador al turno en la raiz."""
    value: float | None
    move: chess.Move | None
    stats: SearchStats
    sort_time: float


def search_root(board: chess.Board, algorithm: str = "minimax", depth: int = 2,
                evaluator=DEFAULT_EVALUATOR, ordering: bool = False) -> RootSearchResult:
    """Utilidad del Experimento 1: minimax / alfa-beta natural / alfa-beta ordenado.

    `algorithm` en {"minimax", "alphabeta"}; `ordering` solo para alfa-beta.
    Mismo arbol, mismas hojas y misma E en los tres casos; deja el tablero intacto.
    `sort_time` es el tiempo gastado ordenando (incluido en `stats.elapsed_s`).
    """
    start = time.perf_counter()
    term = _search_terminal_decision(board, start)
    if term is not None:
        return RootSearchResult(term.score, None, term.stats, 0.0)
    value_white, move, ctx = _search_fixed_depth(board, algorithm, depth, evaluator, ordering)
    ctx.stats.elapsed_s = time.perf_counter() - start
    return RootSearchResult(perspective_sign(board.turn) * value_white, move, ctx.stats,
                            ctx.sort_time)


# ------------------------------------------------------------------ agentes
class MinimaxAgent:
    """Minimax MAX/MIN de profundidad fija (AIMA 5.2). Ignora `time_limit_s` (ver modulo)."""

    def __init__(self, depth: int = 2, evaluator=DEFAULT_EVALUATOR, name: str = "Minimax"):
        self.depth = depth
        self.evaluator = evaluator
        self.name = name
        self.last_pv: list = []

    def choose(self, board: chess.Board, *, time_limit_s: float = 0.0, seed: int = 0) -> Decision:
        start = time.perf_counter()
        term = _search_terminal_decision(board, start)
        if term is not None:
            return term
        value_white, move, ctx = _search_fixed_depth(board, "minimax", self.depth, self.evaluator)
        self.last_pv = list(ctx.pv[0])
        ctx.stats.elapsed_s = time.perf_counter() - start
        return Decision(move, perspective_sign(board.turn) * value_white, ctx.stats)


class AlphaBetaAgent:
    """Alfa-beta de profundidad fija (AIMA 5.3): mismo valor que minimax, menos nodos.

    * `ordering=False`: orden natural de python-chess (el mismo que usa minimax).
    * `ordering=True`: "alfa-beta ordenado" del Experimento 1 (promociones,
      capturas MVV-LVA y killers). El arbol y las hojas son los mismos; cambia
      solo el orden en que se visitan los hijos, por eso el valor no cambia.
    * `log_prunes=True`: guarda en `last_prune_log` cada poda (`PruneEvent`)
      para trazarla a mano; `format_prune_event` la imprime.
    """

    def __init__(self, depth: int = 2, evaluator=DEFAULT_EVALUATOR, ordering: bool = False,
                 name: str = "Alfa-beta", log_prunes: bool = False, max_log: int = 500):
        self.depth = depth
        self.evaluator = evaluator
        self.ordering = ordering
        self.name = name
        self.log_prunes = log_prunes
        self.max_log = max_log
        self.last_prune_log: list = []
        self.last_pruned_children = 0
        self.last_sort_time_s = 0.0
        self.last_pv: list = []

    def choose(self, board: chess.Board, *, time_limit_s: float = 0.0, seed: int = 0) -> Decision:
        start = time.perf_counter()
        term = _search_terminal_decision(board, start)
        if term is not None:
            return term
        value_white, move, ctx = _search_fixed_depth(board, "alphabeta", self.depth,
                                                     self.evaluator, self.ordering,
                                                     self.log_prunes, self.max_log)
        self.last_prune_log = ctx.prune_log or []
        self.last_pruned_children = ctx.pruned_children
        self.last_sort_time_s = ctx.sort_time
        self.last_pv = list(ctx.pv[0])
        ctx.stats.elapsed_s = time.perf_counter() - start
        return Decision(move, perspective_sign(board.turn) * value_white, ctx.stats)


class AlphaBetaImprovedAgent:
    """Alfa-beta con ordenacion + profundizacion iterativa con plazo (`time_limit_s`).

    PROFUNDIZACION_ITERATIVA (pseudocodigo del enunciado):
      1. si la partida ya termino -> Decision(None, utilidad);
      2. jugada de RESPALDO = primera jugada legal segun la ordenacion (capturas
         MVV-LVA primero), con score None y completed_depth 0;
      3. para d = 1, 2, ..., max_depth: alfa-beta ordenado a profundidad d con la
         variante principal (PV) de la iteracion anterior probada primero en cada
         ply, mas promociones, capturas MVV-LVA y killers;
         - si la iteracion TERMINA: reemplaza (jugada, valor) y completed_depth = d;
         - si salta `SearchTimeout`: se descarta la iteracion parcial y se
           conserva la ultima completa (o el respaldo si ninguna termino);
         - si el valor es de mate, se para: mas profundidad no lo cambia.
    El plazo se comprueba al entrar a cada nodo y antes de empezar cada iteracion.
    `stats.nodes/leaves/cutoffs` suman TODAS las iteraciones (incluida la
    abortada): es el trabajo real gastado. `last_iterations` detalla cada una y
    `last_sort_time_s` el tiempo de ordenar. Sin plazo (time_limit_s <= 0) llega
    hasta `max_depth`.
    """

    def __init__(self, max_depth: int = 8, evaluator=DEFAULT_EVALUATOR,
                 name: str = "Alfa-beta mejorado", quiescence: bool = False):
        self.max_depth = max_depth
        self.evaluator = evaluator
        self.name = name
        self.quiescence = quiescence
        self.last_iterations: list = []
        self.last_sort_time_s = 0.0
        self.last_pv: list = []

    def choose(self, board: chess.Board, *, time_limit_s: float = 0.2, seed: int = 0) -> Decision:
        start = time.perf_counter()
        term = _search_terminal_decision(board, start)
        if term is not None:
            return term
        deadline = Deadline(time_limit_s)
        ctx = SearchContext(self.evaluator, deadline=deadline, ordering=True,
                            quiescence=self.quiescence)
        best_move = _search_order_moves(board, 0, ctx)[0]          # respaldo legal
        best_value_white = None
        completed = 0
        self.last_iterations = []
        for depth in range(1, self.max_depth + 1):
            if deadline.expired():
                break
            before = (ctx.stats.nodes, ctx.stats.leaves, ctx.stats.cutoffs, deadline.elapsed())
            try:
                value = _search_alphabeta(board, depth, 0, -_SEARCH_INF, _SEARCH_INF, ctx)
            except SearchTimeout:
                self.last_iterations.append(self._search_iteration_row(depth, False, ctx, before,
                                                                       deadline, None, None))
                break
            best_move, best_value_white, completed = ctx.pv[0][0], value, depth
            ctx.prev_pv = list(ctx.pv[0])
            self.last_iterations.append(self._search_iteration_row(depth, True, ctx, before,
                                                                   deadline, value, best_move))
            if is_mate_score(value):
                break
        self.last_pv = list(ctx.prev_pv)
        self.last_sort_time_s = ctx.sort_time
        ctx.stats.completed_depth = completed
        ctx.stats.elapsed_s = time.perf_counter() - start
        score = (None if best_value_white is None
                 else perspective_sign(board.turn) * best_value_white)
        return Decision(best_move, score, ctx.stats)

    @staticmethod
    def _search_iteration_row(depth, completed, ctx, before, deadline, value, move) -> dict:
        return {"depth": depth, "completed": completed,
                "nodes": ctx.stats.nodes - before[0], "leaves": ctx.stats.leaves - before[1],
                "cutoffs": ctx.stats.cutoffs - before[2],
                "elapsed_s": deadline.elapsed() - before[3],
                "value_white": value, "move": move.uci() if move is not None else None}
