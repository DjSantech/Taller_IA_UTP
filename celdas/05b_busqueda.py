# ===== Demostracion B: minimax = alfa-beta en valor (profundidades 1 y 2), con menos nodos =====
_fens_b = {
    "inicial": chess.STARTING_FEN,
    "italiana": "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "defensa_q1": MINIMAX_DEFENSE_FEN,
    "negras_jaque": "r3k3/ppp2ppp/8/1B6/8/8/PPP2PPP/4K2R b K - 0 1",
    "final_torres": "8/5k2/8/3R4/8/2K5/5r2/8 w - - 0 1",
}
print(f"{'posicion':<14}{'d':>2}  {'minimax':>10} {'nodos':>6} | {'alfa-beta':>10} {'nodos':>6} "
      f"{'podas':>6} | {'AB ordenado':>11} {'nodos':>6}  jugadas (MM / AB / ABo)")
for _nombre, _fen in _fens_b.items():
    for _prof in (1, 2):
        _b = chess.Board(_fen)
        _mm = search_root(_b, "minimax", _prof)
        _ab = search_root(_b, "alphabeta", _prof)
        _abo = search_root(_b, "alphabeta", _prof, ordering=True)
        assert _mm.value == _ab.value == _abo.value          # igualdad EXACTA del valor de la raiz
        assert _ab.stats.nodes <= _mm.stats.nodes
        print(f"{_nombre:<14}{_prof:>2}  {_mm.value:>10.1f} {_mm.stats.nodes:>6} | {_ab.value:>10.1f} "
              f"{_ab.stats.nodes:>6} {_ab.stats.cutoffs:>6} | {_abo.value:>11.1f} {_abo.stats.nodes:>6}  "
              f"{_b.san(_mm.move)} / {_b.san(_ab.move)} / {_b.san(_abo.move)}")
print("Mismo valor en las 10 comparaciones (assert ==). Si las jugadas difieren, es un empate de valor.")

# Pregunta 1: el voraz (= minimax de profundidad 1) gana un peon; minimax-2 ve la respuesta exd4.
_b = chess.Board(MINIMAX_DEFENSE_FEN)
_d1 = MinimaxAgent(depth=1).choose(_b, time_limit_s=0, seed=0)
_d2 = MinimaxAgent(depth=2).choose(_b, time_limit_s=0, seed=0)
print(f"\nMINIMAX_DEFENSE_FEN: profundidad 1 -> {_b.san(_d1.move)} ({_d1.score:+.1f}); "
      f"profundidad 2 -> {_b.san(_d2.move)} ({_d2.score:+.1f}).")

# Pregunta 2: registro de podas reales (trazado a mano en el texto de arriba).
_ab_log = AlphaBetaAgent(depth=2, log_prunes=True)
_d = _ab_log.choose(chess.Board(MINIMAX_DEFENSE_FEN), time_limit_s=0, seed=0)
print(f"\nAlfa-beta natural d=2: {chess.Board(MINIMAX_DEFENSE_FEN).san(_d.move)} ({_d.score:+.3f}), "
      f"{_d.stats.nodes} nodos, {_d.stats.cutoffs} podas, {_ab_log.last_pruned_children} hijos omitidos. "
      "Primeras dos podas del registro:")
for _ev in _ab_log.last_prune_log[:2]:
    print(format_prune_event(_ev))
