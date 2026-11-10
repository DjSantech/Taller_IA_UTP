import chess
import pytest

from conftest import POSITIONS
from chess_ai.environment import (MATE_SCORE, EVAL_BOUND, ChessEnvironment, Deadline,
                                  IllegalMoveError, SearchTimeout, game_outcome,
                                  search_outcome, terminal_value_white, perspective_sign)
from chess_ai.evaluation import evaluate, features, Evaluator


# ---------------------------------------------------------------- entorno
def test_initial_has_20_moves():
    assert chess.Board(POSITIONS["initial"]).legal_moves.count() == 20


def test_special_rules_from_statement():
    b = chess.Board(POSITIONS["castling"])
    assert chess.Move.from_uci("e1g1") in b.legal_moves and chess.Move.from_uci("e1c1") in b.legal_moves
    b = chess.Board(POSITIONS["promotion"])
    assert sum(1 for m in b.legal_moves if m.from_square == chess.A7 and m.promotion) == 4
    b = chess.Board(POSITIONS["en_passant"])
    assert b.is_en_passant(chess.Move.from_uci("e5d6"))


def test_terminal_positions_agree_between_game_and_search_policy():
    for name in ("checkmate", "stalemate"):
        b = chess.Board(POSITIONS[name])
        g, s = game_outcome(b), search_outcome(b)
        assert g is not None and s is not None
        assert g.termination == s.termination and g.winner == s.winner
    assert search_outcome(chess.Board(POSITIONS["checkmate"])).winner == chess.WHITE
    assert search_outcome(chess.Board(POSITIONS["stalemate"])).winner is None


def test_repetition_is_detected_from_history_not_from_fen():
    b = chess.Board()
    for uci in ["g1f3", "g8f6", "f3g1", "f6g8"] * 2:
        b.push_uci(uci)
    # posicion inicial repetida 3 veces: la historia lo revela, el FEN aislado no
    assert search_outcome(b).termination == chess.Termination.THREEFOLD_REPETITION
    assert game_outcome(b) is not None
    assert search_outcome(chess.Board(b.fen())) is None


def test_terminal_utilities_dominate_estimates_and_prefer_short_mates():
    win = chess.Outcome(chess.Termination.CHECKMATE, chess.WHITE)
    loss = chess.Outcome(chess.Termination.CHECKMATE, chess.BLACK)
    assert terminal_value_white(win, 1) > terminal_value_white(win, 5) > EVAL_BOUND
    assert terminal_value_white(loss, 3) < -EVAL_BOUND
    assert terminal_value_white(chess.Outcome(chess.Termination.STALEMATE, None), 2) == 0
    assert perspective_sign(chess.BLACK) * terminal_value_white(loss, 1) == MATE_SCORE - 1


def test_environment_rejects_illegal_and_keeps_state():
    env = ChessEnvironment()
    fen, v = env.board.fen(), env.version
    with pytest.raises(IllegalMoveError):
        env.apply(chess.Move.from_uci("e7e5"))      # pieza negra en turno de blancas
    assert env.board.fen() == fen and env.version == v
    env.apply(chess.Move.from_uci("e2e4"))
    assert env.board.turn == chess.BLACK and env.version == v + 1
    assert env.undo(1) == 1 and env.board.fen() == fen


def test_terminal_game_accepts_no_moves_and_truncation_is_not_a_draw():
    env = ChessEnvironment(POSITIONS["checkmate"])
    assert env.status() == "terminal" and env.official_result() == "1-0"
    with pytest.raises(IllegalMoveError):
        env.apply(next(iter(chess.Board().legal_moves)))
    env = ChessEnvironment(max_plies=2)
    env.apply(chess.Move.from_uci("e2e4")); env.apply(chess.Move.from_uci("e7e5"))
    assert env.status() == "truncated" and env.official_result() == "*"
    assert env.to_pgn().headers["Result"] == "*"


def test_copy_for_agent_keeps_stack_and_is_independent():
    env = ChessEnvironment()
    env.apply(chess.Move.from_uci("e2e4"))
    c = env.copy_for_agent()
    assert c.move_stack == env.board.move_stack
    c.push_uci("e7e5")
    assert len(env.board.move_stack) == 1


def test_deadline():
    d = Deadline(None)
    assert not d.expired()
    d = Deadline(1e-9)
    while not d.expired():
        pass
    with pytest.raises(SearchTimeout):
        d.check()


# ---------------------------------------------------------------- evaluacion
def test_initial_position_is_balanced():
    assert evaluate(chess.Board()) == pytest.approx(0.0)


def test_evaluation_is_antisymmetric_under_color_mirror():
    for fen in ["r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
                "8/5pk1/6p1/8/3P4/8/5PPP/6K1 w - - 0 1",
                POSITIONS["castling"], POSITIONS["promotion"]]:
        b = chess.Board(fen)
        assert evaluate(b.mirror()) == pytest.approx(-evaluate(b))


def test_material_sign_and_black_perspective():
    b = chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")    # blancas con dama de mas
    assert features(b)[0] == pytest.approx(9.0)
    assert evaluate(b) > 0
    assert perspective_sign(chess.BLACK) * evaluate(b) < 0   # para negras es malo


def test_evaluation_bounded_and_evaluator_class():
    b = chess.Board("QQQQKQQQ/QQQQQQQQ/8/8/8/8/8/7k w - - 0 1")
    assert abs(evaluate(b)) <= EVAL_BOUND
    ev = Evaluator((1, 0, 0, 0), "solo_material")
    assert ev(chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")) == pytest.approx(9.0)
