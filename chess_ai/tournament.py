"""Torneo todos contra todos (Experimento 2) y motor de partidas para la ablacion.

PROTOCOLO (justificacion completa en apuntes/09_protocolo.md y bitacora X-):

* APERTURAS. `OPENINGS` son lineas teoricas conocidas y equilibradas (5-10 plies),
  verificadas legales jugada a jugada (`verify_openings`). Cada partida empieza en
  la posicion INICIAL y el controlador aplica la apertura con `env.apply`, asi el
  PGN y la historia (repeticiones) quedan completos. TODOS los emparejamientos
  usan las MISMAS aperturas (`TournamentConfig.opening_ids`).
* COLORES. Cada par de agentes juega cada apertura dos veces, intercambiando
  colores: 15 pares x 8 aperturas x 2 colores = 240 partidas con la configuracion
  por defecto (el minimo del enunciado es 60).
* SEMILLAS. La partida numero k (1, 2, ...) tiene semilla base
  `seed_base + seed_stride * k`; el controlador entrega a cada jugada
  `semilla base + ply` (G-04). Como ninguna partida pasa de ~180 plies y el paso
  es 1000, ninguna jugada de dos partidas distintas comparte semilla.
* PRESUPUESTO. `time_limit_s` por decision (0.2 s por defecto, X-03). Minimax y
  Alfa-beta son de profundidad fija (ignoran el plazo); Alfa-beta mejorado y MCTS
  lo usan. Politica UNIFORME de excesos (G-05): el controlador mide el tiempo real
  de `choose`; si supera `time_limit_s + tolerance_s` la jugada SE APLICA igual y
  se marca `time_exceeded = 1` en el CSV. Se reporta la proporcion por agente.
* LIMITE. `max_plies` plies jugados por los AGENTES (despues de la apertura). Al
  llegar al limite sin final reglamentario la partida es TRUNCADA: resultado
  oficial `*`, fuera de la puntuacion. NUNCA se adjudica por evaluacion estatica;
  el balance de material final se guarda solo como dato descriptivo.
* PUNTOS. Victoria 1, tablas 0.5, derrota 0, solo con partidas terminadas.

Ejecucion en paralelo: `workers > 1` usa `multiprocessing` (procesos). Solo
funciona importando el paquete (por ejemplo desde `tools/correr_experimentos.py`);
en el cuaderno el codigo vive en `__main__` y se juega en serie.
"""
from __future__ import annotations

import csv
import datetime
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Optional

import chess
import chess.pgn

from chess_ai.environment import ChessEnvironment
from chess_ai.evaluation import DEFAULT_EVALUATOR, PIECE_VALUES
from chess_ai.search import AlphaBetaImprovedAgent
from chess_ai.mcts import MCTSAgent
from chess_ai.tuning import load_tuned_evaluator
from chess_ai.controller import (CSV_FIELDS, DEFAULT_TIME_TOLERANCE_S, AgentConfig,
                                 GameController)
from chess_ai.registry import AGENT_FACTORIES, AGENT_NAMES

# --------------------------------------------------------------------- aperturas
# Lineas teoricas principales (ECO), todas terminan con BLANCAS al turno.
OPENINGS = [
    {"id": "A1_italiana", "name": "Italiana (Giuoco Piano)", "eco": "C50",
     "moves": "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5"},
    {"id": "A2_gambito_dama_rehusado", "name": "Gambito de dama rehusado", "eco": "D35",
     "moves": "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6"},
    {"id": "A3_siciliana_najdorf", "name": "Siciliana Najdorf", "eco": "B90",
     "moves": "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6"},
    {"id": "A4_inglesa", "name": "Inglesa (cuatro caballos invertida)", "eco": "A28",
     "moves": "c2c4 e7e5 b1c3 g8f6 g1f3 b8c6"},
    {"id": "A5_espanola", "name": "Espanola (Ruy Lopez)", "eco": "C78",
     "moves": "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6"},
    {"id": "A6_francesa", "name": "Francesa clasica", "eco": "C11",
     "moves": "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6"},
    {"id": "A7_caro_kann", "name": "Caro-Kann clasica", "eco": "B18",
     "moves": "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4 c8f5"},
    {"id": "A8_eslava", "name": "Eslava", "eco": "D11",
     "moves": "d2d4 d7d5 c2c4 c7c6 g1f3 g8f6"},
    {"id": "A9_india_rey", "name": "India de rey", "eco": "E90",
     "moves": "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6"},
    {"id": "A10_nimzoindia", "name": "Nimzoindia", "eco": "E20",
     "moves": "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4"},
    {"id": "A11_escocesa", "name": "Escocesa", "eco": "C45",
     "moves": "e2e4 e7e5 g1f3 b8c6 d2d4 e5d4 f3d4 g8f6"},
    {"id": "A12_londres", "name": "Sistema Londres", "eco": "D02",
     "moves": "d2d4 d7d5 g1f3 g8f6 c1f4 e7e6"},
    {"id": "A13_india_dama", "name": "India de dama", "eco": "E12",
     "moves": "d2d4 g8f6 c2c4 e7e6 g1f3 b7b6"},
    {"id": "A14_escandinava", "name": "Escandinava", "eco": "B01",
     "moves": "e2e4 d7d5 e4d5 d8d5 b1c3 d5a5"},
    {"id": "A15_pirc", "name": "Pirc", "eco": "B07",
     "moves": "e2e4 d7d6 d2d4 g8f6 b1c3 g7g6"},
    {"id": "A16_inglesa_simetrica", "name": "Inglesa simetrica", "eco": "A30",
     "moves": "c2c4 c7c5 g1f3 g8f6 b1c3 b8c6"},
]
OPENINGS_BY_ID = {o["id"]: o for o in OPENINGS}
# Las ocho del torneo (A1-A8): abiertas (e4 e5), cerradas (d4 d5), asimetricas
# (Siciliana, Francesa, Caro-Kann) y de flanco (Inglesa). 15 pares x 8 x 2 = 240 partidas.
TOURNAMENT_OPENING_IDS = tuple(o["id"] for o in OPENINGS[:8])

TOURNAMENT_BUDGET_S = 0.2
TOURNAMENT_MAX_PLIES = 160
TOURNAMENT_DEPTH = 2

# Columnas del CSV por partida (una fila por partida).
GAME_FIELDS = ["game_id", "opening_id", "seed", "white_agent", "black_agent",
               "opening_plies", "plies", "agent_plies", "termination", "official_result",
               "truncated", "white_points", "black_points", "winner_agent",
               "duration_s", "white_moves", "white_time_s", "white_time_max_s",
               "white_exceeded", "white_depth_mean", "white_sims_mean",
               "black_moves", "black_time_s", "black_time_max_s", "black_exceeded",
               "black_depth_mean", "black_sims_mean", "material_white_final", "status"]


def opening_moves(opening) -> list:
    """Lista de `chess.Move` de una apertura (dict de OPENINGS o id)."""
    op = OPENINGS_BY_ID[opening] if isinstance(opening, str) else opening
    return [chess.Move.from_uci(u) for u in op["moves"].split()]


def opening_board(opening) -> chess.Board:
    """Tablero (con historia) tras jugar la apertura desde la posicion inicial."""
    board = chess.Board()
    for move in opening_moves(opening):
        if move not in board.legal_moves:
            raise ValueError(f"apertura {opening}: jugada ilegal {move.uci()}")
        board.push(move)
    return board


def verify_openings(openings=None) -> list:
    """Comprueba legalidad, validez y que la partida siga abierta; devuelve filas con E0."""
    rows = []
    for op in openings or OPENINGS:
        board = opening_board(op)
        assert board.is_valid(), (op["id"], board.status())
        assert board.outcome(claim_draw=True) is None, op["id"]
        rows.append({"opening_id": op["id"], "name": op["name"], "eco": op["eco"],
                     "plies": len(board.move_stack), "turn": "blancas" if board.turn else "negras",
                     "fen": board.fen(), "E0_cp": round(DEFAULT_EVALUATOR(board), 1),
                     "legal_moves": board.legal_moves.count()})
    return rows


# --------------------------------------------------------------------- agentes
# Agentes adicionales para la ablacion (Experimento 3). Se construyen por etiqueta
# dentro de cada proceso, asi la especificacion de una partida es solo texto.
ABLATION_E0_LABEL = "AB mejorado E0"
ABLATION_ESTAR_LABEL = "AB mejorado E*"
TOURNAMENT_EXTRA_FACTORIES = {
    ABLATION_E0_LABEL: lambda cfg: AlphaBetaImprovedAgent(evaluator=DEFAULT_EVALUATOR,
                                                          name=ABLATION_E0_LABEL),
    ABLATION_ESTAR_LABEL: lambda cfg: AlphaBetaImprovedAgent(evaluator=load_tuned_evaluator(),
                                                             name=ABLATION_ESTAR_LABEL),
}


def tournament_make_agent(label: str, cfg: AgentConfig):
    """Agente nuevo por etiqueta: registro de los seis o agentes extra de la ablacion."""
    if label in AGENT_FACTORIES:
        return AGENT_FACTORIES[label](cfg)
    if label in TOURNAMENT_EXTRA_FACTORIES:
        return TOURNAMENT_EXTRA_FACTORIES[label](cfg)
    raise KeyError(f"agente desconocido: {label!r}")


def describe_agent(label: str, cfg: AgentConfig) -> dict:
    """Parametros efectivos de un agente (van a torneo_config.json)."""
    agent = tournament_make_agent(label, cfg)
    out = {"label": label, "class": type(agent).__name__}
    for attr in ("depth", "max_depth", "ordering", "quiescence", "simulations", "exploration",
                 "rollout_limit", "rollout_policy", "capture_bias"):
        if hasattr(agent, attr):
            value = getattr(agent, attr)
            out[attr] = round(value, 6) if isinstance(value, float) else value
    ev = getattr(agent, "evaluator", None)
    if ev is not None:
        out["evaluator"] = {"name": getattr(ev, "name", str(ev)),
                            "weights": list(getattr(ev, "weights", ()))}
    if isinstance(agent, MCTSAgent):
        out["budget"] = ("simulaciones fijas" if agent.simulations is not None
                         else "plazo temporal (time_limit_s)")
    elif hasattr(agent, "max_depth"):
        out["budget"] = "plazo temporal (profundizacion iterativa)"
    elif hasattr(agent, "depth"):
        out["budget"] = "profundidad fija (ignora el plazo; exceso registrado)"
    else:
        out["budget"] = "un ply / sin busqueda"
    return out


# --------------------------------------------------------------------- configuracion
@dataclass
class TournamentConfig:
    """Todo lo que define el torneo. Se guarda completo en el JSON de configuracion."""
    agents: tuple = AGENT_NAMES
    opening_ids: tuple = TOURNAMENT_OPENING_IDS
    time_limit_s: float = TOURNAMENT_BUDGET_S
    max_plies: int = TOURNAMENT_MAX_PLIES          # plies de los agentes, sin contar la apertura
    depth: int = TOURNAMENT_DEPTH                  # Minimax y Alfa-beta
    mcts_simulations: Optional[int] = None         # None: MCTS usa el plazo
    tolerance_s: float = DEFAULT_TIME_TOLERANCE_S
    seed_base: int = 0
    seed_stride: int = 1000
    event: str = "Taller 3 IA UTP - torneo (Experimento 2)"
    game_prefix: str = "T"

    def agent_config(self, seed: int) -> AgentConfig:
        return AgentConfig(depth=self.depth, time_limit_s=self.time_limit_s, seed=seed,
                           simulations=self.mcts_simulations)


def round_robin_schedule(cfg: TournamentConfig) -> list:
    """Todos contra todos: por par y por apertura, una partida con cada color.

    Devuelve dicts {game_id, index, opening_id, seed, white, black}. El orden es
    determinista (pares en el orden de `cfg.agents`, luego aperturas, luego colores).
    """
    games = []
    for a, b in combinations(cfg.agents, 2):
        for op in cfg.opening_ids:
            for white, black in ((a, b), (b, a)):
                games.append({"white": white, "black": black, "opening_id": op})
    return _tour_number(games, cfg)


def paired_schedule(cfg: TournamentConfig, pairs) -> list:
    """Como `round_robin_schedule` pero solo para los pares dados (ablacion)."""
    games = []
    for a, b in pairs:
        for op in cfg.opening_ids:
            for white, black in ((a, b), (b, a)):
                games.append({"white": white, "black": black, "opening_id": op})
    return _tour_number(games, cfg)


def _tour_number(games: list, cfg: TournamentConfig) -> list:
    width = max(3, len(str(len(games))))
    for k, g in enumerate(games, start=1):
        g["index"] = k
        g["game_id"] = f"{cfg.game_prefix}{k:0{width}d}"
        g["seed"] = cfg.seed_base + cfg.seed_stride * k
    return games


# --------------------------------------------------------------------- una partida
def _tour_material_white(board: chess.Board) -> float:
    total = 0.0
    for pt, val in PIECE_VALUES.items():
        total += val * (chess.popcount(board.pieces_mask(pt, chess.WHITE))
                        - chess.popcount(board.pieces_mask(pt, chess.BLACK)))
    return round(total, 1)


def _tour_side_stats(records, color: str) -> dict:
    sel = [r for r in records if r.color == color]
    times = [r.elapsed_s for r in sel]
    return {"moves": len(sel), "time_s": round(sum(times), 4),
            "time_max_s": round(max(times), 4) if times else 0.0,
            "exceeded": sum(1 for r in sel if r.time_exceeded),
            "depth_mean": round(statistics.mean(r.completed_depth for r in sel), 3) if sel else 0.0,
            "sims_mean": round(statistics.mean(r.simulations for r in sel), 1) if sel else 0.0}


def play_game(spec: dict, cfg: TournamentConfig, workers: int = 1) -> dict:
    """Juega UNA partida con `GameController` y devuelve sus filas y su PGN.

    Resultado: {"game": fila de GAME_FIELDS, "decisions": filas con CSV_FIELDS,
    "pgn": texto PGN}. El estado de la partida (terminal/truncada) lo decide el
    entorno; si un agente devolviera algo invalido la partida queda con estado
    'error' y sin resultado (no ocurre en las corridas guardadas).
    """
    t0 = time.perf_counter()
    op = OPENINGS_BY_ID[spec["opening_id"]]
    moves = opening_moves(op)
    env = ChessEnvironment(max_plies=len(moves) + cfg.max_plies)
    for move in moves:
        env.apply(move)
    agent_cfg = cfg.agent_config(spec["seed"])
    white = tournament_make_agent(spec["white"], agent_cfg)
    black = tournament_make_agent(spec["black"], agent_cfg)
    ctl = GameController(env, white, black, agent_cfg, game_id=spec["game_id"],
                         opening_id=op["id"], tolerance_s=cfg.tolerance_s)
    status = ctl.play_until_stop()
    duration = time.perf_counter() - t0

    termination = env.termination() if status in ("terminal", "truncated") else "error"
    result = env.official_result() if status == "terminal" else "*"
    truncated = int(status == "truncated")
    wp = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(result)
    winner = ""
    if result == "1-0":
        winner = spec["white"]
    elif result == "0-1":
        winner = spec["black"]
    ws, bs = _tour_side_stats(ctl.records, "white"), _tour_side_stats(ctl.records, "black")
    game = {
        "game_id": spec["game_id"], "opening_id": op["id"], "seed": spec["seed"],
        "white_agent": spec["white"], "black_agent": spec["black"],
        "opening_plies": len(moves), "plies": env.ply_count,
        "agent_plies": env.ply_count - len(moves), "termination": termination,
        "official_result": result, "truncated": truncated,
        "white_points": "" if wp is None else wp, "black_points": "" if wp is None else 1.0 - wp,
        "winner_agent": winner, "duration_s": round(duration, 3),
        **{f"white_{k}": v for k, v in ws.items()}, **{f"black_{k}": v for k, v in bs.items()},
        "material_white_final": _tour_material_white(env.board), "status": status,
    }
    decisions = [rec.csv_row(termination, result) for rec in ctl.records]

    headers = ctl.pgn_headers()
    headers.update({
        "Event": cfg.event, "Site": f"{platform.system()} {platform.release()}",
        "Round": spec["index"], "Opening": op["name"], "OpeningId": op["id"], "ECO": op["eco"],
        "OpeningMoves": op["moves"], "OpeningPlies": len(moves), "SeedBase": spec["seed"],
        "MaxAgentPlies": cfg.max_plies, "Workers": workers,
        "ExcessPolicy": "se aplica la jugada y se registra time_exceeded",
        "TruncationPolicy": "limite de plies -> truncada, resultado oficial *",
        "Mode": "torneo agente-agente",
    })
    game_pgn = env.to_pgn(headers)
    node, k = game_pgn, 0
    by_ply = {r.ply: r for r in ctl.records}
    while node.variations:
        node = node.variation(0)
        k += 1
        if k == len(moves):
            node.comment = "fin de la apertura; desde aqui juegan los agentes"
        rec = by_ply.get(k)
        if rec is not None:
            info = (f"d={rec.completed_depth}" if rec.simulations == 0
                    else f"sims={rec.simulations}")
            flag = " EXCESO" if rec.time_exceeded else ""
            node.comment = f"[%emt {rec.elapsed_s:.3f}] {info}{flag}"
    pgn_text = str(game_pgn) + "\n"
    return {"game": game, "decisions": decisions, "pgn": pgn_text}


def _tour_worker(args):
    """Funcion de los procesos del pool (debe vivir a nivel de modulo para Windows)."""
    spec, cfg, workers = args
    return spec["index"], play_game(spec, cfg, workers)


# --------------------------------------------------------------------- torneo completo
def run_games(schedule: list, cfg: TournamentConfig, workers: int = 1, progress=None) -> list:
    """Juega las partidas del calendario (en serie o con `workers` procesos), en orden."""
    jobs = [(spec, cfg, workers) for spec in schedule]
    results = {}
    done = 0
    t0 = time.perf_counter()

    def _report(idx, res):
        nonlocal done
        done += 1
        if progress is not None:
            g = res["game"]
            progress(f"[{done:>3}/{len(jobs)}] {g['game_id']} {g['white_agent']} - "
                     f"{g['black_agent']} ({g['opening_id']}): {g['termination']} "
                     f"{g['official_result']} en {g['agent_plies']} plies, {g['duration_s']:.1f} s "
                     f"(acumulado {time.perf_counter() - t0:.0f} s)")

    use_pool = workers > 1 and _tour_worker.__module__ != "__main__"
    if workers > 1 and not use_pool and progress is not None:
        progress("Aviso: el codigo vive en __main__ (cuaderno); se juega en serie.")
    if use_pool:
        import multiprocessing
        with multiprocessing.get_context("spawn").Pool(workers) as pool:
            for idx, res in pool.imap_unordered(_tour_worker, jobs, chunksize=1):
                results[idx] = res
                _report(idx, res)
    else:
        for job in jobs:
            idx, res = _tour_worker(job)
            results[idx] = res
            _report(idx, res)
    return [results[spec["index"]] for spec in schedule]


def _tour_write_csv(path: str, fields, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def environment_info() -> dict:
    """Versiones y hardware (la reproducibilidad incluye el entorno, no solo semillas)."""
    import importlib.metadata as md
    info = {"python": sys.version.split()[0], "python_chess": chess.__version__,
            "platform": platform.platform(), "processor": platform.processor(),
            "machine": platform.machine(), "logical_cpus": os.cpu_count()}
    for pkg in ("numpy", "matplotlib"):
        try:
            info[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            info[pkg] = None
    return info


def run_tournament(cfg: TournamentConfig | None = None, *, schedule: list | None = None,
                   workers: int = 1, out_dir: str | None = None, prefix: str = "torneo",
                   progress=print, extra_config: dict | None = None) -> dict:
    """Juega el torneo y, si `out_dir`, escribe `<prefix>_decisiones.csv`,
    `<prefix>_partidas.csv`, `<prefix>.pgn` y `<prefix>_config.json`.

    Devuelve {"games", "decisions", "pgn", "config"}.
    """
    cfg = cfg or TournamentConfig()
    schedule = schedule if schedule is not None else round_robin_schedule(cfg)
    started = datetime.datetime.now().isoformat(timespec="seconds")
    t0, c0 = time.perf_counter(), time.process_time()
    results = run_games(schedule, cfg, workers=workers, progress=progress)
    wall = time.perf_counter() - t0
    games = [r["game"] for r in results]
    decisions = [row for r in results for row in r["decisions"]]
    labels = sorted({s["white"] for s in schedule} | {s["black"] for s in schedule},
                    key=lambda x: (AGENT_NAMES.index(x) if x in AGENT_NAMES else 99, x))
    config = {
        "description": cfg.event,
        "started": started, "finished": datetime.datetime.now().isoformat(timespec="seconds"),
        "duration_wall_s": round(wall, 1),
        "cpu_main_process_s": round(time.process_time() - c0, 1),
        "workers": workers,
        "n_games": len(games),
        "tournament": {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(cfg).items()},
        "policies": {
            "points": "victoria 1, tablas 0.5, derrota 0; solo partidas terminadas",
            "truncation": (f"{cfg.max_plies} plies de los agentes tras la apertura -> truncada, "
                           "resultado oficial '*', fuera de los puntos; sin adjudicacion por E"),
            "time_excess": (f"tiempo real de choose > {cfg.time_limit_s} + {cfg.tolerance_s} s -> "
                            "time_exceeded=1; la jugada se aplica igual (politica uniforme)"),
            "seeds": f"partida k: semilla base = {cfg.seed_base} + {cfg.seed_stride}*k; jugada: base + ply",
            "draws": "reclamo automatico (board.outcome(claim_draw=True))",
            "openings": "mismas aperturas para todos los pares; cada apertura con ambos colores",
        },
        "agents": {lab: describe_agent(lab, cfg.agent_config(0)) for lab in labels},
        "openings": [dict(OPENINGS_BY_ID[o], fen=opening_board(o).fen()) for o in cfg.opening_ids],
        "games_seeds": {g["game_id"]: g["seed"] for g in schedule},
        "environment": environment_info(),
    }
    if extra_config:
        config.update(extra_config)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        _tour_write_csv(os.path.join(out_dir, f"{prefix}_decisiones.csv"), CSV_FIELDS, decisions)
        _tour_write_csv(os.path.join(out_dir, f"{prefix}_partidas.csv"), GAME_FIELDS, games)
        with open(os.path.join(out_dir, f"{prefix}.pgn"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(r["pgn"] for r in results))
        with open(os.path.join(out_dir, f"{prefix}_config.json"), "w", encoding="utf-8") as fh:
            json.dump(config, fh, ensure_ascii=False, indent=2)
    return {"games": games, "decisions": decisions, "pgn": [r["pgn"] for r in results],
            "config": config}


# --------------------------------------------------------------------- lectura y tablas
_TOUR_INT_FIELDS = {"seed", "ply", "nodes", "leaves", "cutoffs", "completed_depth", "simulations",
                    "time_exceeded", "opening_plies", "plies", "agent_plies", "truncated",
                    "white_moves", "black_moves", "white_exceeded", "black_exceeded"}
_TOUR_FLOAT_FIELDS = {"elapsed_s", "duration_s", "white_time_s", "black_time_s",
                      "white_time_max_s", "black_time_max_s", "white_depth_mean",
                      "black_depth_mean", "white_sims_mean", "black_sims_mean",
                      "material_white_final", "white_points", "black_points"}


def read_typed_csv(path: str) -> list:
    """Lee un CSV del torneo convirtiendo las columnas numericas conocidas."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        for k, v in row.items():
            if v == "" or v is None:
                continue
            if k in _TOUR_INT_FIELDS:
                row[k] = int(float(v))
            elif k in _TOUR_FLOAT_FIELDS:
                row[k] = float(v)
    return rows


def load_tournament(out_dir: str, prefix: str = "torneo") -> dict:
    """Carga lo guardado por `run_tournament` (sin volver a jugar)."""
    out = {"games": read_typed_csv(os.path.join(out_dir, f"{prefix}_partidas.csv")),
           "decisions": read_typed_csv(os.path.join(out_dir, f"{prefix}_decisiones.csv"))}
    cfg_path = os.path.join(out_dir, f"{prefix}_config.json")
    out["config"] = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}
    return out


def decision_mover(row: dict) -> str:
    """Agente que hizo la jugada de una fila de decisiones (ply impar = blancas).

    Vale porque todas las partidas empiezan en la posicion inicial (blancas mueven en
    el ply 1) y la apertura se cuenta en `ply`.
    """
    return row["white_agent"] if int(row["ply"]) % 2 == 1 else row["black_agent"]


def standings(games: list, agents=None) -> list:
    """Tabla del enunciado por agente (solo terminadas puntuan; truncadas aparte).

    Columnas: agente, partidas, terminadas, puntos, victorias, tablas, derrotas,
    truncadas, errores, puntos_por_terminada, cobertura (terminadas / partidas),
    jugadas, tiempo_medio_s (por decision), tiempo_max_s, excesos y prop_excesos.
    Ordenada por puntos por partida terminada (clasificacion PROVISIONAL: depende
    de la cobertura) y despues por puntos.
    """
    labels = list(agents) if agents is not None else sorted(
        {g["white_agent"] for g in games} | {g["black_agent"] for g in games},
        key=lambda x: (AGENT_NAMES.index(x) if x in AGENT_NAMES else 99, x))
    table = []
    for lab in labels:
        row = {"agente": lab, "partidas": 0, "terminadas": 0, "puntos": 0.0, "victorias": 0,
               "tablas": 0, "derrotas": 0, "truncadas": 0, "errores": 0, "jugadas": 0,
               "tiempo_total_s": 0.0, "tiempo_max_s": 0.0, "excesos": 0}
        for g in games:
            for side in ("white", "black"):
                if g[f"{side}_agent"] != lab:
                    continue
                row["partidas"] += 1
                row["jugadas"] += int(g[f"{side}_moves"])
                row["tiempo_total_s"] += float(g[f"{side}_time_s"])
                row["tiempo_max_s"] = max(row["tiempo_max_s"], float(g[f"{side}_time_max_s"]))
                row["excesos"] += int(g[f"{side}_exceeded"])
                if int(g["truncated"]):
                    row["truncadas"] += 1
                    continue
                if g["official_result"] not in ("1-0", "0-1", "1/2-1/2"):
                    row["errores"] += 1
                    continue
                pts = float(g[f"{side}_points"])
                row["terminadas"] += 1
                row["puntos"] += pts
                if pts == 1.0:
                    row["victorias"] += 1
                elif pts == 0.5:
                    row["tablas"] += 1
                else:
                    row["derrotas"] += 1
        n, fin, mv = row["partidas"], row["terminadas"], row["jugadas"]
        row["puntos_por_terminada"] = round(row["puntos"] / fin, 3) if fin else None
        row["cobertura"] = round(fin / n, 3) if n else None
        row["tiempo_medio_s"] = round(row["tiempo_total_s"] / mv, 4) if mv else None
        row["prop_excesos"] = round(row["excesos"] / mv, 4) if mv else None
        row["tiempo_total_s"] = round(row["tiempo_total_s"], 2)
        table.append(row)
    table.sort(key=lambda r: (-(r["puntos_por_terminada"] or 0.0), -r["puntos"]))
    return table


def standings_markdown(table: list) -> str:
    """La tabla del enunciado en Markdown (mas cobertura y excesos)."""
    lines = ["| Agente | Puntos / partidas terminadas | Victorias | Tablas | Derrotas | Truncadas "
             "| Tiempo medio | Cobertura | Excesos |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        ppt = f" ({r['puntos_por_terminada']:.2f})" if r["puntos_por_terminada"] is not None else ""
        lines.append(
            f"| {r['agente']} | {r['puntos']:g} / {r['terminadas']}{ppt} | {r['victorias']} | "
            f"{r['tablas']} | {r['derrotas']} | {r['truncadas']} | "
            f"{r['tiempo_medio_s']:.3f} s | {r['terminadas']}/{r['partidas']} | "
            f"{100 * (r['prop_excesos'] or 0):.1f} % |")
    return "\n".join(lines)


def pairwise_table(games: list, agents=None) -> dict:
    """{(A, B): {"puntos_A", "terminadas", "truncadas", "partidas"}} desde A."""
    labels = list(agents) if agents is not None else sorted(
        {g["white_agent"] for g in games} | {g["black_agent"] for g in games})
    out = {}
    for a in labels:
        for b in labels:
            if a == b:
                continue
            cell = {"puntos_A": 0.0, "terminadas": 0, "truncadas": 0, "partidas": 0}
            for g in games:
                if {g["white_agent"], g["black_agent"]} != {a, b}:
                    continue
                cell["partidas"] += 1
                if int(g["truncated"]) or g["official_result"] == "*":
                    cell["truncadas"] += 1
                    continue
                side = "white" if g["white_agent"] == a else "black"
                cell["terminadas"] += 1
                cell["puntos_A"] += float(g[f"{side}_points"])
            out[(a, b)] = cell
    return out


def score_interval(scores, level: float = 0.95, n_boot: int = 5000, seed: int = 0) -> dict:
    """Media de puntos (1/0.5/0) con intervalo bootstrap percentil reproducible.

    Con pocas partidas el intervalo es ancho: es la incertidumbre honesta del
    resultado. Tambien devuelve el error estandar normal.
    """
    scores = [float(s) for s in scores]
    n = len(scores)
    if n == 0:
        return {"n": 0, "mean": None, "low": None, "high": None, "se": None}
    mean = sum(scores) / n
    se = statistics.stdev(scores) / math.sqrt(n) if n > 1 else float("nan")
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(scores) for _ in range(n)) / n for _ in range(n_boot))
    lo = boots[int((1 - level) / 2 * n_boot)]
    hi = boots[min(n_boot - 1, int((1 + level) / 2 * n_boot))]
    return {"n": n, "mean": round(mean, 4), "low": round(lo, 4), "high": round(hi, 4),
            "se": round(se, 4) if n > 1 else None}


# --------------------------------------------------------------------- carga en paralelo
def _tour_probe(args):
    """Profundidad completada del mejorado y simulaciones de MCTS en unas posiciones."""
    fens, time_limit_s = args
    out = []
    for fen in fens:
        board = chess.Board(fen)
        d = AlphaBetaImprovedAgent().choose(board.copy(stack=True), time_limit_s=time_limit_s)
        m = MCTSAgent().choose(board.copy(stack=True), time_limit_s=time_limit_s, seed=1)
        out.append((d.stats.completed_depth, d.stats.nodes, m.stats.simulations))
    return out


def parallel_load_check(workers: int = 4, fens=None, time_limit_s: float = TOURNAMENT_BUDGET_S,
                        repeats: int = 2) -> dict:
    """Compara en serie vs con `workers` procesos simultaneos (carga del torneo).

    Mide, en las mismas posiciones, la profundidad media completada por el
    mejorado, sus nodos y las simulaciones de MCTS por decision. Si caen poco, el
    paralelismo no cambia de forma grave la fuerza de los agentes por plazo.
    """
    fens = fens or [opening_board(o).fen() for o in OPENINGS[:8]]
    serial = []
    for _ in range(repeats):
        serial.extend(_tour_probe((fens, time_limit_s)))
    parallel = []
    if workers > 1:
        import multiprocessing
        with multiprocessing.get_context("spawn").Pool(workers) as pool:
            for chunk in pool.map(_tour_probe, [(fens, time_limit_s)] * (workers * repeats)):
                parallel.extend(chunk)

    def _summ(rows):
        if not rows:
            return {}
        return {"n": len(rows), "depth_mean": round(statistics.mean(r[0] for r in rows), 3),
                "nodes_mean": round(statistics.mean(r[1] for r in rows), 1),
                "sims_mean": round(statistics.mean(r[2] for r in rows), 1),
                "depth_dist": {d: sum(1 for r in rows if r[0] == d)
                               for d in sorted({r[0] for r in rows})}}

    return {"workers": workers, "time_limit_s": time_limit_s, "positions": len(fens),
            "serial": _summ(serial), "parallel": _summ(parallel)}
