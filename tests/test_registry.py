import chess

from chess_ai.controller import AgentConfig, GameController
from chess_ai.environment import ChessEnvironment
from chess_ai.registry import AGENT_FACTORIES, AGENT_NAMES, make_agent


def test_registry_has_the_six_agents_and_each_returns_a_legal_move():
    assert set(AGENT_NAMES) == set(AGENT_FACTORIES) and len(AGENT_NAMES) == 6
    cfg = AgentConfig(depth=1, time_limit_s=0.05, seed=3, simulations=20)
    board = chess.Board()
    for name in AGENT_NAMES:
        agent = make_agent(name, cfg)
        d = agent.choose(board.copy(stack=True), time_limit_s=cfg.time_limit_s, seed=cfg.seed)
        assert d.move in board.legal_moves, name


def test_factories_build_fresh_agents():
    cfg = AgentConfig(depth=1, time_limit_s=0.05, seed=0, simulations=10)
    assert make_agent("MCTS", cfg) is not make_agent("MCTS", cfg)


def test_registry_agents_play_a_short_game_through_the_controller():
    cfg = AgentConfig(depth=1, time_limit_s=0.05, seed=1, simulations=10)
    env = ChessEnvironment(max_plies=6)
    ctl = GameController(env, make_agent("Voraz", cfg), make_agent("MCTS", cfg), cfg)
    assert ctl.play_until_stop() == "truncated"
    assert len(ctl.records) == 6 and env.official_result() == "*"
