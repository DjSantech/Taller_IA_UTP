# ===== Demostracion C: profundizacion iterativa con plazo (AlphaBetaImprovedAgent) =====
def _tabla_iteraciones(agente):
    print(f"   {'prof':>4} {'termino':>8} {'nodos':>7} {'hojas':>7} {'podas':>6} {'tiempo s':>9} "
          f"{'valor (blancas)':>16}  jugada")
    for _it in agente.last_iterations:
        _v = "-" if _it["value_white"] is None else f"{_it['value_white']:+.1f}"
        print(f"   {_it['depth']:>4} {('si' if _it['completed'] else 'NO'):>8} {_it['nodes']:>7} "
              f"{_it['leaves']:>7} {_it['cutoffs']:>6} {_it['elapsed_s']:>9.4f} {_v:>16}  "
              f"{_it['move'] or '(descartada)'}")


_mej = AlphaBetaImprovedAgent(max_depth=10)
for _titulo, _fen, _plazo in (("inicial, plazo 0.2 s", chess.STARTING_FEN, 0.2),
                              ("medio juego (italiana), plazo 0.2 s",
                               "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", 0.2),
                              ("inicial, plazo agotado de entrada (1e-9 s)", chess.STARTING_FEN, 1e-9)):
    _b = chess.Board(_fen)
    _antes = (_b.fen(), list(_b.move_stack))
    _d = _mej.choose(_b, time_limit_s=_plazo, seed=0)
    assert (_b.fen(), list(_b.move_stack)) == _antes         # tablero intacto aunque se interrumpa
    assert _d.move in _b.legal_moves                         # nunca None en un estado no terminal
    _hechas = [it for it in _mej.last_iterations if it["completed"]]
    assert _d.stats.completed_depth == len(_hechas)
    print(f"\n{_titulo}: devuelve {_b.san(_d.move)}, score={_d.score if _d.score is None else round(_d.score, 1)}, "
          f"completed_depth={_d.stats.completed_depth}, nodos totales={_d.stats.nodes}, "
          f"tiempo={_d.stats.elapsed_s:.3f} s")
    if _mej.last_iterations:
        _tabla_iteraciones(_mej)
    else:
        print("   ninguna iteracion empezo: se devuelve la jugada de RESPALDO (primera segun la ordenacion)")

# Sin plazo y con max_depth fija, el valor coincide con alfa-beta (= minimax) a esa profundidad.
_b = chess.Board("8/5k2/8/3R4/8/2K5/5r2/8 w - - 0 1")
_d = AlphaBetaImprovedAgent(max_depth=3).choose(_b, time_limit_s=0, seed=0)
assert _d.score == search_root(_b, "alphabeta", 3).value
print(f"\nFinal de torres sin plazo, max_depth=3: {_b.san(_d.move)} {_d.score:+.1f} = valor de alfa-beta d=3.")
