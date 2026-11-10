"""Pruebas de minimax, alfa-beta y alfa-beta mejorado (seccion 8 del enunciado).

Posiciones propias (requisito de la seccion 8), con su justificacion:
* OWN["mate_in_two"]  k7/8/2K5/8/8/8/8/7R w: el rey negro solo tiene a7/b8; tras
  Kb6 (o Kc7) le queda una casilla y Th8#/Ta1# es mate. No hay mate en uno (Th8+
  deja Ka7). Prueba que la profundidad 3 (jugada, respuesta, mate) encuentra el
  mate en dos con valor MATE_SCORE - 3 y que la profundidad 2 todavia no lo ve.
* OWN["poisoned"]     6k1/pp3ppp/4p3/3n4/8/8/PP3PPP/3Q2K1 w: el caballo d5 parece
  colgado, pero lo defiende e6. Dxd5 gana 3.2 a un ply y pierde la dama (9) a dos.
  El voraz (profundidad 1) la toma; minimax de profundidad 2 no.
* OWN["evasion"]      k3r3/8/8/7Q/8/8/8/4K3 w: blancas en jaque por la torre e8;
  la mejor evasion es capturar la pieza que da jaque (Dxe8+).
* OWN["black_capture"] 7k/7p/8/8/Q7/2n5/7P/4K3 b: juegan negras y la dama a4 esta
  sin defensa frente al caballo c3. Comprueba la perspectiva: con negras al turno
  el agente debe elegir lo bueno para negras (Cxa4), no para blancas.
* MINIMAX_DEFENSE_FEN (en search.py): pregunta 1 de la sustentacion.

Intermedias (para la equivalencia minimax = alfa-beta): una de piezas menores, una
captura de caballos, una con negras en jaque, un final de torres y uno de peones.
"""
import chess
import pytest

from conftest import POSITIONS
from chess_ai.environment import MATE_SCORE, Deadline, SearchTimeout
from chess_ai.evaluation import DEFAULT_EVALUATOR
from chess_ai.search import (MINIMAX_DEFENSE_FEN, MINIMAX_DEFENSE_GREEDY_MOVE,
                             MINIMAX_DEFENSE_MOVES, AlphaBetaAgent, AlphaBetaImprovedAgent,
                             MinimaxAgent, SearchContext, _search_alphabeta, _search_minimax,
                             format_prune_event, search_root)

OWN = {
    "mate_in_two": "k7/8/2K5/8/8/8/8/7R w - - 0 1",
    "poisoned": "6k1/pp3ppp/4p3/3n4/8/8/PP3PPP/3Q2K1 w - - 0 1",
    "evasion": "k3r3/8/8/7Q/8/8/8/4K3 w - - 0 1",
    "black_capture": "7k/7p/8/8/Q7/2n5/7P/4K3 b - - 0 1",
}
INTERMEDIATE = {
    "minor_pieces": "r3k3/ppp2ppp/2n5/3p4/3P4/2N5/PPP2PPP/R3K3 w Qq - 0 1",
    "knight_capture": "4k3/pp3ppp/2n5/3p4/3N4/8/PP3PPP/4K3 w - - 0 1",
    "black_in_check": "r3k3/ppp2ppp/8/1B6/8/8/PPP2PPP/4K2R b K - 0 1",
    "rook_endgame": "8/5k2/8/3R4/8/2K5/5r2/8 w - - 0 1",
    "pawn_endgame": "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1",
}
STATEMENT_NON_TERMINAL = {k: POSITIONS[k] for k in
                          ("initial", "castling", "promotion", "en_passant", "mate_in_one")}
EQUIV_CASES = {**STATEMENT_NON_TERMINAL, **INTERMEDIATE, "evasion": OWN["evasion"],
               "black_capture": OWN["black_capture"], "mate_in_two": OWN["mate_in_two"]}
INF = float("inf")
_MINIMAX_CACHE = {}


def _minimax_root(fen, depth):
    """minimax de profundidad 3 es caro: se calcula una sola vez por (posicion, profundidad)."""
    key = (fen, depth)
    if key not in _MINIMAX_CACHE:
        _MINIMAX_CACHE[key] = search_root(chess.Board(fen), "minimax", depth)
    return _MINIMAX_CACHE[key]


def _value_after(board, move, depth):
    """Valor minimax (desde blancas) de jugar `move` y buscar depth-1 plies mas."""
    ctx = SearchContext(DEFAULT_EVALUATOR)
    board.push(move)
    try:
        return _search_minimax(board, depth - 1, 1, ctx)
    finally:
        board.pop()


def _snapshot(board):
    return board.fen(), list(board.move_stack)


def _all_agents():
    """Agentes de las pruebas de comportamiento. Se llaman con time_limit_s=0 (sin plazo):
    el mejorado llega siempre a max_depth y el resultado NO depende de la velocidad de
    la maquina. Las pruebas del plazo estan aparte y solo afirman invariantes."""
    return [MinimaxAgent(depth=2), AlphaBetaAgent(depth=2), AlphaBetaAgent(depth=2, ordering=True),
            AlphaBetaImprovedAgent(max_depth=2)]


# ------------------------------------------------- 1. minimax = alfa-beta en valor
@pytest.mark.parametrize("name", list(EQUIV_CASES))
@pytest.mark.parametrize("depth", [1, 2, 3])
def test_minimax_and_alphabeta_same_root_value(name, depth):
    board = chess.Board(EQUIV_CASES[name])
    before = _snapshot(board)
    mm = _minimax_root(EQUIV_CASES[name], depth)
    ab = search_root(board, "alphabeta", depth)
    abo = search_root(board, "alphabeta", depth, ordering=True)
    # EXACTAMENTE el mismo numero: mismas hojas, misma E, mismo max/min en la raiz.
    assert mm.value == ab.value == abo.value
    # Las jugadas pueden diferir por empate (pregunta 3), pero cada una debe alcanzar
    # el valor de la raiz: ninguna es peor, solo aparecio primero en otro orden.
    sign = 1 if board.turn == chess.WHITE else -1
    for res in (mm, ab, abo):
        assert res.move in board.legal_moves
        assert sign * _value_after(board, res.move, depth) == res.value
    # misma cantidad de trabajo o menos; con poda nunca mas nodos que minimax
    assert ab.stats.nodes <= mm.stats.nodes and abo.stats.nodes <= mm.stats.nodes
    assert mm.stats.cutoffs == 0
    assert _snapshot(board) == before


@pytest.mark.parametrize("name", ["poisoned"])
@pytest.mark.parametrize("depth", [1, 2])
def test_same_value_on_expensive_positions_shallow(name, depth):
    board = chess.Board(OWN[name])
    vals = {search_root(board, "minimax", depth).value,
            search_root(board, "alphabeta", depth).value,
            search_root(board, "alphabeta", depth, ordering=True).value}
    assert len(vals) == 1


def test_alphabeta_prunes_and_visits_fewer_nodes_at_depth_3():
    board = chess.Board(POSITIONS["initial"])
    mm = _minimax_root(POSITIONS["initial"], 3)
    ab = search_root(board, "alphabeta", 3)
    abo = search_root(board, "alphabeta", 3, ordering=True)
    assert ab.stats.cutoffs > 0 and ab.stats.nodes < mm.stats.nodes
    assert abo.stats.nodes < ab.stats.nodes           # ordenar ayuda en esta posicion
    assert abo.sort_time > 0 and ab.sort_time == 0
    # mismas definiciones: hojas <= nodos y la raiz cuenta como nodo
    for r in (mm, ab, abo):
        assert 0 < r.stats.leaves < r.stats.nodes
        assert r.stats.completed_depth == 3


def test_minimax_counts_every_node_of_the_full_tree():
    # A profundidad 2 desde la inicial: 1 raiz + 20 hijos + 400 nietos (todas hojas E).
    r = search_root(chess.Board(), "minimax", 2)
    assert (r.stats.nodes, r.stats.leaves) == (421, 400)


# ------------------------------------------------- 2. legalidad en no terminales
@pytest.mark.parametrize("fen", list(STATEMENT_NON_TERMINAL.values()) + list(OWN.values())
                         + [MINIMAX_DEFENSE_FEN])
def test_all_search_agents_return_legal_moves(fen):
    for agent in _all_agents():
        board = chess.Board(fen)
        d = agent.choose(board, time_limit_s=0, seed=0)
        assert d.move is not None and d.move in board.legal_moves, agent.name
        assert d.score is not None
        assert d.stats.nodes >= d.stats.leaves > 0


# ------------------------------------------------- 3. victoria inmediata y evasion
def test_every_agent_mates_in_one():
    for agent in _all_agents() + [MinimaxAgent(depth=1), AlphaBetaAgent(depth=3)]:
        board = chess.Board(POSITIONS["mate_in_one"])
        d = agent.choose(board, time_limit_s=0, seed=0)
        board.push(d.move)
        assert board.is_checkmate(), agent.name
        assert d.score == MATE_SCORE - 1               # gana a distancia 1 ply


def test_check_evasion_captures_the_checking_rook():
    for agent in _all_agents():
        board = chess.Board(OWN["evasion"])
        assert board.is_check()
        d = agent.choose(board, time_limit_s=0, seed=0)
        assert d.move == chess.Move.from_uci("h5e8"), agent.name
        board.push(d.move)
        assert not board.is_attacked_by(chess.BLACK, board.king(chess.WHITE))


# ------------------------------------------------- terminales: sin decision nueva
@pytest.mark.parametrize("name,expected", [("checkmate", -MATE_SCORE), ("stalemate", 0.0)])
def test_terminal_root_returns_none(name, expected):
    for agent in _all_agents():
        board = chess.Board(POSITIONS[name])
        before = _snapshot(board)
        d = agent.choose(board, time_limit_s=0, seed=0)
        assert d.move is None and d.score == expected     # utilidad de derrota para negras / tablas
        assert _snapshot(board) == before
    r = search_root(chess.Board(POSITIONS["checkmate"]), "alphabeta", 2)
    assert r.move is None and r.value == -MATE_SCORE


# ------------------------------------------------- 4. tablero e historia intactos
def _board_with_history():
    board = chess.Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]:
        board.push_uci(uci)
    return board


def test_board_and_history_intact_after_normal_search():
    for agent in _all_agents():
        board = _board_with_history()
        before = _snapshot(board)
        agent.choose(board, time_limit_s=0, seed=0)
        assert _snapshot(board) == before, agent.name


def test_board_intact_when_deadline_interrupts_deep_in_the_tree():
    board = _board_with_history()
    before = _snapshot(board)
    for fn in (lambda ctx: _search_minimax(board, 4, 0, ctx),
               lambda ctx: _search_alphabeta(board, 4, 0, -INF, INF, ctx)):
        ctx = SearchContext(DEFAULT_EVALUATOR, deadline=Deadline(0.02))
        with pytest.raises(SearchTimeout):
            fn(ctx)
        assert ctx.stats.nodes > 1                       # se corto a mitad del arbol
        assert _snapshot(board) == before


def test_board_intact_when_evaluator_raises():
    calls = {"n": 0}

    def broken(b):
        calls["n"] += 1
        if calls["n"] > 50:
            raise RuntimeError("fallo simulado de la evaluacion")
        return DEFAULT_EVALUATOR(b)

    board = _board_with_history()
    before = _snapshot(board)
    with pytest.raises(RuntimeError):
        AlphaBetaAgent(depth=3, evaluator=broken).choose(board, time_limit_s=0, seed=0)
    assert _snapshot(board) == before


def test_board_intact_after_improved_agent_times_out():
    board = _board_with_history()
    before = _snapshot(board)
    agent = AlphaBetaImprovedAgent(max_depth=10)
    d = agent.choose(board, time_limit_s=0.05, seed=0)
    assert _snapshot(board) == before
    assert agent.last_iterations and agent.last_iterations[-1]["completed"] is False
    assert d.move in board.legal_moves


# ------------------------------------------------- 6. profundizacion iterativa
def test_iterative_deepening_with_exhausted_budget_returns_fallback():
    board = chess.Board(POSITIONS["initial"])
    d = AlphaBetaImprovedAgent().choose(board, time_limit_s=1e-9, seed=0)
    assert d.move in board.legal_moves
    assert d.stats.completed_depth == 0 and d.score is None


def test_iterative_deepening_keeps_last_complete_iteration():
    board = chess.Board(INTERMEDIATE["minor_pieces"])
    agent = AlphaBetaImprovedAgent(max_depth=10)
    d = agent.choose(board, time_limit_s=0.15, seed=0)
    done = [r for r in agent.last_iterations if r["completed"]]
    assert d.stats.completed_depth == len(done) >= 1
    assert [r["depth"] for r in done] == list(range(1, len(done) + 1))
    assert d.move.uci() == done[-1]["move"]
    # coherencia: el valor es el de alfa-beta (= minimax) a la profundidad completada
    ref = search_root(board, "alphabeta", d.stats.completed_depth)
    assert d.score == ref.value
    assert sum(r["nodes"] for r in agent.last_iterations) == d.stats.nodes


def test_iterative_deepening_without_deadline_matches_minimax():
    board = chess.Board(INTERMEDIATE["knight_capture"])
    d = AlphaBetaImprovedAgent(max_depth=2).choose(board, time_limit_s=0, seed=0)
    assert d.stats.completed_depth == 2
    assert d.score == search_root(board, "minimax", 2).value


def test_iterative_deepening_stops_on_forced_mate():
    board = chess.Board(POSITIONS["mate_in_one"])
    agent = AlphaBetaImprovedAgent(max_depth=6)
    d = agent.choose(board, time_limit_s=5.0, seed=0)
    assert d.stats.completed_depth == 1 and d.score == MATE_SCORE - 1


# ------------------------------------------------- perspectiva
def test_black_to_move_chooses_what_is_good_for_black():
    for agent in _all_agents() + [MinimaxAgent(depth=1)]:
        board = chess.Board(OWN["black_capture"])
        d = agent.choose(board, time_limit_s=0, seed=0)
        assert d.move == chess.Move.from_uci("c3a4"), agent.name
        assert d.score > 200      # score desde negras: tras Cxa4 negras quedan con caballo de mas


def test_black_mates_in_one_on_mirrored_position():
    board = chess.Board(POSITIONS["mate_in_one"]).mirror()   # mismo problema, negras al turno
    for agent in _all_agents():
        b = board.copy()
        d = agent.choose(b, time_limit_s=0, seed=0)
        b.push(d.move)
        assert b.is_checkmate() and d.score == MATE_SCORE - 1


@pytest.mark.parametrize("fen", [OWN["poisoned"], INTERMEDIATE["knight_capture"],
                                 MINIMAX_DEFENSE_FEN])
def test_mirrored_position_gets_same_score_for_the_side_to_move(fen):
    board = chess.Board(fen)
    for algo, order in (("minimax", False), ("alphabeta", True)):
        a = search_root(board, algo, 2, ordering=order)
        b = search_root(board.mirror(), algo, 2, ordering=order)
        assert a.value == pytest.approx(b.value, abs=1e-9)


# ------------------------------------------------- posiciones propias
def test_mate_in_two_needs_depth_three():
    board = chess.Board(OWN["mate_in_two"])
    shallow = search_root(board, "minimax", 2)
    assert shallow.value < MATE_SCORE - 1000                 # a dos plies no lo ve
    for algo, order in (("minimax", False), ("alphabeta", False), ("alphabeta", True)):
        r = search_root(board, algo, 3, ordering=order)
        assert r.value == MATE_SCORE - 3                     # mate en 2 jugadas = 3 plies
        b = board.copy()
        b.push(r.move)
        # tras la jugada elegida, cualquier defensa negra permite mate inmediato
        for reply in list(b.legal_moves):
            b.push(reply)
            assert any(_gives_mate(b, m) for m in list(b.legal_moves))
            b.pop()
    d = AlphaBetaImprovedAgent(max_depth=5).choose(board, time_limit_s=0, seed=0)
    assert d.score == MATE_SCORE - 3 and d.stats.completed_depth == 3


def _gives_mate(board, move):
    board.push(move)
    try:
        return board.is_checkmate()
    finally:
        board.pop()


def test_poisoned_piece_greedy_takes_minimax_declines():
    board = chess.Board(OWN["poisoned"])
    greedy = MinimaxAgent(depth=1).choose(board, time_limit_s=0, seed=0)
    assert greedy.move == chess.Move.from_uci("d1d5")       # Dxd5?? exd5
    for agent in (MinimaxAgent(depth=2), AlphaBetaAgent(depth=2, ordering=True)):
        d = agent.choose(board, time_limit_s=0, seed=0)
        assert d.move != chess.Move.from_uci("d1d5")
        assert d.score > _value_after(board, chess.Move.from_uci("d1d5"), 2) + 500


def test_minimax_defense_example_question_1():
    board = chess.Board(MINIMAX_DEFENSE_FEN)
    greedy = MinimaxAgent(depth=1).choose(board, time_limit_s=0, seed=0)
    assert greedy.move.uci() == MINIMAX_DEFENSE_GREEDY_MOVE
    mm = MinimaxAgent(depth=2).choose(board, time_limit_s=0, seed=0)
    assert mm.move.uci() in MINIMAX_DEFENSE_MOVES
    # tras Dxh5 la respuesta exd4 gana el caballo: minimax lo ve, el voraz no
    blunder = _value_after(board, chess.Move.from_uci(MINIMAX_DEFENSE_GREEDY_MOVE), 2)
    assert mm.score - blunder > 200
    assert greedy.score > mm.score     # el voraz es "optimista": no mira la respuesta


# ------------------------------------------------- registro de podas (pregunta 2)
def test_prune_log_events_are_valid_cutoffs():
    board = chess.Board(MINIMAX_DEFENSE_FEN)
    agent = AlphaBetaAgent(depth=3, log_prunes=True, max_log=10_000)
    d = agent.choose(board, time_limit_s=0, seed=0)
    log = agent.last_prune_log
    assert len(log) == d.stats.cutoffs > 0
    assert sum(len(ev.pruned) for ev in log) == agent.last_pruned_children
    for ev in log:
        assert ev.pruned and ev.explored and ev.explored[-1][0] == ev.cause
        if ev.node_type == "MAX":
            assert ev.value >= ev.beta
        else:
            assert ev.value <= ev.alpha
        node = chess.Board(ev.fen)
        assert (node.turn == chess.WHITE) == (ev.node_type == "MAX")
    assert "podados" in format_prune_event(log[0])
    # el registro no altera la busqueda
    plain = AlphaBetaAgent(depth=3).choose(board, time_limit_s=0, seed=0)
    assert (plain.score, plain.move, plain.stats.nodes) == (d.score, d.move, d.stats.nodes)


# ------------------------------------------------- quietud (opcional, no oficial)
def test_quiescence_flag_keeps_contract():
    board = chess.Board(INTERMEDIATE["knight_capture"])
    before = _snapshot(board)
    agent = AlphaBetaImprovedAgent(max_depth=2, quiescence=True)
    d = agent.choose(board, time_limit_s=0, seed=0)
    assert d.move in board.legal_moves and _snapshot(board) == before
    assert d.stats.completed_depth == 2
    plain = AlphaBetaImprovedAgent(max_depth=2).choose(board, time_limit_s=0, seed=0)
    assert d.stats.nodes > plain.stats.nodes          # el arbol ya no es el mismo



def test_greedy_trap_of_agents_basic_is_avoided_by_minimax():
    """Cruce con el modulo del voraz: minimax depth 1 = voraz; depth 2 evita Dxb7?? Te1#."""
    try:
        from chess_ai.agents_basic import GREEDY_TRAP_FEN, GREEDY_TRAP_GREEDY_MOVE, GreedyAgent
    except ImportError:
        pytest.skip("agents_basic.GREEDY_TRAP_FEN aun no existe")
    board = chess.Board(GREEDY_TRAP_FEN)
    g = GreedyAgent().choose(board, time_limit_s=0, seed=0)
    m1 = MinimaxAgent(depth=1).choose(board, time_limit_s=0, seed=0)
    assert (m1.move, m1.score) == (g.move, g.score)        # el voraz es minimax de 1 ply
    for agent in (MinimaxAgent(depth=2), AlphaBetaAgent(depth=2, ordering=True)):
        assert agent.choose(board, time_limit_s=0, seed=0).move.uci() != GREEDY_TRAP_GREEDY_MOVE
