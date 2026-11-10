import collections

import chess
import pytest

from conftest import POSITIONS
from chess_ai.agents_basic import (GREEDY_TRAP_FEN, GREEDY_TRAP_GREEDY_MOVE,
                                   GREEDY_TRAP_REFUTATION, GreedyAgent, RandomAgent)
from chess_ai.contract import Decision
from chess_ai.environment import MATE_SCORE, search_outcome

NON_TERMINAL = [n for n, fen in POSITIONS.items() if search_outcome(chess.Board(fen)) is None]
AGENTS = [RandomAgent, GreedyAgent]

# Posicion propia: negras pueden capturar la dama blanca con el caballo (Cxd5).
# Los peones evitan que tras la captura quede material insuficiente.
BLACK_WINS_QUEEN_FEN = "4k3/p7/8/3Q4/8/2n5/7P/4K3 b - - 0 1"


def _board_with_history() -> chess.Board:
    b = chess.Board()
    for uci in ("e2e4", "e7e5", "g1f3", "b8c6"):
        b.push_uci(uci)
    return b


@pytest.mark.parametrize("agent_cls", AGENTS)
@pytest.mark.parametrize("name", NON_TERMINAL)
def test_legal_move_in_every_non_terminal_position(agent_cls, name):
    board = chess.Board(POSITIONS[name])
    for seed in range(5):
        d = agent_cls().choose(board, time_limit_s=0.0, seed=seed)
        assert isinstance(d, Decision)
        assert d.move in board.legal_moves


@pytest.mark.parametrize("agent_cls", AGENTS)
def test_terminal_positions_return_none_with_exact_utility(agent_cls):
    mate = agent_cls().choose(chess.Board(POSITIONS["checkmate"]), time_limit_s=0.0, seed=1)
    assert mate.move is None and mate.score == -MATE_SCORE   # derrota de negras, que deciden
    stale = agent_cls().choose(chess.Board(POSITIONS["stalemate"]), time_limit_s=0.0, seed=1)
    assert stale.move is None and stale.score == 0


@pytest.mark.parametrize("agent_cls", AGENTS)
def test_same_seed_same_move(agent_cls):
    board = _board_with_history()
    moves = {agent_cls().choose(board, time_limit_s=0.0, seed=123).move for _ in range(5)}
    assert len(moves) == 1


def test_random_agent_depends_on_seed_and_covers_all_moves():
    board = chess.Board()
    counts = collections.Counter(RandomAgent().choose(board, time_limit_s=0.0, seed=s).move.uci()
                                 for s in range(2000))
    assert len(counts) == 20                       # las 20 jugadas iniciales aparecen
    assert max(counts.values()) < 3 * min(counts.values())   # aproximadamente uniforme (esperado 100)


@pytest.mark.parametrize("agent_cls", AGENTS)
def test_board_and_history_are_left_intact(agent_cls):
    board = _board_with_history()
    fen, stack = board.fen(), list(board.move_stack)
    agent_cls().choose(board, time_limit_s=0.0, seed=7)
    assert board.fen() == fen and board.move_stack == stack


def test_greedy_restores_board_even_if_evaluator_fails():
    def broken(_board):
        raise RuntimeError("evaluador roto a proposito")
    board = _board_with_history()
    fen, stack = board.fen(), list(board.move_stack)
    with pytest.raises(RuntimeError):
        GreedyAgent(broken).choose(board, time_limit_s=0.0, seed=0)
    assert board.fen() == fen and board.move_stack == stack


def test_greedy_takes_mate_in_one():
    board = chess.Board(POSITIONS["mate_in_one"])
    for seed in range(5):
        d = GreedyAgent().choose(board, time_limit_s=0.0, seed=seed)
        board.push(d.move)
        assert board.is_checkmate()
        board.pop()
        assert d.score == MATE_SCORE - 1           # victoria a distancia 1


def test_greedy_as_black_chooses_what_is_good_for_black():
    board = chess.Board(BLACK_WINS_QUEEN_FEN)
    d = GreedyAgent().choose(board, time_limit_s=0.0, seed=0)
    assert d.move.uci() == "c3d5"                  # Cxd5: gana la dama
    assert d.score > 0                             # positivo desde negras, que deciden


def test_greedy_stats_definitions():
    board = chess.Board()
    d = GreedyAgent().choose(board, time_limit_s=0.0, seed=0)
    assert d.stats.nodes == d.stats.leaves == 20
    assert d.stats.completed_depth == 1 and d.stats.cutoffs == 0 and d.stats.simulations == 0
    r = RandomAgent().choose(board, time_limit_s=0.0, seed=0)
    assert r.stats.nodes == 0 and r.stats.leaves == 0 and r.score is None


def test_greedy_returns_legal_move_when_deadline_expires():
    board = chess.Board()
    d = GreedyAgent().choose(board, time_limit_s=1e-9, seed=0)
    assert d.move in board.legal_moves
    assert d.stats.nodes == 1 and d.stats.completed_depth == 0


def test_greedy_accepts_plain_function_as_evaluator():
    board = chess.Board(BLACK_WINS_QUEEN_FEN)
    d = GreedyAgent(lambda b: 0.0).choose(board, time_limit_s=0.0, seed=3)
    assert d.move in board.legal_moves and d.score == 0.0


def test_greedy_falls_into_back_rank_trap():
    """Pregunta 1: el voraz gana un peon y recibe mate; un ply no ve la respuesta."""
    board = chess.Board(GREEDY_TRAP_FEN)
    for seed in range(5):
        d = GreedyAgent().choose(board, time_limit_s=0.0, seed=seed)
        assert d.move.uci() == GREEDY_TRAP_GREEDY_MOVE
        assert d.score > 0                         # el voraz cree que va ganando
    board.push_uci(GREEDY_TRAP_GREEDY_MOVE)
    board.push_uci(GREEDY_TRAP_REFUTATION)
    assert board.is_checkmate()                    # ...y negras dan mate
