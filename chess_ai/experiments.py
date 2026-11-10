"""Experimentos de la seccion 9: ahorro de busqueda, torneo, ablacion, MCTS y graficas.

Las funciones `run_*` ejecutan (las pesadas se corren con tools/correr_experimentos.py);
las funciones `*_load` / `*_summary` / `fig_*` leen los CSV guardados en `resultados/`
para que el cuaderno muestre los resultados SIN volver a jugar el torneo.

Advertencia de definiciones: «nodos» de alfa-beta = llamadas recursivas sobre una
posicion (S-02); «nodos» de MCTS = nodos creados en el arbol (uno por simulacion
como maximo). No son comparables entre si; solo se comparan dentro de una familia.
"""
from __future__ import annotations

import csv
import os
import statistics

import chess

from chess_ai.environment import Deadline, SearchTimeout, is_mate_score
from chess_ai.evaluation import DEFAULT_EVALUATOR
from chess_ai.search import (MINIMAX_DEFENSE_FEN, AlphaBetaImprovedAgent, SearchContext,
                             _search_alphabeta, search_root)
from chess_ai.mcts import (mcts_benchmark_summary, mcts_non_monotonic_cases,
                           mcts_rows_to_csv, mcts_tactics_benchmark)
from chess_ai.tuning import _tune_project_root
from chess_ai.tournament import (ABLATION_E0_LABEL, ABLATION_ESTAR_LABEL, OPENINGS,
                                 TOURNAMENT_OPENING_IDS, TournamentConfig, decision_mover,
                                 load_tournament, opening_board, paired_schedule,
                                 pairwise_table, read_typed_csv, run_tournament,
                                 score_interval, standings)

EXP_RESULTS_DIR = os.path.join(_tune_project_root(), "resultados")
# Paleta categorica fija (orden estable: el color sigue a la entidad).
EXP_COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
EXP_INK, EXP_MUTED = "#0b0b0b", "#52514e"

# --------------------------------------------------------------------- Experimento 1
EXP1_POSITIONS = [
    {"id": "P1_captura", "character": "captura",
     "description": "Escocesa tras 3.d4: negras al turno con exd4 y Cxd4 disponibles",
     "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq - 0 3"},
    {"id": "P2_jaque", "character": "jaque",
     "description": "Centro 1.e4 e5 2.d4 exd4 3.Dxd4 Cc6 4.De3 Ab4+: blancas en jaque",
     "fen": "r1bqk1nr/pppp1ppp/2n5/8/1b2P3/4Q3/PPP2PPP/RNB1KBNR w KQkq - 3 5"},
    {"id": "P3_defensa", "character": "defensa",
     "description": "Caballo d4 atacado por e5 y cebo en h5 (MINIMAX_DEFENSE_FEN, pregunta 1)",
     "fen": MINIMAX_DEFENSE_FEN},
    {"id": "P4_tranquila", "character": "tranquila",
     "description": "Sistema Londres tras 6...Ad6: desarrollo sin amenazas inmediatas",
     "fen": "r1bqk2r/pp3ppp/2nbpn2/2pp4/3P1B2/2P1PN2/PP1N1PPP/R2QKB1R w KQkq - 3 7"},
    {"id": "P5_final", "character": "final",
     "description": "Final de torres con peones (3 contra 3)",
     "fen": "8/5pk1/6p1/p7/P2R4/6P1/2r2PK1/8 w - - 0 40"},
]
EXP1_ALGORITHMS = (("Minimax", "minimax", False), ("Alfa-beta natural", "alphabeta", False),
                   ("Alfa-beta ordenado", "alphabeta", True))
EXP1_FIELDS = ["position_id", "character", "turn", "depth", "algorithm", "value", "move",
               "nodes", "leaves", "cutoffs", "time_s", "sort_time_s", "search_time_s",
               "nodes_vs_minimax", "time_vs_minimax"]


def _exp_write_csv(path, rows, fields=None) -> None:
    if not path or not rows:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fields})


def run_exp1(depths=(1, 2, 3), positions=None, evaluator=DEFAULT_EVALUATOR,
             out_path: str | None = None) -> list:
    """Minimax / alfa-beta natural / alfa-beta ordenado con E fija a cada profundidad.

    Comprueba (assert) que los tres valores coinciden y que el tablero queda intacto.
    `time_s` incluye el tiempo de ordenar; `search_time_s` = time_s - sort_time_s.
    """
    rows = []
    for pos in positions or EXP1_POSITIONS:
        board = chess.Board(pos["fen"])
        assert board.is_valid(), (pos["id"], board.status())
        fen0 = board.fen()
        for depth in depths:
            base = None
            for label, algo, ordering in EXP1_ALGORITHMS:
                r = search_root(board, algo, depth, evaluator, ordering)
                assert board.fen() == fen0 and not board.move_stack, "tablero modificado"
                if base is None:
                    base = r
                assert abs(r.value - base.value) < 1e-6, (pos["id"], depth, label, r.value, base.value)
                rows.append({
                    "position_id": pos["id"], "character": pos["character"],
                    "turn": "blancas" if board.turn else "negras", "depth": depth,
                    "algorithm": label, "value": round(r.value, 2),
                    "move": r.move.uci() if r.move else "", "nodes": r.stats.nodes,
                    "leaves": r.stats.leaves, "cutoffs": r.stats.cutoffs,
                    "time_s": round(r.stats.elapsed_s, 5), "sort_time_s": round(r.sort_time, 5),
                    "search_time_s": round(r.stats.elapsed_s - r.sort_time, 5),
                    "nodes_vs_minimax": round(r.stats.nodes / base.stats.nodes, 4),
                    "time_vs_minimax": round(r.stats.elapsed_s / base.stats.elapsed_s, 4)
                    if base.stats.elapsed_s > 0 else ""})
    _exp_write_csv(out_path, rows, EXP1_FIELDS)
    return rows


def exp1_load(path: str | None = None) -> list:
    path = path or os.path.join(EXP_RESULTS_DIR, "exp1_ahorro.csv")
    rows = read_typed_csv(path)
    for r in rows:
        for k in ("depth", "nodes", "leaves", "cutoffs"):
            r[k] = int(r[k])
        for k in ("value", "time_s", "sort_time_s", "search_time_s", "nodes_vs_minimax"):
            r[k] = float(r[k])
    return rows


def exp1_summary(rows) -> list:
    """Totales sobre las 5 posiciones por profundidad y algoritmo (+ razon frente a minimax)."""
    out = []
    for depth in sorted({r["depth"] for r in rows}):
        base_nodes = sum(r["nodes"] for r in rows if r["depth"] == depth and r["algorithm"] == "Minimax")
        base_time = sum(r["time_s"] for r in rows if r["depth"] == depth and r["algorithm"] == "Minimax")
        for label, _, _ in EXP1_ALGORITHMS:
            sel = [r for r in rows if r["depth"] == depth and r["algorithm"] == label]
            if not sel:
                continue
            nodes = sum(r["nodes"] for r in sel)
            t = sum(r["time_s"] for r in sel)
            out.append({"depth": depth, "algorithm": label, "nodes": nodes,
                        "leaves": sum(r["leaves"] for r in sel),
                        "cutoffs": sum(r["cutoffs"] for r in sel), "time_s": round(t, 4),
                        "sort_time_s": round(sum(r["sort_time_s"] for r in sel), 4),
                        "nodes_vs_minimax": round(nodes / base_nodes, 4) if base_nodes else None,
                        "time_vs_minimax": round(t / base_time, 4) if base_time else None})
    return out


# ---------------------------------------------------------- profundidad contra plazo
def _exp_iterative_depth(board: chess.Board, time_limit_s: float, ordering: bool,
                         evaluator=DEFAULT_EVALUATOR, max_depth: int = 8) -> tuple:
    """Profundizacion iterativa identica a la del mejorado, con o sin ordenacion.

    Con `ordering=False` no hay PV previa, MVV-LVA ni killers (orden natural): es la
    ablacion «ordenacion si/no» con plazo. Devuelve (profundidad completada, nodos).
    """
    deadline = Deadline(time_limit_s)
    ctx = SearchContext(evaluator, deadline=deadline, ordering=ordering)
    completed = 0
    for depth in range(1, max_depth + 1):
        if deadline.expired():
            break
        try:
            value = _search_alphabeta(board, depth, 0, -float("inf"), float("inf"), ctx)
        except SearchTimeout:
            break
        completed = depth
        ctx.prev_pv = list(ctx.pv[0])
        if is_mate_score(value):
            break
    return completed, ctx.stats.nodes


def depth_time_positions() -> list:
    """Posiciones de la curva profundidad-plazo: aperturas del torneo + las del Exp. 1."""
    out = [(o, opening_board(o).fen()) for o in TOURNAMENT_OPENING_IDS[:4]]
    out += [(p["id"], p["fen"]) for p in EXP1_POSITIONS]
    return out


def run_depth_vs_time(budgets=(0.05, 0.1, 0.2, 0.5, 1.0), positions=None,
                      out_path: str | None = None, n_positions: int | None = None) -> list:
    """Profundidad completada por el mejorado (con ordenacion) y por la misma
    profundizacion sin ordenacion, para varios plazos y posiciones."""
    positions = positions or depth_time_positions()
    if n_positions:
        positions = positions[:n_positions]
    rows = []
    for pid, fen in positions:
        for budget in budgets:
            board = chess.Board(fen)
            d = AlphaBetaImprovedAgent().choose(board, time_limit_s=budget)
            rows.append({"position_id": pid, "budget_s": budget, "ordering": 1,
                         "completed_depth": d.stats.completed_depth, "nodes": d.stats.nodes,
                         "elapsed_s": round(d.stats.elapsed_s, 4)})
            depth, nodes = _exp_iterative_depth(chess.Board(fen), budget, ordering=False)
            rows.append({"position_id": pid, "budget_s": budget, "ordering": 0,
                         "completed_depth": depth, "nodes": nodes, "elapsed_s": budget})
    _exp_write_csv(out_path, rows)
    return rows


def depth_time_load(path: str | None = None) -> list:
    rows = read_typed_csv(path or os.path.join(EXP_RESULTS_DIR, "exp_profundidad_tiempo.csv"))
    for r in rows:
        r["budget_s"] = float(r["budget_s"])
        for k in ("ordering", "completed_depth", "nodes"):
            r[k] = int(r[k])
    return rows


def depth_time_summary(rows) -> list:
    out = []
    for budget in sorted({r["budget_s"] for r in rows}):
        for ordering in (1, 0):
            sel = [r["completed_depth"] for r in rows
                   if r["budget_s"] == budget and r["ordering"] == ordering]
            if sel:
                out.append({"budget_s": budget, "ordering": ordering, "n": len(sel),
                            "depth_mean": round(statistics.mean(sel), 3),
                            "depth_min": min(sel), "depth_max": max(sel)})
    return out


# --------------------------------------------------------------------- Experimento 2
def tournament_analysis(data: dict) -> dict:
    """Resumen del torneo guardado: clasificacion, cruces, terminaciones, excesos,
    profundidad del mejorado y simulaciones de MCTS por jugada."""
    games, decisions = data["games"], data["decisions"]
    table = standings(games)
    terminations = {}
    for g in games:
        terminations[g["termination"]] = terminations.get(g["termination"], 0) + 1
    by_agent = {}
    for row in decisions:
        by_agent.setdefault(decision_mover(row), []).append(row)
    per_agent = {}
    for lab, rows in by_agent.items():
        times = [r["elapsed_s"] for r in rows]
        per_agent[lab] = {
            "jugadas": len(rows), "tiempo_medio_s": round(statistics.mean(times), 4),
            "tiempo_desv_s": round(statistics.pstdev(times), 4), "tiempo_max_s": round(max(times), 4),
            "excesos": sum(r["time_exceeded"] for r in rows),
            "prop_excesos": round(sum(r["time_exceeded"] for r in rows) / len(rows), 4),
            "nodos_medios": round(statistics.mean(r["nodes"] for r in rows), 1)}
    imp = [r["completed_depth"] for r in by_agent.get("Alfa-beta mejorado", [])]
    sims = [r["simulations"] for r in by_agent.get("MCTS", [])]
    out = {"standings": table, "pairwise": pairwise_table(games), "terminations": terminations,
           "n_games": len(games), "truncated": sum(int(g["truncated"]) for g in games),
           "per_agent": per_agent}
    if imp:
        out["improved_depth"] = {"mean": round(statistics.mean(imp), 3),
                                 "dist": {d: imp.count(d) for d in sorted(set(imp))}}
    if sims:
        s = sorted(sims)
        out["mcts_simulations"] = {"mean": round(statistics.mean(s), 1),
                                   "std": round(statistics.pstdev(s), 1), "min": s[0],
                                   "p10": s[len(s) // 10], "median": s[len(s) // 2],
                                   "p90": s[(9 * len(s)) // 10], "max": s[-1]}
    return out


def pairwise_markdown(pairwise: dict, agents) -> str:
    """Matriz de cruces: puntos de la fila contra la columna / terminadas (truncadas)."""
    head = "| Fila contra columna | " + " | ".join(agents) + " |"
    lines = [head, "|---" * (len(agents) + 1) + "|"]
    for a in agents:
        cells = []
        for b in agents:
            if a == b:
                cells.append("—")
                continue
            c = pairwise[(a, b)]
            cells.append(f"{c['puntos_A']:g}/{c['terminadas']} ({c['truncadas']}t)")
        lines.append(f"| {a} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------- Experimento 3
ABLATION_OPENING_IDS = tuple(o["id"] for o in OPENINGS)     # las 16 aperturas
ABLATION_RIVAL = "Minimax"   # en el piloto empato ~50 % con el mejorado: rival informativo


def ablation_config(rapido: bool = False) -> TournamentConfig:
    if rapido:
        return TournamentConfig(agents=(ABLATION_E0_LABEL, ABLATION_ESTAR_LABEL, "Voraz"),
                                opening_ids=ABLATION_OPENING_IDS[:1], time_limit_s=0.05,
                                max_plies=16, seed_base=500_000, game_prefix="X",
                                event="Taller 3 IA UTP - ablacion RAPIDA de prueba")
    return TournamentConfig(agents=(ABLATION_E0_LABEL, ABLATION_ESTAR_LABEL, ABLATION_RIVAL),
                            opening_ids=ABLATION_OPENING_IDS, seed_base=500_000,
                            game_prefix="X", event="Taller 3 IA UTP - ablacion E0 vs E* (Experimento 3)")


def run_ablation(out_dir: str | None = None, workers: int = 1, rapido: bool = False,
                 rival: str = ABLATION_RIVAL, progress=print) -> dict:
    """E0 contra E* (mismo agente mejorado, mismo plazo, mismas aperturas, colores
    intercambiados) y ambos contra un rival comun. Escribe exp3_ablacion_*."""
    cfg = ablation_config(rapido)
    if not rapido:
        cfg.agents = (ABLATION_E0_LABEL, ABLATION_ESTAR_LABEL, rival)
    r = cfg.agents[2]
    schedule = paired_schedule(cfg, [(ABLATION_E0_LABEL, ABLATION_ESTAR_LABEL),
                                     (ABLATION_E0_LABEL, r), (ABLATION_ESTAR_LABEL, r)])
    res = run_tournament(cfg, schedule=schedule, workers=workers, out_dir=out_dir,
                         prefix="exp3_ablacion", progress=progress)
    if out_dir:
        ablation_summary(res["games"], out_path=os.path.join(out_dir, "exp3_ablacion_resumen.csv"))
    return res


def _exp_side_scores(games, label, opponent):
    """Puntos de `label` contra `opponent` en terminadas + material final en truncadas."""
    scores, material, n, trunc = [], [], 0, 0
    for g in games:
        if {g["white_agent"], g["black_agent"]} != {label, opponent}:
            continue
        n += 1
        side = "white" if g["white_agent"] == label else "black"
        if int(g["truncated"]) or g["official_result"] == "*":
            trunc += 1
            m = float(g["material_white_final"])
            material.append(m if side == "white" else -m)
            continue
        scores.append(float(g[f"{side}_points"]))
    return scores, material, n, trunc


ABLATION_SUMMARY_FIELDS = ["comparacion", "agente", "rival", "partidas", "terminadas", "truncadas",
                           "victorias", "tablas", "derrotas", "puntos", "puntuacion_media",
                           "ic95_bajo", "ic95_alto", "material_medio_truncadas_no_oficial"]


def ablation_summary(games, out_path: str | None = None) -> list:
    """Puntuacion con IC 95 % bootstrap (solo terminadas) y, aparte y rotulado como no
    oficial, el balance medio de material al truncar."""
    labels = sorted({g["white_agent"] for g in games} | {g["black_agent"] for g in games})
    rival = [x for x in labels if x not in (ABLATION_E0_LABEL, ABLATION_ESTAR_LABEL)]
    comps = [("E* contra E0 (directo)", ABLATION_ESTAR_LABEL, ABLATION_E0_LABEL)]
    for r in rival:
        comps += [(f"E0 contra {r}", ABLATION_E0_LABEL, r), (f"E* contra {r}", ABLATION_ESTAR_LABEL, r)]
    rows = []
    for name, a, b in comps:
        scores, material, n, trunc = _exp_side_scores(games, a, b)
        if n == 0:
            continue
        ci = score_interval(scores)
        rows.append({"comparacion": name, "agente": a, "rival": b, "partidas": n,
                     "terminadas": len(scores), "truncadas": trunc,
                     "victorias": scores.count(1.0), "tablas": scores.count(0.5),
                     "derrotas": scores.count(0.0), "puntos": sum(scores),
                     "puntuacion_media": ci["mean"], "ic95_bajo": ci["low"], "ic95_alto": ci["high"],
                     "material_medio_truncadas_no_oficial":
                         round(statistics.mean(material), 2) if material else ""})
    _exp_write_csv(out_path, rows, ABLATION_SUMMARY_FIELDS)
    return rows


def ablation_load(out_dir: str | None = None) -> dict:
    out_dir = out_dir or EXP_RESULTS_DIR
    data = load_tournament(out_dir, prefix="exp3_ablacion")
    path = os.path.join(out_dir, "exp3_ablacion_resumen.csv")
    data["summary"] = read_typed_csv(path) if os.path.exists(path) else ablation_summary(data["games"])
    return data


def ablation_depths(decisions) -> dict:
    """Profundidad media completada por etiqueta (E0 y E* cuestan lo mismo de evaluar)."""
    out = {}
    for row in decisions:
        out.setdefault(decision_mover(row), []).append(row["completed_depth"])
    return {k: round(statistics.mean(v), 3) for k, v in out.items()}


def ordering_ablation(exp1_rows, depth_rows) -> list:
    """Ablacion de la ordenacion: profundidad fija (Exp. 1) y con plazo (curva)."""
    out = []
    for depth in sorted({r["depth"] for r in exp1_rows}):
        nat = [r for r in exp1_rows if r["depth"] == depth and r["algorithm"] == "Alfa-beta natural"]
        ordd = [r for r in exp1_rows if r["depth"] == depth and r["algorithm"] == "Alfa-beta ordenado"]
        n_nat, n_ord = sum(r["nodes"] for r in nat), sum(r["nodes"] for r in ordd)
        t_nat, t_ord = sum(r["time_s"] for r in nat), sum(r["time_s"] for r in ordd)
        out.append({"modo": "profundidad fija", "parametro": f"d={depth}",
                    "sin_ordenacion": n_nat, "con_ordenacion": n_ord, "medida": "nodos (5 posiciones)",
                    "razon_con_sin": round(n_ord / n_nat, 4) if n_nat else None,
                    "tiempo_sin_s": round(t_nat, 4), "tiempo_con_s": round(t_ord, 4),
                    "tiempo_ordenar_s": round(sum(r["sort_time_s"] for r in ordd), 4)})
    for s in depth_time_summary(depth_rows):
        if s["ordering"] != 1:
            continue
        nat = [x for x in depth_time_summary(depth_rows)
               if x["budget_s"] == s["budget_s"] and x["ordering"] == 0][0]
        out.append({"modo": "plazo", "parametro": f"{s['budget_s']} s",
                    "sin_ordenacion": nat["depth_mean"], "con_ordenacion": s["depth_mean"],
                    "medida": f"profundidad media completada ({s['n']} posiciones)",
                    "razon_con_sin": round(s["depth_mean"] / nat["depth_mean"], 4)
                    if nat["depth_mean"] else None})
    return out


# --------------------------------------------------------------------- Experimento 4
EXP4_CONFIGS = {"captures_L4": {}, "eval_L0": {"rollout_limit": 0},
                "uniform_L8": {"rollout_policy": "uniform", "rollout_limit": 8}}


def run_exp4(path: str | None = None, budgets=(50, 200, 800, 2000), seeds=range(5),
             only_default: bool = False) -> list:
    """Regenera el benchmark de tacticas (misma funcion que la etapa de MCTS)."""
    rows = []
    for label, kwargs in EXP4_CONFIGS.items():
        if only_default and label != "captures_L4":
            continue
        rows += mcts_tactics_benchmark(budgets=budgets, seeds=seeds, label=label, **kwargs)
    if path:
        mcts_rows_to_csv(rows, path)
    return rows


def exp4_load(path: str | None = None) -> list:
    path = path or os.path.join(EXP_RESULTS_DIR, "mcts_tacticas.csv")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ("budget", "seed", "correct", "simulations", "nodes", "leaves", "max_depth"):
            r[k] = int(r[k])
        r["elapsed_s"] = float(r["elapsed_s"])
    return rows


def exp4_summary(rows) -> dict:
    """Tasa de acierto por presupuesto (con desviacion ENTRE semillas), tiempos y
    casos no monotonos por semilla."""
    by_budget = mcts_benchmark_summary(rows)
    for s in by_budget:
        sel = [r for r in rows if r["config"] == s["config"] and r["budget"] == s["budget"]]
        per_seed = []
        for seed in sorted({r["seed"] for r in sel}):
            hits = [r["correct"] for r in sel if r["seed"] == seed]
            per_seed.append(sum(hits) / len(hits))
        s["hit_rate_seed_std"] = round(statistics.pstdev(per_seed), 4)
        s["hit_rate_seed_min"] = min(per_seed)
        s["hit_rate_seed_max"] = max(per_seed)
        s["hit_rate"] = round(s["hit_rate"], 4)
        s["time_mean_s"] = round(s["time_mean_s"], 5)
        s["time_std_s"] = round(s["time_std_s"], 5)
    by_tactic = {}
    for r in rows:
        if r["config"] != "captures_L4":
            continue
        by_tactic.setdefault(r["tactic"], {}).setdefault(r["budget"], []).append(r["correct"])
    tactic_table = [{"tactic": t, **{f"b{b}": f"{sum(v)}/{len(v)}" for b, v in sorted(d.items())}}
                    for t, d in by_tactic.items()]
    return {"by_budget": by_budget, "by_tactic": tactic_table,
            "non_monotonic": mcts_non_monotonic_cases(rows)}


# --------------------------------------------------------------------- graficas
def _exp_plt():
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                                "axes.edgecolor": EXP_MUTED, "axes.labelcolor": EXP_INK,
                                "xtick.color": EXP_MUTED, "ytick.color": EXP_MUTED,
                                "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
                                "axes.axisbelow": True, "font.size": 9})
    return plt


def _exp_save(fig, path):
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="white")
    return fig


def fig_exp1_nodes(rows, path: str | None = None):
    """Barras de nodos por algoritmo y posicion, un panel por profundidad (escala log)."""
    plt = _exp_plt()
    depths = sorted({r["depth"] for r in rows})
    positions = [p["id"] for p in EXP1_POSITIONS if any(r["position_id"] == p["id"] for r in rows)]
    fig, axes = plt.subplots(1, len(depths), figsize=(4.2 * len(depths), 3.6), sharey=False)
    axes = axes if len(depths) > 1 else [axes]
    width = 0.26
    for ax, depth in zip(axes, depths):
        for i, (label, _, _) in enumerate(EXP1_ALGORITHMS):
            vals = [next(r["nodes"] for r in rows if r["depth"] == depth and r["position_id"] == p
                         and r["algorithm"] == label) for p in positions]
            xs = [k + (i - 1) * width for k in range(len(positions))]
            ax.bar(xs, vals, width * 0.92, color=EXP_COLORS[i], label=label)
        ax.set_yscale("log")
        ax.set_title(f"Profundidad {depth}", color=EXP_INK)
        ax.set_xticks(range(len(positions)))
        ax.set_xticklabels([p.split("_", 1)[1] for p in positions], rotation=20)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("nodos visitados (escala log)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Experimento 1: nodos de minimax y alfa-beta con la misma E0 (mismo valor)",
                 color=EXP_INK)
    fig.tight_layout()
    return _exp_save(fig, path)


def fig_depth_time(rows, path: str | None = None):
    """Profundidad completada contra plazo: mejorado (con ordenacion) vs sin ordenacion."""
    plt = _exp_plt()
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for ordering, color, label in ((1, EXP_COLORS[0], "con ordenacion (agente mejorado)"),
                                   (0, EXP_COLORS[1], "sin ordenacion (orden natural)")):
        summ = [s for s in depth_time_summary(rows) if s["ordering"] == ordering]
        xs = [s["budget_s"] for s in summ]
        ax.fill_between(xs, [s["depth_min"] for s in summ], [s["depth_max"] for s in summ],
                        color=color, alpha=0.12, linewidth=0)
        ax.plot(xs, [s["depth_mean"] for s in summ], "-o", color=color, lw=2, ms=6, label=label)
    ax.set_xscale("log")
    ax.set_xticks(sorted({r["budget_s"] for r in rows}))
    ax.set_xticklabels([f"{b:g}" for b in sorted({r["budget_s"] for r in rows})])
    ax.set_xlabel("plazo por decision (s, escala log)")
    ax.set_ylabel("profundidad completada")
    ax.set_title("Profundizacion iterativa: media y rango sobre "
                 f"{len({r['position_id'] for r in rows})} posiciones", color=EXP_INK)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return _exp_save(fig, path)


def fig_mcts_budget(rows, path: str | None = None):
    """Tasa de acierto de MCTS por presupuesto (barras de error = desviacion entre
    semillas) y tiempo medio por decision."""
    plt = _exp_plt()
    summ = exp4_summary(rows)["by_budget"]
    configs = list(dict.fromkeys(s["config"] for s in summ))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 3.6))
    for i, cfg in enumerate(configs):
        sel = [s for s in summ if s["config"] == cfg]
        xs = [s["budget"] for s in sel]
        a1.errorbar(xs, [s["hit_rate"] for s in sel], yerr=[s["hit_rate_seed_std"] for s in sel],
                    fmt="-o", color=EXP_COLORS[i], lw=2, ms=6, capsize=3, label=cfg)
        a2.errorbar(xs, [s["time_mean_s"] for s in sel], yerr=[s["time_std_s"] for s in sel],
                    fmt="-o", color=EXP_COLORS[i], lw=2, ms=6, capsize=3, label=cfg)
    for ax in (a1, a2):
        ax.set_xscale("log")
        ax.set_xlabel("simulaciones por decision (escala log)")
    a1.set_ylim(0, 1.05)
    a1.set_ylabel("tasa de acierto (10 tacticas)")
    a1.set_title("Acierto tactico (± desv. entre 5 semillas)", color=EXP_INK)
    a2.set_yscale("log")
    a2.set_ylabel("tiempo por decision (s, log)")
    a2.set_title("Tiempo medio (± desv.)", color=EXP_INK)
    a1.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    return _exp_save(fig, path)


def fig_tournament(table, path: str | None = None):
    """Victorias, tablas, derrotas y truncadas por agente; puntos/terminadas a la derecha."""
    plt = _exp_plt()
    table = list(table)[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    names = [r["agente"] for r in table]
    left = [0] * len(table)
    parts = (("victorias", "victorias", EXP_COLORS[2]), ("tablas", "tablas", "#b9b8b2"),
             ("derrotas", "derrotas", EXP_COLORS[7]), ("truncadas", "truncadas (sin resultado)", "#e4e3df"))
    for key, label, color in parts:
        vals = [r[key] for r in table]
        ax.barh(names, vals, left=left, color=color, label=label, edgecolor="white", linewidth=1.5)
        left = [a + b for a, b in zip(left, vals)]
    for k, r in enumerate(table):
        ppt = r["puntos_por_terminada"]
        txt = f"{r['puntos']:g}/{r['terminadas']}" + (f" = {ppt:.2f}" if ppt is not None else "")
        ax.text(left[k] + 0.5, k, txt, va="center", color=EXP_INK)
    ax.set_xlim(0, max(left) * 1.3)
    ax.set_xlabel("partidas")
    ax.grid(axis="y", visible=False)
    ax.set_title("Experimento 2: resultados por agente (puntos / partidas terminadas)", color=EXP_INK)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.45, -0.18))
    fig.tight_layout()
    return _exp_save(fig, path)


def fig_ablation(summary, ordering_rows, path: str | None = None):
    """Izquierda: puntuacion (IC 95 %) de E* y E0. Derecha: ahorro por la ordenacion."""
    plt = _exp_plt()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
    summary = list(summary)
    names = [s["comparacion"] for s in summary]
    for k, s in enumerate(summary):
        if s["puntuacion_media"] in ("", None):
            continue
        m, lo, hi = float(s["puntuacion_media"]), float(s["ic95_bajo"]), float(s["ic95_alto"])
        color = EXP_COLORS[1] if "E*" in s["agente"] else EXP_COLORS[0]
        a1.errorbar([m], [k], xerr=[[m - lo], [hi - m]], fmt="o", color=color, ms=8, capsize=4, lw=2)
        a1.text(1.02, k, f"{int(s['terminadas'])} term. / {int(s['truncadas'])} trunc.",
                va="center", color=EXP_MUTED, transform=a1.get_yaxis_transform())
    a1.axvline(0.5, color=EXP_MUTED, lw=1, ls="--")
    a1.set_yticks(range(len(names)))
    a1.set_yticklabels(names)
    a1.set_xlim(-0.03, 1.03)
    a1.set_xlabel("puntuacion media del agente (terminadas, IC 95 % bootstrap)")
    a1.set_title("Ablacion de la mejora: E0 vs E*", color=EXP_INK)
    a1.grid(axis="y", visible=False)
    fixed = [r for r in ordering_rows if r["modo"] == "profundidad fija"]
    timed = [r for r in ordering_rows if r["modo"] == "plazo"]
    xs = list(range(len(fixed)))
    a2.bar([x - 0.2 for x in xs], [r["sin_ordenacion"] for r in fixed], 0.38,
           color=EXP_COLORS[1], label="sin ordenacion")
    a2.bar([x + 0.2 for x in xs], [r["con_ordenacion"] for r in fixed], 0.38,
           color=EXP_COLORS[0], label="con ordenacion")
    a2.set_yscale("log")
    a2.set_xticks(xs)
    a2.set_xticklabels([r["parametro"] for r in fixed])
    a2.set_ylabel("nodos totales (5 posiciones, log)")
    a2.grid(axis="x", visible=False)
    sub = ", ".join(f"{r['parametro']}: {r['sin_ordenacion']:.2f}->{r['con_ordenacion']:.2f}"
                    for r in timed if r["parametro"] in ("0.2 s", "1.0 s"))
    a2.set_title("Ablacion de la ordenacion (profundidad fija)", color=EXP_INK)
    if sub:
        a2.text(0.02, -0.22, "Profundidad media con plazo " + sub, transform=a2.transAxes,
                color=EXP_MUTED)
    a2.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return _exp_save(fig, path)


def make_all_figures(out_dir: str | None = None) -> list:
    """Regenera todas las PNG desde los CSV que existan en `out_dir`."""
    plt = _exp_plt()
    out_dir = out_dir or EXP_RESULTS_DIR
    made = []

    def _p(name):
        return os.path.join(out_dir, name)

    exp1 = exp1_load(_p("exp1_ahorro.csv")) if os.path.exists(_p("exp1_ahorro.csv")) else None
    dt = (depth_time_load(_p("exp_profundidad_tiempo.csv"))
          if os.path.exists(_p("exp_profundidad_tiempo.csv")) else None)
    if exp1:
        plt.close(fig_exp1_nodes(exp1, _p("fig_exp1_nodos.png")))
        made.append(_p("fig_exp1_nodos.png"))
    if dt:
        plt.close(fig_depth_time(dt, _p("fig_profundidad_tiempo.png")))
        made.append(_p("fig_profundidad_tiempo.png"))
    mcts_path = _p("mcts_tacticas.csv")
    if not os.path.exists(mcts_path):
        mcts_path = os.path.join(EXP_RESULTS_DIR, "mcts_tacticas.csv")
    if os.path.exists(mcts_path):
        plt.close(fig_mcts_budget(exp4_load(mcts_path), _p("fig_mcts_presupuesto.png")))
        made.append(_p("fig_mcts_presupuesto.png"))
    if os.path.exists(_p("torneo_partidas.csv")):
        data = load_tournament(out_dir, "torneo")
        plt.close(fig_tournament(standings(data["games"]), _p("fig_torneo.png")))
        made.append(_p("fig_torneo.png"))
    if os.path.exists(_p("exp3_ablacion_partidas.csv")) and exp1 and dt:
        ab = ablation_load(out_dir)
        plt.close(fig_ablation(ab["summary"], ordering_ablation(exp1, dt), _p("fig_ablacion.png")))
        made.append(_p("fig_ablacion.png"))
    return made
