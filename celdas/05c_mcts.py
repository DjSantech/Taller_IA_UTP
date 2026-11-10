# ===== Demostracion D: MCTS-UCT con simulaciones fijas (reproducible) =====
_tacticas = {t["id"]: t for t in MCTS_TACTICS}
for _id in ("T3_mate1_b_backrank", "T6_queen_b"):
    _t = _tacticas[_id]
    _b = chess.Board(_t["fen"])
    _antes = (_b.fen(), list(_b.move_stack))
    _ag = MCTSAgent(simulations=300)
    _d = _ag.choose(_b, time_limit_s=0, seed=0)
    _ag_otro = MCTSAgent(simulations=300)
    _d_otra = _ag_otro.choose(_b, time_limit_s=0, seed=0)
    assert (_b.fen(), list(_b.move_stack)) == _antes
    # misma semilla y mismas simulaciones -> misma jugada y mismas visitas en la raiz
    assert _d.move == _d_otra.move and _ag.last_info["root_visits"] == _ag_otro.last_info["root_visits"]
    _info = _ag.last_info
    _top = list(_info["root_visits"].items())[:4]
    print(f"{_id} ({'negras' if _b.turn == chess.BLACK else 'blancas'} al turno): juega {_b.san(_d.move)} "
          f"{'(correcta)' if _d.move.uci() in _t['solutions'] else '(INCORRECTA)'}; "
          f"q = {_info['win_probability']:.3f} desde quien decide; score = {_d.score:+.0f} cp")
    print(f"   simulaciones={_d.stats.simulations}, nodos={_d.stats.nodes}, rollouts truncados="
          f"{_info['truncated_rollouts']}, terminales={_info['terminal_rollouts']}, "
          f"profundidad max={_d.stats.completed_depth}")
    print("   visitas de la raiz (top 4): " + ", ".join(
        f"{_b.san(chess.Move.from_uci(u))}={v} (valor {_info['root_values'][u]:.2f})" for u, v in _top))
