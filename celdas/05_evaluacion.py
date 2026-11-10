# ===== E(s) en algunas posiciones: caracteristicas, signo y dominio de los terminales =====
# (POSITIONS del enunciado se define mas adelante, en la seccion 8; aqui van FEN explicitos.)
_fens_e = {
    "inicial": chess.STARTING_FEN,
    "italiana": "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    "pasado_b": "8/8/1k6/8/8/6K1/1p6/8 w - - 0 1",
    "rey_abierto": "rnbq1rk1/ppp2p1p/3p1np1/8/3PP3/2N2N2/PPP2PPP/R1BQKB1R w KQ - 0 7",
}
print(f"{'posicion':<13}{'M':>7}{'P':>8}{'K':>8}{'A':>7}{'E0 (cp)':>10}{'E0 reflejada':>14}")
for _nombre, _fen in _fens_e.items():
    _b = chess.Board(_fen)
    _f = features(_b)
    _e, _e_ref = DEFAULT_EVALUATOR(_b), DEFAULT_EVALUATOR(_b.mirror())
    assert abs(_e + _e_ref) < 1e-9          # antisimetria: reflejar e intercambiar colores invierte el signo
    print(f"{_nombre:<13}{_f[0]:>7.1f}{_f[1]:>8.2f}{_f[2]:>8.2f}{_f[3]:>7.0f}{_e:>10.1f}{_e_ref:>14.1f}")

# Un mate siempre domina: la mayor estimacion posible frente al mate mas lejano representable.
_mate = terminal_value_white(chess.Board("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1").outcome(), ply=MAX_MATE_PLY)
assert _mate > EVAL_BOUND
print(f"\nCota de E: +-{EVAL_BOUND:.0f} cp. Mate de blancas a {MAX_MATE_PLY} plies: {_mate:.0f} cp "
      f"(domina a cualquier E). Tablas: {DRAW_SCORE:.0f}.")
