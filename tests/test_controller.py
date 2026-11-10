"""Pruebas del controlador (seccion 6) y prueba de humo de la interfaz.

Los agentes reales los escriben otros modulos; aqui se usan agentes "stub"
definidos en la prueba para aislar la logica de turnos.
"""
import asyncio
import csv
import io
import random
import time

import chess
import chess.pgn
import pytest

from conftest import POSITIONS
from chess_ai.contract import Decision, SearchStats
from chess_ai.controller import (CSV_FIELDS, HUMAN_LABEL, AgentConfig, GameController,
                                 build_agent)
from chess_ai.environment import ChessEnvironment


# ------------------------------------------------------------------ stubs
class RandomStub:
    """Aleatorio simple y reproducible; anota color, semilla y tablero recibidos."""

    def __init__(self, name="Stub", color=None, sleep_s=0.0):
        self.name, self.color, self.sleep_s = name, color, sleep_s
        self.calls, self.seeds, self.boards = 0, [], []

    def choose(self, board, *, time_limit_s, seed):
        self.calls += 1
        self.seeds.append(seed)
        self.boards.append(board)
        if self.color is not None:
            assert board.turn == self.color, "se pidio jugada al agente del color equivocado"
        if self.sleep_s:
            time.sleep(self.sleep_s)
        moves = sorted(board.legal_moves, key=lambda m: m.uci())
        move = random.Random(seed).choice(moves)
        return Decision(move, 0.0, SearchStats(nodes=len(moves), leaves=len(moves),
                                               completed_depth=1, elapsed_s=0.0))


class IllegalStub:
    name = "Ilegal"

    def choose(self, board, *, time_limit_s, seed):
        return Decision(chess.Move(chess.E2, chess.E5), 0.0, SearchStats())


class NoneStub:
    name = "Nulo"

    def choose(self, board, *, time_limit_s, seed):
        return Decision(None, None, SearchStats())


class CrashStub:
    name = "Falla"

    def choose(self, board, *, time_limit_s, seed):
        raise RuntimeError("boom")


class SlowStub:
    name = "Lento"

    def choose(self, board, *, time_limit_s, seed):
        time.sleep(time_limit_s * 3)
        return Decision(next(iter(board.legal_moves)), 0.0, SearchStats(completed_depth=4))


class MutatingStub:
    """Simula un cambio del estado real mientras el agente 'piensa'."""
    name = "Mutador"

    def __init__(self, env):
        self.env = env

    def choose(self, board, *, time_limit_s, seed):
        self.env.apply(chess.Move.from_uci("e2e4"))     # alguien cambio el tablero real
        return Decision(chess.Move.from_uci("d2d4"), 0.0, SearchStats())


class CallbackStub(RandomStub):
    """Ejecuta `hook(controller)` durante choose() (reentrada / pausa)."""

    def __init__(self, hook, **kw):
        super().__init__(**kw)
        self.hook, self.results = hook, []

    def choose(self, board, *, time_limit_s, seed):
        self.results.append(self.hook())
        return super().choose(board, time_limit_s=time_limit_s, seed=seed)


def make(white=None, black=None, fen=None, max_plies=None, **cfg):
    env = ChessEnvironment(fen, max_plies=max_plies)
    config = AgentConfig(**{"time_limit_s": 0.0, **cfg})
    return env, GameController(env, white, black, config)


# --------------------------------------------------------- alternancia
def test_turns_alternate_and_each_request_applies_exactly_one_move():
    w, b = RandomStub("W", chess.WHITE), RandomStub("B", chess.BLACK)
    env, ctl = make(w, b)
    for i in range(12):
        v = env.version
        rep = ctl.request_turn()
        assert rep.status == "applied"
        assert env.ply_count == i + 1 and env.version == v + 1   # exactamente una jugada
    assert (w.calls, b.calls) == (6, 6)
    assert [r.color for r in ctl.records] == ["white", "black"] * 6
    assert [r.ply for r in ctl.records] == list(range(1, 13))


def test_agent_receives_copy_with_history_not_the_real_board():
    w, b = RandomStub("W"), RandomStub("B")
    env, ctl = make(w, b)
    ctl.request_turn(); ctl.request_turn(); ctl.request_turn()
    seen = b.boards[-1]
    assert seen is not env.board and len(seen.move_stack) == 1      # historia conservada


def test_seed_policy_is_seed_base_plus_ply():
    w, b = RandomStub("W"), RandomStub("B")
    env, ctl = make(w, b, seed=100)
    for _ in range(6):
        ctl.request_turn()
    assert w.seeds == [100, 102, 104] and b.seeds == [101, 103, 105]
    assert [r.seed for r in ctl.records] == [100, 101, 102, 103, 104, 105]


def test_same_seed_reproduces_the_game():
    games = []
    for _ in range(2):
        env, ctl = make(RandomStub("W"), RandomStub("B"), seed=7)
        ctl.play_until_stop(max_turns=20)
        games.append([m.uci() for m in env.board.move_stack])
    assert games[0] == games[1] and len(games[0]) == 20


# ------------------------------------------------------ jugadas invalidas
@pytest.mark.parametrize("stub", [IllegalStub(), NoneStub(), CrashStub()])
def test_invalid_agent_output_does_not_change_state(stub):
    env, ctl = make(stub, None)
    fen, version = env.board.fen(), env.version
    rep = ctl.request_turn()
    assert rep.status == "error"
    assert env.board.fen() == fen and env.version == version and ctl.records == []
    assert ctl.errors and ctl.searching is False


def test_stale_decision_is_discarded():
    env = ChessEnvironment()
    ctl = GameController(env, None, None, AgentConfig(time_limit_s=0))
    ctl.set_agents(MutatingStub(env), None)
    rep = ctl.request_turn()
    assert rep.status == "stale"
    # solo quedo el cambio externo (e2e4); d2d4 del agente NO se aplico
    assert [m.uci() for m in env.board.move_stack] == ["e2e4"]
    assert ctl.records == []


def test_reentrant_request_during_search_is_busy():
    holder = {}
    stub = CallbackStub(lambda: holder["ctl"].request_turn().status, name="R")
    env, ctl = make(stub, stub)
    holder["ctl"] = ctl
    assert ctl.request_turn().status == "applied"
    assert stub.results == ["busy"] and env.ply_count == 1


def test_slow_agent_is_flagged_but_move_applied():
    env, ctl = make(SlowStub(), None, time_limit_s=0.05)
    ctl.tolerance_s = 0.02
    rep = ctl.request_turn()
    assert rep.status == "applied" and rep.record.time_exceeded
    assert rep.record.elapsed_s >= 0.15 and env.ply_count == 1


def test_fast_agent_not_flagged_and_no_budget_never_flags():
    env, ctl = make(RandomStub(), RandomStub(), time_limit_s=1.0)
    assert ctl.request_turn().record.time_exceeded is False
    env, ctl = make(SlowStub(), None, time_limit_s=0.0)   # sin plazo
    assert ctl.request_turn().record.time_exceeded is False


# ------------------------------------------------------- terminales
@pytest.mark.parametrize("name", ["checkmate", "stalemate"])
def test_terminal_game_never_asks_the_agent(name):
    stub = RandomStub()
    env, ctl = make(stub, stub, fen=POSITIONS[name])
    assert ctl.request_turn().status == "over"
    assert stub.calls == 0 and env.ply_count == 0


def test_truncation_at_max_plies():
    stub = RandomStub()
    env, ctl = make(stub, stub, max_plies=6)
    reason = ctl.play_until_stop()
    assert reason == "truncated" and env.ply_count == 6 and env.status() == "truncated"
    assert ctl.request_turn().status == "over" and stub.calls == 6
    game = chess.pgn.read_game(io.StringIO(ctl.export_pgn()))
    assert game.headers["Result"] == "*" and game.headers["Termination"] == "truncated"


def test_mate_reached_by_agent_stops_the_loop():
    class Mate:
        name = "Mate"

        def choose(self, board, *, time_limit_s, seed):
            for m in board.legal_moves:
                board.push(m)
                mate = board.is_checkmate()
                board.pop()
                if mate:
                    return Decision(m, 1e5, SearchStats())
            return Decision(next(iter(board.legal_moves)), 0.0, SearchStats())

    env, ctl = make(Mate(), RandomStub(), fen=POSITIONS["mate_in_one"])
    assert ctl.play_until_stop() == "terminal"
    assert env.official_result() == "1-0" and ctl.records[-1].termination == "checkmate"


# ------------------------------------------------------- humano
def test_human_moves_validated_and_turn_enforced():
    env, ctl = make(None, RandomStub("B"))
    assert ctl.request_turn().status == "human"
    rep = ctl.human_move(chess.Move.from_uci("e7e5"))        # pieza negra en turno blanco
    assert rep.status == "rejected" and env.ply_count == 0
    assert ctl.human_move("e2e4").status == "applied"
    v = env.version
    assert ctl.human_move("d2d4").status == "rejected"         # le toca al agente
    assert env.version == v
    assert ctl.request_turn().status == "applied" and env.ply_count == 2
    assert ctl.records[0].agent == HUMAN_LABEL and ctl.records[1].agent == "B"


def test_human_human_mode_plays_statement_manual_test():
    env, ctl = make(None, None)
    for uci in ["e2e4", "e7e5", "g1f3"]:
        assert ctl.human_move(uci).status == "applied"
    fen = env.board.fen()
    assert ctl.human_move("d2d4").status == "rejected"         # pieza blanca en turno negro
    assert env.board.fen() == fen
    assert env.san_history() == ["e4", "e5", "Nf3"]


def test_promotion_from_loaded_position():
    env, ctl = make(None, None)
    assert ctl.new_game(POSITIONS["promotion"]).status == "reset"
    assert ctl.human_move("a7a8").status == "rejected"         # falta la pieza de promocion
    assert ctl.human_move("a7a8n").status == "applied"
    assert env.board.piece_at(chess.A8) == chess.Piece(chess.KNIGHT, chess.WHITE)


# ------------------------------------------------------- deshacer
def test_undo_human_vs_agent_returns_to_human_turn():
    env, ctl = make(None, RandomStub("B"))
    ctl.human_move("e2e4"); ctl.request_turn()
    assert ctl.undo().status == "undone"
    assert env.ply_count == 0 and env.board.turn == chess.WHITE and ctl.records == []
    # si el agente aun no respondio, se deshace solo la jugada humana
    ctl.human_move("e2e4")
    ctl.undo()
    assert env.ply_count == 0 and env.board.turn == chess.WHITE


def test_undo_when_agent_plays_white():
    env, ctl = make(RandomStub("W"), None)
    ctl.request_turn(); ctl.human_move(next(iter(env.board.legal_moves))); ctl.request_turn()
    assert env.ply_count == 3
    ctl.undo()                                                 # vuelve al turno de negras (humano)
    assert env.ply_count == 1 and env.board.turn == chess.BLACK and len(ctl.records) == 1


@pytest.mark.parametrize("players", ["hh", "aa"])
def test_undo_one_ply_in_other_modes(players):
    a = (lambda: RandomStub()) if players == "aa" else (lambda: None)
    env, ctl = make(a(), a())
    for uci in ["e2e4", "e7e5", "g1f3"]:
        if players == "hh":
            ctl.human_move(uci)
        else:
            ctl.request_turn()
    ctl.undo()
    assert env.ply_count == 2 and len(ctl.records) == 2


def test_undo_forbidden_during_search_and_running_loop():
    holder = {}
    stub = CallbackStub(lambda: holder["ctl"].undo().status, name="U")
    env, ctl = make(stub, stub)
    holder["ctl"] = ctl
    ctl.request_turn()
    assert stub.results == ["busy"] and env.ply_count == 1
    ctl.running = True
    assert ctl.undo().status == "busy" and env.ply_count == 1
    ctl.running = False
    assert ctl.undo().status == "undone" and env.ply_count == 0


def test_new_game_and_change_agents():
    env, ctl = make(RandomStub(), RandomStub())
    ctl.play_until_stop(max_turns=4)
    assert ctl.new_game().status == "reset"
    assert env.ply_count == 0 and ctl.records == [] and ctl.game_id == "gui-002"
    assert ctl.new_game("not a fen").status == "rejected"
    ctl.set_agents(None, RandomStub())
    assert ctl.mode() == "humano-agente"


def test_build_agent_uses_factories_and_human_is_none():
    cfg = AgentConfig(depth=3, time_limit_s=0.1, seed=5, simulations=200)
    factories = {HUMAN_LABEL: None, "Stub": lambda c: RandomStub(f"Stub d{c.depth}")}
    assert build_agent(factories, HUMAN_LABEL, cfg) is None
    assert build_agent(factories, "Stub", cfg).name == "Stub d3"
    with pytest.raises(KeyError):
        build_agent(factories, "Nadie", cfg)


# ------------------------------------------------------- exportacion
def test_csv_has_exactly_statement_columns():
    env, ctl = make(RandomStub("W"), RandomStub("B"), max_plies=4)
    ctl.play_until_stop()
    rows = list(csv.reader(io.StringIO(ctl.export_csv())))
    assert rows[0] == CSV_FIELDS == ["game_id", "opening_id", "seed", "white_agent",
                                     "black_agent", "ply", "move_uci", "nodes", "leaves",
                                     "cutoffs", "completed_depth", "elapsed_s", "simulations",
                                     "time_exceeded", "termination", "official_result"]
    assert len(rows) == 5
    data = list(csv.DictReader(io.StringIO(ctl.export_csv())))
    assert {r["termination"] for r in data} == {"truncated"}
    assert {r["official_result"] for r in data} == {"*"}
    assert data[0]["white_agent"] == "W" and data[0]["black_agent"] == "B"


def test_export_files_and_pgn_headers(tmp_path):
    env, ctl = make(RandomStub("W"), None, seed=3, time_limit_s=0.2)
    ctl.request_turn(); ctl.human_move(next(iter(env.board.legal_moves)))
    pgn_path, csv_path = tmp_path / "g.pgn", tmp_path / "g.csv"
    ctl.export_pgn(str(pgn_path)); ctl.export_csv(str(csv_path))
    game = chess.pgn.read_game(io.StringIO(pgn_path.read_text(encoding="utf-8")))
    assert game.headers["White"] == "W" and game.headers["Black"] == HUMAN_LABEL
    assert game.headers["SeedBase"] == "3" and game.headers["TimeBudgetS"] == "0.2"
    assert len(list(game.mainline_moves())) == 2
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == ",".join(CSV_FIELDS)


# --------------------------------------------------- bucle cooperativo
def test_async_loop_stops_when_paused_from_inside_a_turn():
    holder = {"n": 0}

    def hook():
        holder["n"] += 1
        if holder["n"] == 3:
            holder["ctl"].pause()

    stub = CallbackStub(hook)
    env, ctl = make(stub, stub)
    holder["ctl"] = ctl
    reason = asyncio.run(ctl.run_async())
    assert reason == "paused" and env.ply_count == 3 and ctl.running is False


def test_async_loop_yields_so_a_concurrent_pause_is_served():
    stub = RandomStub(sleep_s=0.005)
    env, ctl = make(stub, stub, max_plies=400)

    async def scenario():
        task = asyncio.create_task(ctl.run_async(delay_s=0.0))
        await asyncio.sleep(0.05)          # el "clic" de Pausar llega mientras juega
        assert ctl.running
        ctl.pause()
        return await task

    reason = asyncio.run(scenario())
    assert reason == "paused" and 0 < env.ply_count < 400
    assert len(ctl.records) == env.ply_count


def test_async_loop_stops_at_truncation_human_and_error():
    env, ctl = make(RandomStub(), RandomStub(), max_plies=5)
    assert asyncio.run(ctl.run_async()) == "truncated" and env.ply_count == 5
    env, ctl = make(RandomStub(), None)
    assert asyncio.run(ctl.run_async()) == "human" and env.ply_count == 1
    env, ctl = make(IllegalStub(), RandomStub())
    assert asyncio.run(ctl.run_async()) == "error" and env.ply_count == 0


# ------------------------------------------------- humo de la interfaz
def _app(**kw):
    from chess_ai.gui import ChessApp
    factories = {"Humano": None, "Stub": lambda cfg: RandomStub(f"Stub-s{cfg.seed}")}
    return ChessApp(factories, **kw)


def test_gui_smoke_human_moves_and_agent_button(tmp_path):
    app = _app(export_dir=str(tmp_path), auto_reply=False)
    assert "<svg" in app.board_html.value and app.controller.mode() == "humano-humano"
    app.origin.value, app.target.value = "e2", "e4"
    assert app.on_move().status == "applied" and app.env.ply_count == 1
    fen = app.env.board.fen()
    app.origin.value, app.target.value = "d2", "d4"            # pieza blanca en turno negro
    assert app.on_move().status == "rejected" and app.env.board.fen() == fen
    app.black_select.value = "Stub"
    assert app.controller.mode() == "humano-agente"
    assert app.on_agent_turn().status == "applied" and app.env.ply_count == 2
    assert "Stub-s0" in app.log_html.value and "1. e4" in app.history_html.value
    assert app.on_undo().status == "undone" and app.env.ply_count == 0
    path = app.on_export_csv()
    assert open(path, encoding="utf-8").readline().strip() == ",".join(CSV_FIELDS)
    assert app.on_export_pgn().endswith(".pgn")


def test_gui_auto_reply_without_event_loop_plays_synchronously():
    app = _app(black="Stub", auto_reply=True)
    app.origin.value, app.target.value = "g1", "f3"
    app.on_move()
    assert app.env.ply_count == 2 and app.env.board.turn == chess.WHITE


def test_gui_promotion_and_new_game_from_fen():
    app = _app()
    app.fen_text.value = POSITIONS["promotion"]
    assert app.on_new_game().status == "reset"
    app.origin.value, app.target.value, app.promotion.value = "a7", "a8", "r"
    app.on_move()
    assert app.env.board.piece_at(chess.A8) == chess.Piece(chess.ROOK, chess.WHITE)


def test_gui_start_pause_inside_event_loop():
    app = _app(white="Stub", black="Stub", delay_s=0.0)

    async def scenario():
        app.on_toggle_run()                       # Iniciar
        assert app.run_button.description == "Pausar"
        await asyncio.sleep(0.02)
        app.on_toggle_run()                       # Pausar
        return await app._task

    assert asyncio.run(scenario()) == "paused"
    assert app.env.ply_count > 0 and app.run_button.description == "Iniciar"
