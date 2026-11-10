# -*- coding: utf-8 -*-
"""Ejecuta los experimentos pesados de la seccion 9 y escribe `resultados/`.

Uso (con el Python del entorno ia-taller3, desde la raiz del proyecto):

    python tools/correr_experimentos.py                       # todo (exp1, torneo, ablacion, mcts, figuras)
    python tools/correr_experimentos.py --solo exp1           # Experimento 1 (segundos)
    python tools/correr_experimentos.py --solo torneo --workers 4
    python tools/correr_experimentos.py --solo ablacion --workers 4
    python tools/correr_experimentos.py --solo mcts           # resume resultados/mcts_tacticas.csv
    python tools/correr_experimentos.py --solo mcts --regenerar-mcts   # vuelve a correr el benchmark
    python tools/correr_experimentos.py --solo profundidad    # curvas profundidad-plazo
    python tools/correr_experimentos.py --solo figuras        # solo regenera PNG desde los CSV
    python tools/correr_experimentos.py --rapido              # version corta de prueba (resultados/tmp/)

`--solo` acepta varios valores separados por coma. La salida de consola conviene
redirigirla a un `*.log` (ignorado por git):

    python tools/correr_experimentos.py --solo torneo --workers 4 > torneo.log 2>&1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

os.environ.setdefault("MPLBACKEND", "Agg")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

PASOS = ("exp1", "torneo", "ablacion", "mcts", "profundidad", "figuras")


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def paso_exp1(out_dir: str, rapido: bool) -> None:
    from chess_ai.experiments import run_exp1, exp1_summary
    rows = run_exp1(depths=(1, 2) if rapido else (1, 2, 3),
                    out_path=os.path.join(out_dir, "exp1_ahorro.csv"))
    for r in exp1_summary(rows):
        _log(f"exp1 {r}")


def paso_torneo(out_dir: str, rapido: bool, workers: int) -> None:
    from chess_ai.tournament import (TournamentConfig, parallel_load_check, run_tournament,
                                     standings, standings_markdown)
    if rapido:
        cfg = TournamentConfig(agents=("Aleatorio", "Voraz", "Alfa-beta mejorado"),
                               opening_ids=("A1_italiana",), time_limit_s=0.05, max_plies=16,
                               event="Taller 3 IA UTP - torneo RAPIDO de prueba")
        check = None
    else:
        cfg = TournamentConfig()
        check = None
        if workers > 1:
            _log(f"verificando carga en paralelo con {workers} procesos ...")
            check = parallel_load_check(workers)
            _log(f"carga: {json.dumps(check)}")
            with open(os.path.join(out_dir, "torneo_carga_paralela.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(check, fh, ensure_ascii=False, indent=2)
    res = run_tournament(cfg, workers=workers, out_dir=out_dir, prefix="torneo", progress=_log,
                         extra_config={"parallel_load_check": check} if check else None)
    _log(f"torneo: {len(res['games'])} partidas en {res['config']['duration_wall_s']} s")
    print(standings_markdown(standings(res["games"])), flush=True)


def paso_ablacion(out_dir: str, rapido: bool, workers: int, rival: str | None) -> None:
    from chess_ai.experiments import run_ablation, ablation_summary, ABLATION_RIVAL
    res = run_ablation(out_dir=out_dir, workers=workers, rapido=rapido,
                       rival=rival or ABLATION_RIVAL, progress=_log)
    for r in ablation_summary(res["games"], out_path=None):
        _log(f"ablacion {r}")


def paso_mcts(out_dir: str, rapido: bool, regenerar: bool) -> None:
    from chess_ai.experiments import exp4_load, exp4_summary, run_exp4
    path = os.path.join(out_dir, "mcts_tacticas.csv")
    if regenerar or rapido:
        run_exp4(path, budgets=(20, 50, 100) if rapido else (50, 200, 800, 2000),
                 seeds=range(2) if rapido else range(5), only_default=rapido)
    for r in exp4_summary(exp4_load(path))["by_budget"]:
        _log(f"exp4 {r}")


def paso_profundidad(out_dir: str, rapido: bool) -> None:
    from chess_ai.experiments import run_depth_vs_time
    rows = run_depth_vs_time(budgets=(0.05, 0.1) if rapido else (0.05, 0.1, 0.2, 0.5, 1.0),
                             out_path=os.path.join(out_dir, "exp_profundidad_tiempo.csv"),
                             n_positions=2 if rapido else None)
    _log(f"profundidad: {len(rows)} mediciones")


def paso_figuras(out_dir: str) -> None:
    from chess_ai.experiments import make_all_figures
    for path in make_all_figures(out_dir):
        _log(f"figura {path}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", default="", help="pasos separados por coma: " + ",".join(PASOS))
    parser.add_argument("--workers", type=int, default=1, help="procesos para torneo/ablacion (<= 4)")
    parser.add_argument("--rapido", action="store_true",
                        help="version corta de prueba; escribe en resultados/tmp/")
    parser.add_argument("--regenerar-mcts", action="store_true",
                        help="vuelve a correr el benchmark de tacticas de MCTS")
    parser.add_argument("--rival", default=None, help="rival comun de la ablacion")
    parser.add_argument("--salida", default=None, help="carpeta de salida (por omision resultados/)")
    args = parser.parse_args(argv)

    pasos = [p.strip() for p in args.solo.split(",") if p.strip()] or list(PASOS)
    for p in pasos:
        if p not in PASOS:
            parser.error(f"paso desconocido {p!r}; opciones: {', '.join(PASOS)}")
    if args.workers > 4:
        parser.error("use como maximo 4 procesos: mas procesos roban CPU a los agentes por plazo")
    out_dir = args.salida or os.path.join(RAIZ, "resultados", "tmp" if args.rapido else "")
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    os.chdir(RAIZ)

    t0 = time.perf_counter()
    for p in pasos:
        tp = time.perf_counter()
        _log(f"=== paso {p} (salida {out_dir}) ===")
        if p == "exp1":
            paso_exp1(out_dir, args.rapido)
        elif p == "torneo":
            paso_torneo(out_dir, args.rapido, args.workers)
        elif p == "ablacion":
            paso_ablacion(out_dir, args.rapido, args.workers, args.rival)
        elif p == "mcts":
            paso_mcts(out_dir, args.rapido, args.regenerar_mcts)
        elif p == "profundidad":
            paso_profundidad(out_dir, args.rapido)
        elif p == "figuras":
            paso_figuras(out_dir)
        _log(f"=== paso {p} terminado en {time.perf_counter() - tp:.1f} s ===")
    _log(f"total {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
