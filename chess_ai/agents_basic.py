"""Agentes basicos (seccion 5 del enunciado): Aleatorio y Voraz de un ply.

Ambos cumplen el contrato `choose(board, *, time_limit_s, seed) -> Decision`:

* Reciben una COPIA del tablero con historia y la devuelven intacta (FEN y
  `move_stack`): el voraz hace push/pop dentro de `try/finally`.
* `Decision.move is None` solo si el estado ya es terminal segun
  `search_outcome` (mate, ahogado, material insuficiente, regla de 50 o
  repeticion triple). En ese caso `Decision.score` es la utilidad exacta del
  estado desde el jugador al turno (p. ej. -MATE_SCORE si le dieron mate).
* `Decision.score` se reporta SIEMPRE desde el jugador que decide en la raiz
  (BITACORA D-06): positivo = bueno para quien mueve.
* Todo lo aleatorio usa `random.Random(seed)` propio de la llamada: misma
  posicion + misma semilla -> misma jugada, sin depender del estado global.

Definiciones de metricas (SearchStats) en estos agentes:

| Campo           | Aleatorio                   | Voraz                                        |
|-----------------|-----------------------------|----------------------------------------------|
| nodes           | 0 (no genera sucesores)     | sucesores generados (push) = jugadas legales |
| leaves          | 0 (no evalua nada)          | sucesores evaluados (terminal exacto o E)    |
| cutoffs         | 0                           | 0 (no hay poda)                              |
| completed_depth | 0                           | 1 si evaluo todos los sucesores; 0 si el     |
|                 |                             | plazo corto la lista (devuelve el mejor visto)|
| elapsed_s       | tiempo de pared de choose   | tiempo de pared de choose                    |
| simulations     | 0                           | 0                                            |
"""
from __future__ import annotations

import random

import chess

from chess_ai.contract import Decision, SearchStats
from chess_ai.environment import (Deadline, perspective_sign, search_outcome,
                                  terminal_value_white)
from chess_ai.evaluation import DEFAULT_EVALUATOR

# Tolerancia para considerar empatados dos valores de E (sumas de flotantes).
_BASIC_TIE_EPS = 1e-9

# ---------------------------------------------------------------------------
# Posicion donde el voraz FALLA (pregunta 1 de la sustentacion).
#
#   Negras: Rg8 (rey), Re8 (torre), peones b7 f7 g7 h7.
#   Blancas: Rg1 (rey), Db6 (dama), peones f2 g2 h2. Juegan blancas.
#
# Negras amenazan ...Te1# (mate del pasillo: el rey blanco esta encerrado por
# sus propios peones f2 g2 h2 y nada cubre la primera fila). El voraz mira un
# solo ply: ve que Dxb7 gana un peon (+100 cp de material) y no ve la respuesta
# ...Te1#. Un minimax de profundidad 2 si genera la respuesta de negras, ve que
# tras Dxb7 llega un mate (utilidad -MATE_SCORE + 2) y escoge una DEFENSA:
# cubrir e1 con la dama (Db4, la que eligio un minimax-2 de prueba con E0) o
# abrir una casilla de escape al rey (h3, g3, f3, ...).
# El caso lo verifica `tests/test_agents_basic.py::test_greedy_falls_into_back_rank_trap`;
# la parte de minimax la verifica la prueba del modulo de busqueda.
GREEDY_TRAP_FEN = "4r1k1/1p3ppp/1Q6/8/8/8/5PPP/6K1 w - - 0 1"
GREEDY_TRAP_GREEDY_MOVE = "b6b7"     # lo que juega el voraz: Dxb7??
GREEDY_TRAP_REFUTATION = "e8e1"      # respuesta de negras: Te1#


def _basic_sorted_moves(board: chess.Board) -> list:
    """Jugadas legales ordenadas por UCI.

    python-chess ya genera las jugadas en un orden determinista, pero ese orden
    es un detalle interno de la biblioteca. Ordenar por la cadena UCI fija el
    orden ANTES de muestrear o desempatar: la jugada que sale con una semilla
    depende solo de la posicion y de la semilla, no de la version del generador.
    """
    return sorted(board.legal_moves, key=lambda m: m.uci())


def _basic_terminal_decision(board: chess.Board, outcome, deadline: Deadline) -> Decision:
    """Decision para un estado ya terminal: sin jugada y con su utilidad exacta."""
    value = perspective_sign(board.turn) * terminal_value_white(outcome, 0)
    return Decision(move=None, score=value,
                    stats=SearchStats(elapsed_s=deadline.elapsed()))


class RandomAgent:
    """Agente Aleatorio: elige uniformemente entre las jugadas legales.

    Es la linea base del torneo. No evalua posiciones, por eso `score` es None
    en estados no terminales. Reproducible: `random.Random(seed)` sobre la lista
    de jugadas ordenada por UCI.
    """

    def __init__(self, name: str = "Aleatorio"):
        self.name = name

    def choose(self, board: chess.Board, *, time_limit_s: float = 0.0, seed: int = 0) -> Decision:
        deadline = Deadline(time_limit_s)
        outcome = search_outcome(board)
        if outcome is not None:
            return _basic_terminal_decision(board, outcome, deadline)
        rng = random.Random(seed)
        move = rng.choice(_basic_sorted_moves(board))
        return Decision(move=move, score=None,
                        stats=SearchStats(elapsed_s=deadline.elapsed()))

    def __repr__(self) -> str:
        return f"RandomAgent({self.name!r})"


class GreedyAgent:
    """Agente Voraz de un ply: evalua cada sucesor inmediato y toma el mejor.

    Para cada jugada legal (en orden UCI):
      1. push de la jugada;
      2. si el sucesor es terminal (`search_outcome`), su valor es la utilidad
         exacta a distancia 1: un mate inmediato vale MATE_SCORE - 1 y domina a
         cualquier E; tablas valen 0;
      3. si no, su valor es E(sucesor) desde blancas;
      4. pop (en `finally`, aunque algo falle).
    El valor desde blancas se convierte con `perspective_sign` del que decide,
    y se maximiza. Asi negras prefieren valores de E bajos (buenos para negras).

    Desempate: entre las jugadas cuyo valor esta a menos de 1e-9 del maximo se
    elige una con `random.Random(seed)` (lista en orden UCI). Es reproducible y
    evita el sesgo sistematico de "la primera jugada del generador" en
    posiciones tranquilas donde muchas jugadas valen lo mismo.

    Plazo: es cooperativo (D-10). Se revisa despues de cada sucesor; si vence,
    se devuelve la mejor jugada vista (siempre hay al menos una evaluada) con
    `completed_depth = 0`. Con plazo <= 0 no hay limite.

    `evaluator` es cualquier invocable `board -> centipeones desde blancas`
    (un `Evaluator` o una funcion), lo que permite usar el voraz con pesos
    ajustados o con solo material en el modulo de ajuste.
    """

    def __init__(self, evaluator=DEFAULT_EVALUATOR, name: str = "Voraz"):
        self.evaluator = evaluator
        self.name = name

    def choose(self, board: chess.Board, *, time_limit_s: float = 0.0, seed: int = 0) -> Decision:
        deadline = Deadline(time_limit_s)
        outcome = search_outcome(board)
        if outcome is not None:
            return _basic_terminal_decision(board, outcome, deadline)

        sign = perspective_sign(board.turn)
        stats = SearchStats()
        scored = []                       # (valor desde quien decide, jugada)
        moves = _basic_sorted_moves(board)
        for move in moves:
            board.push(move)
            try:
                stats.nodes += 1
                child = search_outcome(board)
                if child is not None:
                    value_white = terminal_value_white(child, 1)
                else:
                    value_white = self.evaluator(board)
                stats.leaves += 1
            finally:
                board.pop()
            scored.append((sign * value_white, move))
            if deadline.expired():
                break

        best = max(v for v, _ in scored)
        ties = [m for v, m in scored if v >= best - _BASIC_TIE_EPS]
        move = ties[0] if len(ties) == 1 else random.Random(seed).choice(ties)
        stats.completed_depth = 1 if len(scored) == len(moves) else 0
        stats.elapsed_s = deadline.elapsed()
        return Decision(move=move, score=best, stats=stats)

    def __repr__(self) -> str:
        return f"GreedyAgent({self.name!r}, {self.evaluator!r})"
