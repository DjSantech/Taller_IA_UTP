# ===== Experimento 4: MCTS por presupuesto de simulaciones y semilla (resultados guardados) =====
# El benchmark completo (3 configuraciones x 4 presupuestos x 5 semillas x 10 tacticas = 600 filas)
# tarda varios minutos; aqui se carga resultados/mcts_tacticas.csv y se REPITE en vivo una muestra
# para comprobar que, con simulaciones fijas, el resultado es exactamente reproducible.
import os

import matplotlib.pyplot as plt
from IPython.display import Markdown, display

_ruta_mcts = os.path.join("resultados", "mcts_tacticas.csv")
if os.path.exists(_ruta_mcts):
    mcts_filas = exp4_load(_ruta_mcts)
    _res = exp4_summary(mcts_filas)
    _lineas = ["| Configuración | Simulaciones | Tasa de acierto | Desv. entre semillas | Mín.–máx. por semilla | Tiempo medio (s) | Desv. tiempo (s) |",
               "|---|---:|---:|---:|---|---:|---:|"]
    for _s in _res["by_budget"]:
        _lineas.append(f"| {_s['config']} | {_s['budget']} | {_s['hit_rate']:.2f} | {_s['hit_rate_seed_std']:.3f} | "
                       f"{_s['hit_rate_seed_min']:.1f}–{_s['hit_rate_seed_max']:.1f} | {_s['time_mean_s']:.3f} | "
                       f"{_s['time_std_s']:.3f} |")
    display(Markdown("\n".join(_lineas)))
    _cols = [k for k in _res["by_tactic"][0] if k != "tactic"]
    _lineas = ["| Táctica (captures_L4) | " + " | ".join(c[1:] + " sims" for c in _cols) + " |",
               "|---" * (len(_cols) + 1) + "|"]
    for _t in _res["by_tactic"]:
        _lineas.append(f"| {_t['tactic']} | " + " | ".join(_t[c] for c in _cols) + " |")
    display(Markdown("\n".join(_lineas)))
    print(f"Casos (tactica, semilla) no monotonos al crecer el presupuesto: {len(_res['non_monotonic'])}")

    # Muestra en vivo: 4 filas del CSV repetidas con el mismo codigo (jugada y simulaciones deben coincidir).
    _tac = {t["id"]: t for t in MCTS_TACTICS}
    _muestra = [r for r in mcts_filas if r["config"] == "captures_L4" and r["budget"] == 200
                and r["seed"] in (0, 1) and r["tactic"] in ("T3_mate1_b_backrank", "T7_avoid_b_scholar")]
    for _r in _muestra:
        _d = MCTSAgent(simulations=_r["budget"]).choose(chess.Board(_tac[_r["tactic"]]["fen"]),
                                                       time_limit_s=0, seed=_r["seed"])
        assert _d.move.uci() == _r["move"] and _d.stats.simulations == _r["simulations"]
    print(f"Repetidas en vivo {len(_muestra)} filas del CSV: misma jugada y mismas simulaciones.")
    fig_mcts_budget(mcts_filas)
    plt.show()
else:
    print("AVISO: falta resultados/mcts_tacticas.csv (benchmark del Experimento 4).")
