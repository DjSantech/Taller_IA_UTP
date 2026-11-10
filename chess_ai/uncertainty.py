"""Seccion 7, apartado D: incertidumbre y garantias (AIMA 4.3, 4.4 y 5.5).

D1. Busqueda AND-OR (AIMA, fig. 4.11) sobre un mate forzado REAL de ajedrez:
    nodos OR = jugadas del atacante (basta UNA que funcione); nodos AND = TODAS
    las respuestas legales del defensor (el plan debe funcionar contra cada una).
    El resultado es un PLAN CONDICIONAL, no una secuencia:
        {jugada_atacante: {respuesta_1: subplan_1, respuesta_2: subplan_2, ...}}
    Una hoja de mate es {jugada: {}} y solo se acepta si la jugada da jaque mate.
D2. Arbol pequeno con nodos de azar, SEPARADO del ajedrez (no se cambian reglas
    del ajedrez con dados): expectiminimax frente a minimax de peor caso.
D3. Kriegspiel: estado de creencia (conjunto de tableros posibles) y su
    crecimiento tras jugadas no observadas del rival.
"""
from __future__ import annotations

from dataclasses import dataclass

import chess

from chess_ai.environment import search_outcome

# =============================================================================
# D1. AND-OR para mates forzados
# =============================================================================


@dataclass
class AndOrStats:
    """Contadores de la busqueda AND-OR (para comparar posiciones y ordenes)."""

    or_nodes: int = 0
    and_nodes: int = 0
    failures_by_draw: int = 0


def _unc_key(board: chess.Board) -> str:
    """Clave de estado para el control de ciclos del camino (sin relojes de jugadas)."""
    return board.epd()


def _unc_attacker_order(board: chess.Board):
    """Orden de las jugadas OR: jaques primero, luego capturas, luego el resto.

    Solo cambia CUANTO se explora antes de hallar un plan, no si existe; es la misma
    idea que ordenar jugadas en alfa-beta (seccion 7.B).
    """
    moves = list(board.legal_moves)
    return sorted(moves, key=lambda m: (not board.gives_check(m), not board.is_capture(m),
                                        m.uci()))


def _unc_or_search(board, n_left, path, stats):
    stats.or_nodes += 1
    if n_left <= 0:
        return None
    key = _unc_key(board)
    if key in path:                       # ciclo en el camino actual: fracaso (AIMA)
        return None
    path = path | {key}
    for move in _unc_attacker_order(board):
        board.push(move)
        try:
            if board.is_checkmate():
                return {move: {}}
            if n_left > 1 and search_outcome(board) is None:
                sub = _unc_and_search(board, n_left - 1, path, stats)
                if sub is not None:
                    return {move: sub}
            elif search_outcome(board) is not None:
                stats.failures_by_draw += 1   # ahogado/tablas: no es exito
        finally:
            board.pop()
    return None


def _unc_and_search(board, n_left, path, stats):
    """Nodo AND: el plan debe existir para CADA respuesta legal del defensor."""
    stats.and_nodes += 1
    replies = list(board.legal_moves)
    if not replies:
        # AIMA devuelve el plan vacio si no hay estados que cubrir; en ajedrez eso
        # seria aceptar un AHOGADO como exito. Aqui solo el mate (ya detectado en el
        # nodo OR) es exito; sin respuestas y sin mate = fracaso.
        return None
    plan = {}
    for reply in replies:
        board.push(reply)
        try:
            if search_outcome(board) is not None:   # tablas tras la defensa
                stats.failures_by_draw += 1
                return None
            sub = _unc_or_search(board, n_left, path, stats)
        finally:
            board.pop()
        if sub is None:
            return None                   # UNA defensa sin respuesta tumba el plan
        plan[reply] = sub
    return plan


def and_or_mate_search(board: chess.Board, max_attacker_moves: int,
                       stats: AndOrStats | None = None, shortest: bool = True):
    """Busca un plan de mate forzado en a lo sumo `max_attacker_moves` jugadas del bando al turno.

    Devuelve el plan condicional {jugada: {respuesta: subplan}} o None (fracaso).
    Con `shortest=True` profundiza n = 1, 2, ..., max (como IDDFS en el Taller 1):
    el primer plan hallado es el del mate forzado MAS CORTO en jugadas del atacante.
    Con `shortest=False` acepta el primer plan de longitud <= max que encuentre.
    Trabaja sobre una copia: el tablero recibido (FEN y pila) queda intacto.
    """
    stats = stats if stats is not None else AndOrStats()
    work = board.copy(stack=True)
    if search_outcome(work) is not None:
        return None
    limits = range(1, max_attacker_moves + 1) if shortest else (max_attacker_moves,)
    for n in limits:
        plan = _unc_or_search(work, n, frozenset(), stats)
        if plan is not None:
            return plan
    return None


def verify_mate_plan(board: chess.Board, plan) -> dict:
    """Verificacion INDEPENDIENTE del buscador: recorre el plan con las reglas.

    Exige: en cada nodo OR una sola jugada legal; si su subplan es {} la jugada da
    jaque mate; si no, las claves del subplan son EXACTAMENTE todas las respuestas
    legales del defensor. Devuelve {'ok', 'leaves', 'max_attacker_moves', 'error'}.
    """
    info = {"ok": True, "leaves": 0, "max_attacker_moves": 0, "error": ""}

    def walk(b, p, depth):
        if not isinstance(p, dict) or len(p) != 1:
            raise ValueError("un nodo OR debe tener exactamente una jugada")
        (move, sub), = p.items()
        if move not in b.legal_moves:
            raise ValueError(f"jugada ilegal {move.uci()} en {b.fen()}")
        b.push(move)
        try:
            if not sub:
                if not b.is_checkmate():
                    raise ValueError(f"hoja sin mate tras {move.uci()}: {b.fen()}")
                info["leaves"] += 1
                info["max_attacker_moves"] = max(info["max_attacker_moves"], depth)
                return
            legal = set(b.legal_moves)
            if set(sub) != legal:
                missing = sorted(m.uci() for m in legal - set(sub))
                raise ValueError(f"defensas sin cubrir: {missing}")
            for reply, subplan in sub.items():
                b.push(reply)
                try:
                    walk(b, subplan, depth + 1)
                finally:
                    b.pop()
        finally:
            b.pop()

    try:
        walk(board.copy(stack=True), plan, 1)
    except ValueError as exc:
        info["ok"] = False
        info["error"] = str(exc)
    return info


def format_mate_plan(board: chess.Board, plan, indent: str = "") -> str:
    """Plan en SAN, legible: cada nivel AND lista todas las defensas."""
    lines = []
    b = board.copy(stack=True)

    def number(bb):
        return f"{bb.fullmove_number}." if bb.turn == chess.WHITE else f"{bb.fullmove_number}..."

    def rec(bb, p, ind):
        (move, sub), = p.items()
        text = f"{ind}{number(bb)} {bb.san(move)}"
        bb.push(move)
        if not sub:
            lines.append(text + "   (mate)")
        else:
            lines.append(text + f"   -> {len(sub)} defensa(s):")
            for reply, subplan in sorted(sub.items(), key=lambda kv: bb.san(kv[0])):
                lines.append(f"{ind}    si {number(bb)} {bb.san(reply)}:")
                bb.push(reply)
                rec(bb, subplan, ind + "        ")
                bb.pop()
        bb.pop()

    if plan is None:
        return indent + "sin plan (fracaso)"
    rec(b, plan, indent)
    return "\n".join(lines)


def count_plan_leaves(plan) -> int:
    (move, sub), = plan.items()
    if not sub:
        return 1
    return sum(count_plan_leaves(p) for p in sub.values())


# Posiciones de D1. Las "mate en 2" se verifican en las pruebas: existe plan de 2
# y NO existe plan de 1.
MATE_POSITIONS = {
    # La de la seccion 8 del enunciado: Qg7# (y no hay otra forma de fallar).
    "mate_en_1": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
    # Mate del pasillo (ultima fila) con torres dobladas: 1.Rd8+ Rxd8 2.Rxd8#.
    # Patron clasico; la unica defensa legal es capturar (AND con 1 rama).
    "mate_en_2_pasillo": "2r3k1/5ppp/8/8/8/8/3R1PPP/3R2K1 w - - 0 1",
    # Rey y dama contra rey y peon: jugada TRANQUILA 1.Kf6 y tres defensas, cada
    # una con un mate DISTINTO (Kh5 Qg5#, Kh7 Qg7#, a4 Qg6#). La hallamos con un
    # generador aleatorio de posiciones y la certificamos con verify_mate_plan.
    "mate_en_2_dama": "8/4K3/7k/p7/8/8/6Q1/8 w - - 0 1",
}


# =============================================================================
# D2. Arbol con azar: expectiminimax frente a minimax
# =============================================================================


@dataclass
class ChanceNode:
    """Nodo de un arbol de juego con azar.

    kind: 'max' | 'min' | 'chance' | 'leaf'. `children`: lista de (etiqueta, prob, nodo);
    prob solo se usa en nodos de azar (debe sumar 1). `utility` solo en hojas.
    """

    kind: str
    children: tuple = ()
    utility: float = 0.0


def _unc_leaf(u):
    return ChanceNode("leaf", (), float(u))


def _unc_min(*vals):
    return ChanceNode("min", tuple((f"r{i + 1}", None, _unc_leaf(v)) for i, v in enumerate(vals)))


def expectiminimax(node: ChanceNode) -> float:
    """Valor EXPECTIMINIMAX (AIMA 5.5): MAX, MIN y esperanza en nodos de azar."""
    if node.kind == "leaf":
        return node.utility
    vals = [(p, expectiminimax(ch)) for _, p, ch in node.children]
    if node.kind == "max":
        return max(v for _, v in vals)
    if node.kind == "min":
        return min(v for _, v in vals)
    total = sum(p for p, _ in vals)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"probabilidades que no suman 1: {total}")
    return sum(p * v for p, v in vals)


def worst_case_minimax(node: ChanceNode) -> float:
    """Minimax sobre el MISMO arbol, tratando el azar como un adversario (peor caso).

    Es lo que haria un agente minimax que ignora las probabilidades: supone que el
    "dado" elige siempre el resultado peor para MAX.
    """
    if node.kind == "leaf":
        return node.utility
    vals = [worst_case_minimax(ch) for _, _, ch in node.children]
    return max(vals) if node.kind == "max" else min(vals)


def chance_root_decision(root: ChanceNode, value_fn) -> tuple[str, dict]:
    """Accion elegida en la raiz MAX y valor de cada accion segun `value_fn`."""
    values = {label: value_fn(ch) for label, _, ch in root.children}
    best = max(values, key=lambda k: values[k])    # empate: la primera listada
    return best, values


def transform_utilities(node: ChanceNode, fn) -> ChanceNode:
    """Copia del arbol con utilidades transformadas por `fn` (misma estructura)."""
    if node.kind == "leaf":
        return _unc_leaf(fn(node.utility))
    return ChanceNode(node.kind, tuple((lab, p, transform_utilities(ch, fn))
                                       for lab, p, ch in node.children))


def chance_tree_leaves(node: ChanceNode) -> list:
    if node.kind == "leaf":
        return [node.utility]
    return [u for _, _, ch in node.children for u in chance_tree_leaves(ch)]


def chance_tree_safe_vs_risky() -> ChanceNode:
    """MAX elige 'segura' o 'arriesgada'; luego azar (moneda cargada); luego MIN; hojas.

    Escala de utilidad: puntos para MAX en [-10, 10] (+ bueno para MAX).
    Probabilidades: resultado favorable 0.75, desfavorable 0.25.
    """
    return ChanceNode("max", (
        ("segura", None, ChanceNode("chance", (
            ("favorable", 0.75, _unc_min(3, 4)),
            ("desfavorable", 0.25, _unc_min(2, 5))))),
        ("arriesgada", None, ChanceNode("chance", (
            ("favorable", 0.75, _unc_min(6, 8)),
            ("desfavorable", 0.25, _unc_min(-4, 0))))),
    ))


def chance_tree_scale() -> ChanceNode:
    """Arbol para mostrar que expectiminimax depende de la ESCALA (AIMA 5.5, fig. 5.12).

    Utilidades en {1, ..., 9}; probabilidades 0.9 / 0.1. Con la transformacion
    monotona u -> 4**u cambia la decision de expectiminimax y no la de minimax.
    """
    return ChanceNode("max", (
        ("a1", None, ChanceNode("chance", (
            ("p=0.9", 0.9, _unc_min(2, 5)),
            ("p=0.1", 0.1, _unc_min(3, 6))))),
        ("a2", None, ChanceNode("chance", (
            ("p=0.9", 0.9, _unc_min(1, 7)),
            ("p=0.1", 0.1, _unc_min(4, 9))))),
    ))


def chance_scale_transform(u: float) -> float:
    """Transformacion monotona creciente NO lineal usada en D2: u -> 4**u."""
    return 4.0 ** u


# =============================================================================
# D3. Kriegspiel: estado de creencia
# =============================================================================


def _unc_referee_percept(board: chess.Board, move: chess.Move) -> tuple:
    """Lo que el arbitro anuncia de una jugada del rival: (captura en casilla, da jaque).

    Simplificacion documentada: el arbitro de Kriegspiel anuncia capturas (con la
    casilla) y jaques; no anuncia que pieza se movio ni desde donde.
    """
    capture = chess.square_name(move.to_square) if board.is_capture(move) else None
    return (capture, board.gives_check(move))


def belief_after_hidden_move(belief: dict, percept=(None, False)) -> dict:
    """Actualiza el estado de creencia tras UNA jugada no observada del rival.

    `belief`: {epd: tablero}. Cada mundo se expande con todas las jugadas legales del
    rival cuyo anuncio del arbitro coincide con `percept`; se fusionan los tableros
    iguales.
    """
    out = {}
    for b in belief.values():
        for mv in b.legal_moves:
            if _unc_referee_percept(b, mv) != percept:
                continue
            nb = b.copy(stack=False)
            nb.push(mv)
            out.setdefault(nb.epd(), nb)
    return out


def belief_after_own_try(belief: dict, move_uci: str) -> tuple[dict, dict]:
    """Nuestro intento de jugada: el arbitro dice 'legal' o 'ilegal'.

    Devuelve (mundos donde seria legal, mundos donde seria ilegal): el anuncio parte
    el estado de creencia. En los mundos legales la jugada se aplica.
    """
    legal, illegal = {}, {}
    for key, b in belief.items():
        mv = chess.Move.from_uci(move_uci)
        if mv in b.legal_moves:
            nb = b.copy(stack=False)
            nb.push(mv)
            legal[nb.epd()] = nb
        else:
            illegal[key] = b
    return legal, illegal


def kriegspiel_belief_demo(fen: str = chess.STARTING_FEN,
                           own_moves=("e2e4", "g1f3")) -> list[dict]:
    """Crecimiento del estado de creencia de blancas en Kriegspiel.

    Blancas conocen sus jugadas; las de negras no se ven (percepcion del arbitro:
    "sin captura, sin jaque"). Devuelve una fila por paso con el tamano del estado
    de creencia.
    """
    board = chess.Board(fen)
    belief = {board.epd(): board}
    rows = [{"paso": "inicio", "mundos_posibles": len(belief)}]
    for uci in own_moves:
        belief, illegal = belief_after_own_try(belief, uci)
        rows.append({"paso": f"blancas juegan {uci} (conocida)", "mundos_posibles": len(belief),
                     "mundos_donde_era_ilegal": len(illegal)})
        belief = belief_after_hidden_move(belief)
        rows.append({"paso": "negras responden (no observada)", "mundos_posibles": len(belief)})
    return rows
