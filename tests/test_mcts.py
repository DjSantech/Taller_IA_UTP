"""Pruebas del agente MCTS-UCT (chess_ai/mcts.py). Prefijo de bitacora: M-."""
import math

import chess
import pytest

from conftest import POSITIONS
from chess_ai.environment import EVAL_BOUND, MATE_SCORE
from chess_ai.mcts import (MCTS_TACTICS, MCTSAgent, _mcts_logit_cp, _mcts_sigmoid,
                           mcts_benchmark_summary, mcts_non_monotonic_cases,
                           mcts_tactics_benchmark, mcts_verify_tactics)

NON_TERMINAL = [k for k in POSITIONS if k not in ("checkmate", "stalemate")]
TACTIC = {t["id"]: t for t in MCTS_TACTICS}


class _WhitePerspectiveMCTS(MCTSAgent):
    """Variante con el ERROR de la pregunta 6: todos los nodos guardan W desde blancas,
    asi que en los nodos de negras UCT maximiza para blancas."""

    def _reward_for(self, mover, reward_white):
        return reward_white


# ------------------------------------------------------------------ legalidad y terminales
@pytest.mark.parametrize("name", NON_TERMINAL)
def test_legal_move_in_non_terminal_positions(name):
    board = chess.Board(POSITIONS[name])
    d = MCTSAgent(simulations=60).choose(board, time_limit_s=0, seed=3)
    assert d.move in board.legal_moves
    assert d.stats.simulations == 60 and d.stats.leaves == 60
    assert d.stats.nodes >= 2 and d.stats.completed_depth >= 1
    assert isinstance(d.score, float)
    assert abs(d.score) <= EVAL_BOUND or d.score == MATE_SCORE - 1   # hijo terminal = mate


@pytest.mark.parametrize("name,expected", [("checkmate", -MATE_SCORE), ("stalemate", 0.0)])
def test_terminal_returns_none(name, expected):
    board = chess.Board(POSITIONS[name])
    d = MCTSAgent(simulations=50).choose(board, time_limit_s=0, seed=0)
    assert d.move is None
    assert d.score == expected            # derrota de negras desde negras / tablas


# ------------------------------------------------------------------ reproducibilidad
def test_same_seed_same_simulations_is_reproducible():
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3")
    runs = []
    for _ in range(2):
        agent = MCTSAgent(simulations=150)
        d = agent.choose(board.copy(stack=True), time_limit_s=0, seed=11)
        runs.append((d.move, d.score, d.stats.nodes, agent.last_info["root_visits"]))
    assert runs[0] == runs[1]
    other = MCTSAgent(simulations=150)
    other.choose(board.copy(stack=True), time_limit_s=0, seed=12)
    # otra semilla cambia el orden de expansion (y, en general, las visitas)
    assert other.last_info["root_visits"] != runs[0][3]


def test_fixed_simulations_ignore_wall_clock():
    """Con simulaciones fijas el plazo no corta: la reproducibilidad no depende de la maquina."""
    d = MCTSAgent(simulations=40).choose(chess.Board(), time_limit_s=1e-9, seed=0)
    assert d.stats.simulations == 40


# ------------------------------------------------------------------ tablero intacto
def test_board_and_history_untouched():
    board = chess.Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]:
        board.push_uci(uci)
    fen, stack = board.fen(), list(board.move_stack)
    for restore in ("push_pop", "copy"):
        MCTSAgent(simulations=80, restore=restore).choose(board, time_limit_s=0, seed=1)
        assert board.fen() == fen and board.move_stack == stack


def test_board_untouched_when_evaluator_raises():
    calls = {"n": 0}

    def exploding(board):
        calls["n"] += 1
        if calls["n"] == 5:
            raise RuntimeError("fallo inyectado en mitad de un rollout")
        return 0.0

    board = chess.Board()
    board.push_uci("d2d4")
    fen, stack = board.fen(), list(board.move_stack)
    with pytest.raises(RuntimeError):
        MCTSAgent(simulations=50, evaluator=exploding, rollout_limit=6).choose(
            board, time_limit_s=0, seed=0)
    assert board.fen() == fen and board.move_stack == stack


# ------------------------------------------------------------------ tactica
@pytest.mark.parametrize("seed", range(3))
def test_mate_in_one_with_enough_budget(seed):
    board = chess.Board(POSITIONS["mate_in_one"])
    agent = MCTSAgent(simulations=200)
    d = agent.choose(board, time_limit_s=0, seed=seed)
    board.push(d.move)
    assert board.is_checkmate()
    assert agent.last_info["win_probability"] == 1.0 and d.score == MATE_SCORE - 1


def test_tactics_solutions_verified_by_rules():
    assert len(MCTS_TACTICS) >= 6
    assert mcts_verify_tactics() == []


# ------------------------------------------------------------------ perspectiva (pregunta 6)
@pytest.mark.parametrize("tactic", ["T3_mate1_b_backrank", "T6_queen_b"])
def test_black_to_move_correct_perspective_vs_white_perspective_bug(tactic):
    """Negras al turno: la convencion correcta acierta y la variante que guarda W desde
    blancas (maximiza para el jugador equivocado) falla en las mismas semillas."""
    t = TACTIC[tactic]
    for seed in range(3):
        good = MCTSAgent(simulations=300).choose(chess.Board(t["fen"]), time_limit_s=0, seed=seed)
        bad = _WhitePerspectiveMCTS(simulations=300).choose(chess.Board(t["fen"]), time_limit_s=0,
                                                           seed=seed)
        assert good.move.uci() in t["solutions"]
        assert bad.move.uci() not in t["solutions"]


def test_each_node_stores_value_of_the_player_who_moved():
    board = chess.Board(TACTIC["T3_mate1_b_backrank"]["fen"])     # negras al turno
    agent = MCTSAgent(simulations=300)
    d = agent.choose(board, time_limit_s=0, seed=0)
    root = agent.last_root
    stack = [(root, board.copy(stack=True))]
    while stack:                                   # recorre el arbol rehaciendo jugadas
        node, b = stack.pop()
        for child in node.children:
            assert child.mover == b.turn           # quien mueve en el padre "posee" el hijo
            nb = b.copy(stack=False)
            nb.push(child.move)
            stack.append((child, nb))
    mate = next(c for c in root.children if c.move.uci() == "a8a1")
    assert mate.mover == chess.BLACK and mate.mean() == 1.0   # victoria de negras = 1
    assert d.move.uci() == "a8a1" and d.score > 0              # score desde negras


# ------------------------------------------------------------------ rollouts truncados
def test_truncated_rollout_is_counted_as_truncated_not_draw():
    board = chess.Board(POSITIONS["initial"])
    agent = MCTSAgent(simulations=30, rollout_limit=2)
    agent.choose(board, time_limit_s=0, seed=0)
    info = agent.last_info
    assert info["truncated_rollouts"] == 30 and info["terminal_rollouts"] == 0
    # una recompensa truncada no es 0.5 "por tablas": es la sigmoide de E
    assert _mcts_sigmoid(0.0) == 0.5 and _mcts_sigmoid(900.0) == pytest.approx(0.905, abs=1e-3)
    assert _mcts_logit_cp(_mcts_sigmoid(250.0)) == pytest.approx(250.0)


def test_terminal_rollouts_are_counted_separately():
    agent = MCTSAgent(simulations=200)
    agent.choose(chess.Board(POSITIONS["mate_in_one"]), time_limit_s=0, seed=0)
    info = agent.last_info
    assert info["terminal_rollouts"] > 0
    assert info["terminal_rollouts"] + info["truncated_rollouts"] == 200


# ------------------------------------------------------------------ plazo
def test_time_budget_returns_legal_move():
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3")
    agent = MCTSAgent(simulations=None)
    d = agent.choose(board, time_limit_s=0.05, seed=0)
    assert d.move in board.legal_moves
    assert d.stats.simulations > 0 and agent.last_info["budget_mode"] == "time"
    assert d.stats.elapsed_s < 0.05 + 0.25          # una simulacion de mas como mucho


def test_tiny_deadline_still_returns_legal_move():
    board = chess.Board()
    d = MCTSAgent(simulations=None).choose(board, time_limit_s=1e-9, seed=0)
    assert d.move in board.legal_moves and math.isfinite(d.score)


# ------------------------------------------------------------------ benchmark
def test_benchmark_rows_and_summary_shape():
    rows = mcts_tactics_benchmark(MCTS_TACTICS[:2], budgets=(10, 30), seeds=range(2),
                                  label="smoke")
    assert len(rows) == 2 * 2 * 2
    assert {"config", "tactic", "budget", "seed", "correct", "elapsed_s"} <= set(rows[0])
    summary = mcts_benchmark_summary(rows)
    assert [s["budget"] for s in summary] == [10, 30]
    assert all(0.0 <= s["hit_rate"] <= 1.0 for s in summary)
    fake = [dict(config="c", tactic="t", seed=0, budget=b, correct=c)
            for b, c in ((1, 1), (2, 0), (3, 1))]
    assert mcts_non_monotonic_cases(fake) == [("c", "t", 0, [1, 0, 1])]
