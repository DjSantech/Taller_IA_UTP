# ===== Demostracion A: reproducibilidad por semilla y perspectiva de color =====
from collections import Counter as _Counter

_inicial = chess.Board()
_aleatorio, _voraz = RandomAgent(), GreedyAgent()

# 1) Aleatorio: misma semilla -> misma jugada; muchas semillas -> cubre las 20 jugadas.
_j1 = _aleatorio.choose(_inicial.copy(stack=True), time_limit_s=0, seed=42).move
_j2 = _aleatorio.choose(_inicial.copy(stack=True), time_limit_s=0, seed=42).move
assert _j1 == _j2
_cuenta = _Counter(_aleatorio.choose(_inicial, time_limit_s=0, seed=s).move.uci() for s in range(2000))
print(f"Aleatorio, semilla 42 dos veces: {_j1.uci()} y {_j2.uci()} (iguales).")
print(f"Aleatorio con 2000 semillas: {len(_cuenta)} jugadas distintas de 20; "
      f"frecuencia min/max = {min(_cuenta.values())}/{max(_cuenta.values())}.")

# 2) Voraz: un mate en uno domina a cualquier estimacion; tablero intacto.
_b = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
_antes = (_b.fen(), list(_b.move_stack))
_d = _voraz.choose(_b, time_limit_s=0, seed=0)
assert (_b.fen(), list(_b.move_stack)) == _antes
print(f"\nVoraz en mate en uno: {_b.san(_d.move)} con score {_d.score:.0f} "
      f"(nodos={_d.stats.nodes}, hojas={_d.stats.leaves}).")

# 3) Perspectiva: con negras al turno el voraz minimiza E (bueno para negras).
_b = chess.Board("4k3/p7/8/3Q4/8/2n5/7P/4K3 b - - 0 1")
_d = _voraz.choose(_b, time_limit_s=0, seed=0)
assert _d.move == chess.Move.from_uci("c3d5") and _d.score > 0
_b.push(_d.move)
print(f"Voraz con NEGRAS: {_b.peek().uci()} (Cxd5), score {_d.score:+.1f} cp desde negras; "
      f"E desde blancas tras la jugada = {DEFAULT_EVALUATOR(_b):+.1f} (negativa: buena para negras).")

# 4) Estado terminal: sin decision nueva y utilidad de derrota para negras.
_d = _voraz.choose(chess.Board("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"), time_limit_s=0, seed=0)
print(f"Voraz en la posicion de mate (juegan negras): move={_d.move}, score={_d.score:.0f}")

# 5) Donde falla el voraz (pregunta 1): GREEDY_TRAP_FEN.
_b = chess.Board(GREEDY_TRAP_FEN)
_d = _voraz.choose(_b, time_limit_s=0, seed=0)
_b2 = _b.copy(); _b2.push(_d.move); _b2.push_uci(GREEDY_TRAP_REFUTATION)
print(f"\nGREEDY_TRAP_FEN: el voraz juega {_b.san(_d.move)} ({_d.score:+.1f} cp) y tras "
      f"...Te1 la posicion es jaque mate: {_b2.is_checkmate()}")
