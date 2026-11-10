"""Pruebas del torneo (Experimento 2) y de los experimentos de la seccion 9."""
import csv
import io
import os
import subprocess
import sys
import time
from collections import Counter

import chess
import chess.pgn
import pytest

from chess_ai.controller import CSV_FIELDS
from chess_ai.registry import AGENT_NAMES
from chess_ai.tournament import (GAME_FIELDS, OPENINGS, OPENINGS_BY_ID, TOURNAMENT_OPENING_IDS,
                                 TournamentConfig, load_tournament, opening_board,
                                 round_robin_schedule, run_tournament, score_interval, standings,
                                 verify_openings)
from chess_ai.experiments import EXP1_POSITIONS, exp1_summary, run_exp1

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ calendario
def test_round_robin_is_complete_with_swapped_colors():
    cfg = TournamentConfig()
    games = round_robin_schedule(cfg)
    n_pairs = len(AGENT_NAMES) * (len(AGENT_NAMES) - 1) // 2
    assert n_pairs == 15
    assert len(games) == n_pairs * len(cfg.opening_ids) * 2 >= 60
    # cada par ordenado (blancas, negras) aparece una vez por apertura
    per_color = Counter((g["white"], g["black"], g["opening_id"]) for g in games)
    assert set(per_color.values()) == {1}
    for g in games:
        assert (g["black"], g["white"], g["opening_id"]) in per_color
        assert g["white"] != g["black"]
    # cada agente juega lo mismo con blancas que con negras
    whites = Counter(g["white"] for g in games)
    blacks = Counter(g["black"] for g in games)
    assert whites == blacks and len(whites) == 6


def test_seeds_and_ids_are_distinct_and_documented():
    games = round_robin_schedule(TournamentConfig())
    assert len({g["seed"] for g in games}) == len(games)
    assert len({g["game_id"] for g in games}) == len(games)
    # paso 1000 > plies posibles: ninguna semilla por jugada se repite entre partidas
    seeds = sorted(g["seed"] for g in games)
    assert min(b - a for a, b in zip(seeds, seeds[1:])) >= 1000


def test_openings_are_legal_valid_and_shared_by_every_pair():
    rows = verify_openings()
    assert len(rows) == len(OPENINGS) == len({o["id"] for o in OPENINGS})
    for r in rows:
        board = chess.Board(r["fen"])
        assert board.is_valid() and not board.is_game_over(claim_draw=True)
        assert abs(r["E0_cp"]) < 100          # sin ventaja material ni posicional grande
    games = round_robin_schedule(TournamentConfig())
    by_pair = {}
    for g in games:
        by_pair.setdefault(frozenset((g["white"], g["black"])), set()).add(g["opening_id"])
    assert all(ops == set(TOURNAMENT_OPENING_IDS) for ops in by_pair.values())
    # la apertura se reproduce desde la posicion inicial con historia
    b = opening_board("A3_siciliana_najdorf")
    assert len(b.move_stack) == len(OPENINGS_BY_ID["A3_siciliana_najdorf"]["moves"].split())


# ------------------------------------------------------------------ partidas reales cortas
@pytest.fixture(scope="module")
def tiny_tournament(tmp_path_factory):
    out = tmp_path_factory.mktemp("torneo")
    cfg = TournamentConfig(agents=("Aleatorio", "Voraz", "Alfa-beta mejorado"),
                           opening_ids=("A1_italiana",), time_limit_s=0.02, max_plies=6,
                           event="prueba")
    t0 = time.perf_counter()
    res = run_tournament(cfg, out_dir=str(out), progress=None)
    return out, res, time.perf_counter() - t0


def test_quick_tournament_runs_in_seconds(tiny_tournament):
    _, res, elapsed = tiny_tournament
    assert len(res["games"]) == 6
    assert elapsed < 30


def test_decisions_csv_has_exact_columns(tiny_tournament):
    out, res, _ = tiny_tournament
    with open(out / "torneo_decisiones.csv", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        assert next(reader) == CSV_FIELDS
        rows = list(reader)
    assert len(rows) == len(res["decisions"]) > 0
    with open(out / "torneo_partidas.csv", encoding="utf-8") as fh:
        assert next(csv.reader(fh)) == GAME_FIELDS
    assert (out / "torneo_config.json").exists()


def test_pgn_contains_every_game_with_headers(tiny_tournament):
    out, res, _ = tiny_tournament
    text = (out / "torneo.pgn").read_text(encoding="utf-8")
    stream = io.StringIO(text)
    games = []
    while (g := chess.pgn.read_game(stream)) is not None:
        games.append(g)
    assert len(games) == len(res["games"])
    for g, row in zip(games, res["games"]):
        assert g.headers["White"] == row["white_agent"]
        assert g.headers["OpeningId"] == row["opening_id"]
        assert int(g.headers["SeedBase"]) == row["seed"]
        assert g.headers["Result"] == row["official_result"]
        assert len(list(g.mainline_moves())) == row["plies"]


def test_truncated_games_have_no_official_result(tiny_tournament):
    _, res, _ = tiny_tournament
    truncated = [g for g in res["games"] if g["truncated"]]
    assert truncated, "con 6 plies alguna partida debe truncarse"
    for g in truncated:
        assert g["official_result"] == "*" and g["termination"] == "truncated"
        assert g["white_points"] == "" and g["black_points"] == ""
        assert g["agent_plies"] == 6
    for row in res["decisions"]:
        game = next(g for g in res["games"] if g["game_id"] == row["game_id"])
        assert row["official_result"] == game["official_result"]


def test_saved_files_load_back(tiny_tournament):
    out, res, _ = tiny_tournament
    data = load_tournament(str(out))
    assert [g["game_id"] for g in data["games"]] == [g["game_id"] for g in res["games"]]
    assert standings(data["games"]) == standings(res["games"])


# ------------------------------------------------------------------ clasificacion
def _g(gid, white, black, result, truncated=0, wt=1.0, bt=2.0, wx=0, bx=0):
    pts = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(result)
    return {"game_id": gid, "white_agent": white, "black_agent": black,
            "official_result": result, "truncated": truncated,
            "white_points": "" if pts is None else pts, "black_points": "" if pts is None else 1 - pts,
            "white_moves": 10, "black_moves": 10, "white_time_s": wt, "black_time_s": bt,
            "white_time_max_s": 0.2, "black_time_max_s": 0.3, "white_exceeded": wx,
            "black_exceeded": bx}


def test_standings_by_hand():
    games = [_g("1", "A", "B", "1-0"), _g("2", "B", "A", "1/2-1/2"),
             _g("3", "A", "C", "0-1", bx=2), _g("4", "C", "B", "*", truncated=1),
             _g("5", "B", "C", "0-1")]
    table = {r["agente"]: r for r in standings(games, agents=("A", "B", "C"))}
    a, b, c = table["A"], table["B"], table["C"]
    assert (a["puntos"], a["terminadas"], a["victorias"], a["tablas"], a["derrotas"]) == (1.5, 3, 1, 1, 1)
    assert (b["puntos"], b["terminadas"], b["truncadas"]) == (0.5, 3, 1)
    assert (c["puntos"], c["terminadas"], c["victorias"], c["truncadas"]) == (2.0, 2, 2, 1)
    # la truncada no da puntos a nadie: puntos totales = partidas terminadas
    assert sum(r["puntos"] for r in table.values()) == 4
    assert c["cobertura"] == round(2 / 3, 3)
    assert c["excesos"] == 2 and c["prop_excesos"] == round(2 / 30, 4)
    assert a["tiempo_medio_s"] == round((1.0 + 2.0 + 1.0) / 30, 4)
    assert list(table) == ["C", "A", "B"]      # ordenada por puntos por terminada


def test_score_interval_contains_mean_and_is_reproducible():
    s = [1, 1, 0.5, 0, 1, 0.5, 1, 0]
    a, b = score_interval(s), score_interval(s)
    assert a == b and a["low"] <= a["mean"] <= a["high"]
    assert score_interval([])["mean"] is None


# ------------------------------------------------------------------ experimento 1
def test_exp1_positions_are_valid_and_of_each_kind():
    kinds = {p["character"] for p in EXP1_POSITIONS}
    assert kinds == {"captura", "jaque", "defensa", "tranquila", "final"}
    for p in EXP1_POSITIONS:
        b = chess.Board(p["fen"])
        assert b.is_valid() and b.outcome(claim_draw=True) is None
    assert chess.Board(EXP1_POSITIONS[1]["fen"]).is_check()


def test_exp1_values_match_on_small_positions(tmp_path):
    rows = run_exp1(depths=(1, 2), positions=[EXP1_POSITIONS[4], EXP1_POSITIONS[2]],
                    out_path=str(tmp_path / "e1.csv"))
    assert len(rows) == 2 * 2 * 3
    for key in {(r["position_id"], r["depth"]) for r in rows}:
        vals = {r["value"] for r in rows if (r["position_id"], r["depth"]) == key}
        assert len(vals) == 1
    summ = exp1_summary(rows)
    for s in summ:
        if s["algorithm"] != "Minimax" and s["depth"] == 2:
            assert s["nodes"] < next(x["nodes"] for x in summ
                                     if x["depth"] == 2 and x["algorithm"] == "Minimax")
    assert (tmp_path / "e1.csv").exists()


# ------------------------------------------------------------------ guion --rapido
def test_runner_quick_mode(tmp_path):
    t0 = time.perf_counter()
    proc = subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "correr_experimentos.py"),
                           "--rapido", "--solo", "torneo,exp1", "--salida", str(tmp_path)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (tmp_path / "torneo_decisiones.csv").exists()
    assert (tmp_path / "exp1_ahorro.csv").exists()
    assert time.perf_counter() - t0 < 60
