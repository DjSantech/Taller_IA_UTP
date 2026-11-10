# ===== Experimento 2: torneo todos contra todos (resultados guardados) + partida corta en vivo =====
# EJECUTAR_COMPLETO = True repite el torneo COMPLETO aqui mismo, con este mismo codigo. Son cientos
# de partidas con 0.2 s por jugada: en serie tarda horas. Por eso lo corrimos con
#     python tools/correr_experimentos.py
# (mismo paquete chess_ai, en paralelo con procesos) y aqui se CARGAN sus archivos de resultados/.
# Con False, ademas, se juega en vivo una partida corta para mostrar que el codigo corre.
import json
import os

import matplotlib.pyplot as plt
from IPython.display import Markdown, display

EJECUTAR_COMPLETO = False

if EJECUTAR_COMPLETO:
    run_tournament(TournamentConfig(), out_dir="resultados")
else:
    _cfg_demo = TournamentConfig(agents=("Alfa-beta mejorado", "MCTS"), opening_ids=("A1_italiana",),
                                 max_plies=16, game_prefix="DEMO", seed_base=0)
    _spec = round_robin_schedule(_cfg_demo)[0]
    _demo = play_game(_spec, _cfg_demo)
    _g = _demo["game"]
    print(f"Partida de demostracion (en vivo): {_g['white_agent']} - {_g['black_agent']}, apertura "
          f"{_g['opening_id']}, {_cfg_demo.max_plies} plies de agentes como maximo, "
          f"{_cfg_demo.time_limit_s} s por jugada -> {_g['termination']} {_g['official_result']}")
    print(_demo["pgn"])
    print(f"{len(_demo['decisions'])} filas con las columnas CSV_FIELDS; ultimas tres:")
    for _row in _demo["decisions"][-3:]:
        print("  " + ", ".join(f"{k}={_row[k]}" for k in ("ply", "move_uci", "nodes", "cutoffs",
                                                         "completed_depth", "simulations",
                                                         "elapsed_s", "time_exceeded")))

_ruta_partidas = os.path.join("resultados", "torneo_partidas.csv")
if os.path.exists(_ruta_partidas):
    torneo = load_tournament("resultados", "torneo")
    torneo_analisis = tournament_analysis(torneo)
    _conf = torneo["config"]
    print(f"\nTorneo guardado: {torneo_analisis['n_games']} partidas, {len(torneo['decisions'])} decisiones; "
          f"truncadas: {torneo_analisis['truncated']}; terminaciones: {torneo_analisis['terminations']}")
    if _conf:
        print("Configuracion (resultados/torneo_config.json): " + json.dumps(
            {k: _conf[k] for k in list(_conf)[:12]}, ensure_ascii=False)[:900])
    display(Markdown("**Tabla del enunciado** (clasificación provisional: solo puntúan las partidas "
                     "terminadas; las truncadas van aparte y sin resultado)\n\n"
                     + standings_markdown(torneo_analisis["standings"])))
    _agentes = [r["agente"] for r in torneo_analisis["standings"]]
    display(Markdown("**Cruces** (puntos de la fila contra la columna / terminadas, t = truncadas)\n\n"
                     + pairwise_markdown(torneo_analisis["pairwise"], _agentes)))
    _lineas = ["| Agente | Jugadas | Tiempo medio (s) | Desv. (s) | Máximo (s) | Excesos | Nodos medios |",
               "|---|---:|---:|---:|---:|---:|---:|"]
    for _ag, _p in torneo_analisis["per_agent"].items():
        _lineas.append(f"| {_ag} | {_p['jugadas']} | {_p['tiempo_medio_s']:.4f} | {_p['tiempo_desv_s']:.4f} | "
                       f"{_p['tiempo_max_s']:.3f} | {_p['excesos']} ({100 * _p['prop_excesos']:.1f} %) | "
                       f"{_p['nodos_medios']:.0f} |")
    display(Markdown("**Tiempo y excesos por decisión** (los nodos de agentes distintos NO son "
                     "comparables: cada familia los define distinto)\n\n" + "\n".join(_lineas)))
    if "improved_depth" in torneo_analisis:
        print("Alfa-beta mejorado, profundidad completada por jugada:", torneo_analisis["improved_depth"])
    if "mcts_simulations" in torneo_analisis:
        print("MCTS, simulaciones por jugada con el plazo:", torneo_analisis["mcts_simulations"])
    fig_tournament(torneo_analisis["standings"])
    plt.show()
else:
    print("\nAVISO: aun no existe resultados/torneo_partidas.csv; ejecute tools/correr_experimentos.py "
          "y vuelva a construir el cuaderno.")

_ruta_dt = os.path.join("resultados", "exp_profundidad_tiempo.csv")
if os.path.exists(_ruta_dt):
    fig_depth_time(depth_time_load(_ruta_dt))       # curva de profundidad contra tiempo
    plt.show()
