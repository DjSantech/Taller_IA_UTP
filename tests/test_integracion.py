"""Pruebas de la seccion 7 (A, B y D): torre, heuristicas, AND-OR, expectiminimax, Kriegspiel."""
import itertools

import chess
import pytest

from chess_ai.rook_problem import (
    ROOK_COST_MODELS, ROOK_OBSTACLES_LENGTH_VS_COST, RookProblem, h_manhattan, h_rook_lines,
    rook_astar, rook_bfs, rook_check_heuristic, rook_dfs, rook_dfs_order_demo, rook_greedy,
    rook_run_all, rook_scenarios, rook_square, rook_square_name, rook_true_costs, rook_ucs,
    rook_unit_manhattan_counterexample, plot_rook_expansions, rook_results_table)
from chess_ai.uncertainty import (
    MATE_POSITIONS, AndOrStats, and_or_mate_search, belief_after_hidden_move,
    belief_after_own_try, chance_root_decision, chance_scale_transform,
    chance_tree_leaves, chance_tree_safe_vs_risky, chance_tree_scale, count_plan_leaves,
    expectiminimax, format_mate_plan, kriegspiel_belief_demo, transform_utilities,
    verify_mate_plan, worst_case_minimax)

ALL_SQUARES = [(c, r) for c in range(8) for r in range(8)]
SCENARIOS = list(rook_scenarios().values())


# --- A. formulacion y busqueda no informada ----------------------------------
def test_square_names_roundtrip():
    assert rook_square("a1") == (0, 0) and rook_square("h8") == (7, 7)
    assert all(rook_square(rook_square_name(s)) == s for s in ALL_SQUARES)


def test_actions_from_a1_empty_board():
    p = RookProblem()
    acts = p.actions((0, 0))
    assert len(acts) == 14                      # 7 hacia el norte + 7 hacia el este
    assert acts[0] == ("N", 1) and acts[7] == ("E", 1)
    assert p.result((0, 0), ("N", 7)) == (0, 7)
    assert p.step_cost((0, 0), ("N", 7), (0, 7)) == 1
    assert p.with_cost("distance").step_cost((0, 0), ("N", 7), (0, 7)) == 7


def test_obstacles_block_and_cannot_be_jumped():
    p = RookProblem(obstacles=frozenset({(0, 3)}))
    north = [k for d, k in p.actions((0, 0)) if d == "N"]
    assert north == [1, 2]
    assert not p.is_valid_path([(0, 0), (0, 7), (7, 7)])


@pytest.mark.parametrize("problem", SCENARIOS)
@pytest.mark.parametrize("model", ROOK_COST_MODELS)
def test_all_routes_are_legal_rook_moves(problem, model):
    for r in rook_run_all(problem.with_cost(model)):
        assert r.found, r.algorithm
        assert problem.is_valid_path(r.path), (r.algorithm, r.route_text())
        assert r.length == len(r.path) - 1


@pytest.mark.parametrize("problem", SCENARIOS)
def test_bfs_is_optimal_in_length(problem):
    hstar = rook_true_costs(problem.with_cost("unit"))
    assert rook_bfs(problem).length == hstar[problem.start]


@pytest.mark.parametrize("problem", SCENARIOS)
@pytest.mark.parametrize("model", ROOK_COST_MODELS)
def test_ucs_and_astar_are_optimal_in_their_cost(problem, model):
    p = problem.with_cost(model)
    opt = rook_true_costs(p)[p.start]
    assert rook_ucs(p).cost == opt
    assert rook_astar(p).cost == opt


@pytest.mark.parametrize("problem", SCENARIOS)
@pytest.mark.parametrize("model", ROOK_COST_MODELS)
def test_astar_with_admissible_h_expands_no_more_than_ucs(problem, model):
    p = problem.with_cost(model)
    assert rook_astar(p).expanded <= rook_ucs(p).expanded


def test_ucs_unit_reproduces_bfs_expansion_order():
    # Igual que en el Taller 1 (D-22): con costo unitario y desempate FIFO, UCS = BFS.
    for p in SCENARIOS:
        assert rook_ucs(p).expansion_order == rook_bfs(p).expansion_order


def test_length_and_cost_differ_with_obstacles():
    p = RookProblem(obstacles=ROOK_OBSTACLES_LENGTH_VS_COST)
    by_moves = rook_ucs(p)
    by_squares = rook_ucs(p.with_cost("distance"))
    assert (by_moves.length, by_moves.cost_distance) == (5, 16)
    assert (by_squares.length, by_squares.cost_distance) == (7, 14)


def test_dfs_route_depends_on_action_order():
    rows = rook_dfs_order_demo()
    routes = {r["ruta"] for r in rows}
    assert len(routes) >= 3
    assert all(r["ucs_unit_cost"] == 2 for r in rows)   # el optimo no cambia
    assert rows[0]["longitud"] == 14 and rows[1]["longitud"] == 2


def test_dfs_is_not_optimal_in_length():
    assert rook_dfs(RookProblem()).length > rook_bfs(RookProblem()).length


def test_unreachable_goal_returns_no_path():
    walled = frozenset({(6, 7), (7, 6)})                 # h8 encerrada
    p = RookProblem(obstacles=walled)
    for r in rook_run_all(p):
        assert not r.found and r.length == -1 and r.cost == float("inf")


# --- B. heuristicas: verificacion exhaustiva ---------------------------------
@pytest.mark.parametrize("obstacles", [frozenset(), ROOK_OBSTACLES_LENGTH_VS_COST])
def test_lines_heuristic_admissible_and_consistent_for_unit_cost_all_squares(obstacles):
    check = rook_check_heuristic(RookProblem(obstacles=obstacles), h_rook_lines)
    assert check["states"] == 64 - len(obstacles)
    assert check["admissible"] and check["consistent"]


@pytest.mark.parametrize("goal", [(7, 7), (3, 4), (0, 0)])
def test_lines_heuristic_admissible_for_every_goal(goal):
    assert rook_check_heuristic(RookProblem(start=(1, 1) if goal != (1, 1) else (0, 0),
                                            goal=goal), h_rook_lines)["admissible"]


@pytest.mark.parametrize("obstacles", [frozenset(), ROOK_OBSTACLES_LENGTH_VS_COST])
def test_manhattan_admissible_and_consistent_for_distance_cost_all_squares(obstacles):
    check = rook_check_heuristic(RookProblem(obstacles=obstacles, cost_model="distance"),
                                 h_manhattan)
    assert check["admissible"] and check["consistent"]


def test_manhattan_overestimates_with_unit_cost():
    hstar = rook_true_costs(RookProblem())
    assert h_manhattan((0, 0), (7, 7)) == 14 and hstar[(0, 0)] == 2
    assert not rook_check_heuristic(RookProblem(), h_manhattan)["admissible"]


def test_manhattan_with_unit_cost_makes_astar_suboptimal():
    ce = rook_unit_manhattan_counterexample()
    assert ce["problem"] is not None
    assert ce["manhattan"].length > ce["optimal"].length
    assert rook_astar(ce["problem"]).length == ce["optimal"].length   # h de la consigna si


def test_greedy_is_not_optimal_in_distance_cost_with_obstacles():
    p = RookProblem(obstacles=ROOK_OBSTACLES_LENGTH_VS_COST, cost_model="distance")
    assert rook_greedy(p).cost > rook_ucs(p).cost


def test_true_costs_match_bfs_from_every_square():
    hstar = rook_true_costs(RookProblem())
    for s in itertools.islice(ALL_SQUARES, 0, 64, 5):
        assert rook_bfs(RookProblem(start=s)).length == hstar[s]


def test_plot_returns_figure(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    tables = {"a1->h8": rook_results_table(RookProblem())}
    fig = plot_rook_expansions(tables, str(tmp_path / "f.png"))
    assert fig is not None and (tmp_path / "f.png").exists()


# --- D1. AND-OR ---------------------------------------------------------------
@pytest.mark.parametrize("name,depth", [("mate_en_1", 1), ("mate_en_2_pasillo", 2),
                                        ("mate_en_2_dama", 2)])
def test_and_or_plan_covers_all_defenses_and_ends_in_mate(name, depth):
    board = chess.Board(MATE_POSITIONS[name])
    fen = board.fen()
    plan = and_or_mate_search(board, depth)
    assert plan is not None
    info = verify_mate_plan(board, plan)
    assert info["ok"], info["error"]
    assert info["max_attacker_moves"] == depth
    assert board.fen() == fen and not board.move_stack     # tablero intacto


@pytest.mark.parametrize("name", ["mate_en_2_pasillo", "mate_en_2_dama"])
def test_mate_in_two_positions_have_no_mate_in_one(name):
    assert and_or_mate_search(chess.Board(MATE_POSITIONS[name]), 1) is None


def test_mate_in_two_queen_plan_is_conditional():
    board = chess.Board(MATE_POSITIONS["mate_en_2_dama"])
    plan = and_or_mate_search(board, 2)
    (key, replies), = plan.items()
    assert board.san(key) == "Kf6"
    after = board.copy()
    after.push(key)
    assert set(replies) == set(after.legal_moves) and len(replies) == 3
    second = {next(iter(sub)) for sub in replies.values()}
    assert len(second) == 3                                  # una respuesta por defensa
    assert count_plan_leaves(plan) == 3
    assert "Qg5#" in format_mate_plan(board, plan)


def test_linear_sequence_is_not_a_plan():
    board = chess.Board(MATE_POSITIONS["mate_en_2_dama"])
    kf6, kh7, qg7 = (chess.Move.from_uci(u) for u in ("e7f6", "h6h7", "g2g7"))
    info = verify_mate_plan(board, {kf6: {kh7: {qg7: {}}}})
    assert not info["ok"] and "defensas sin cubrir" in info["error"]
    after = board.copy()
    after.push(kf6)
    same_reply = {kf6: {r: {qg7: {}} for r in after.legal_moves}}
    assert not verify_mate_plan(board, same_reply)["ok"]


def test_shortest_plan_is_preferred():
    board = chess.Board(MATE_POSITIONS["mate_en_1"])
    longer = and_or_mate_search(board, 3, shortest=False)
    shortest = and_or_mate_search(board, 3)
    assert verify_mate_plan(board, longer)["max_attacker_moves"] == 3
    assert verify_mate_plan(board, shortest)["max_attacker_moves"] == 1


def test_stalemate_is_not_success():
    # Tras 1.Qf7 negras no tienen jugadas pero NO estan en jaque: ahogado = tablas.
    # Un AND "sin estados que cubrir" no puede contarse como exito (en AIMA si lo seria).
    board = chess.Board("7k/8/8/6K1/8/8/8/5Q2 w - - 0 1")
    after = board.copy()
    after.push_uci("f1f7")
    assert after.is_stalemate()
    stats = AndOrStats()
    assert and_or_mate_search(board, 1, stats) is None
    assert stats.failures_by_draw >= 1


def test_no_plan_returns_none():
    assert and_or_mate_search(chess.Board(), 2) is None


# --- D2. expectiminimax frente a minimax --------------------------------------
def test_expectiminimax_and_minimax_choose_differently():
    tree = chance_tree_safe_vs_risky()
    e_best, e_vals = chance_root_decision(tree, expectiminimax)
    m_best, m_vals = chance_root_decision(tree, worst_case_minimax)
    assert e_vals == {"segura": pytest.approx(2.75), "arriesgada": pytest.approx(3.5)}
    assert m_vals == {"segura": 2.0, "arriesgada": -4.0}
    assert (e_best, m_best) == ("arriesgada", "segura")


def test_monotone_transform_changes_expectiminimax_not_minimax():
    tree = chance_tree_scale()
    leaves = chance_tree_leaves(tree)
    new = transform_utilities(tree, chance_scale_transform)
    new_leaves = chance_tree_leaves(new)
    # La transformacion conserva el orden de las hojas (monotona creciente).
    assert sorted(range(len(leaves)), key=leaves.__getitem__) == \
        sorted(range(len(new_leaves)), key=new_leaves.__getitem__)
    assert chance_root_decision(tree, expectiminimax)[0] == "a1"
    assert chance_root_decision(new, expectiminimax)[0] == "a2"
    assert chance_root_decision(tree, worst_case_minimax)[0] == "a1"
    assert chance_root_decision(new, worst_case_minimax)[0] == "a1"


def test_chance_probabilities_must_sum_to_one():
    from chess_ai.uncertainty import ChanceNode
    bad = ChanceNode("chance", (("x", 0.5, ChanceNode("leaf", (), 1.0)),))
    with pytest.raises(ValueError):
        expectiminimax(bad)


# --- D3. Kriegspiel -------------------------------------------------------------
def test_belief_state_grows_with_hidden_moves():
    rows = kriegspiel_belief_demo()
    sizes = [r["mundos_posibles"] for r in rows]
    assert sizes[0] == 1 and sizes[2] == 20
    assert sizes[-1] > sizes[2]


def test_illegal_try_splits_belief_state():
    board = chess.Board()
    board.push_uci("e2e4")
    belief = belief_after_hidden_move({board.epd(): board})
    legal, illegal = belief_after_own_try(belief, "e4e5")
    assert len(legal) + len(illegal) == len(belief) == 20
    assert len(illegal) == 1                      # solo si negras jugaron ...e5
    (world,) = illegal.values()
    assert world.piece_at(chess.E5) == chess.Piece(chess.PAWN, chess.BLACK)
