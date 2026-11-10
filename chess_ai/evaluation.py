"""Evaluacion comun E(s) = wm*M(s) + wp*P(s) + wk*K(s) + wa*A(s), desde BLANCAS.

Cada caracteristica es (valor de blancas) - (valor de negras), asi que el signo
es siempre "positivo = mejor para blancas" y la evaluacion es antisimetrica:
reflejar el tablero e intercambiar colores invierte el signo (prueba en tests).

| Car. | Definicion                                            | Escala tipica | Que decision pretende inducir                         | Costo |
|------|-------------------------------------------------------|---------------|-------------------------------------------------------|-------|
| M    | material en peones: P=1, N=3.2, B=3.3, R=5, Q=9       | -39 .. +39    | no regalar piezas; cambiar cuando se va ganando       | O(1) bitboards |
| P    | estructura de peones: pasados (con bono por avance)   | aprox -6 .. 6 | crear y empujar pasados; evitar doblados y aislados   | O(peones) |
|      | menos doblados menos aislados                         |               |                                                       |       |
| K    | seguridad del rey: escudo de peones menos casillas    | aprox -9 .. 3 | enrocar y no abrir el rey en el medio juego           | O(9) ataques |
|      | de la zona del rey atacadas por el rival, x fase      |               | (en finales la fase -> 0 y el termino se apaga)       |       |
| A    | actividad: casillas atacadas por N, B, R, Q que no    | aprox -40..40 | desarrollar piezas y abrir lineas                     | O(piezas) |
|      | estan ocupadas por piezas propias                     |               |                                                       |       |

Pesos por defecto (centipeones por unidad): wm=100, wp=15, wk=10, wa=4.
Los valores terminales NO pasan por aqui (ver environment.terminal_value_white);
el resultado se recorta a +-EVAL_BOUND para que un mate siempre domine.
"""
from __future__ import annotations

import chess

from chess_ai.environment import EVAL_BOUND

PIECE_VALUES = {chess.PAWN: 1.0, chess.KNIGHT: 3.2, chess.BISHOP: 3.3,
                chess.ROOK: 5.0, chess.QUEEN: 9.0, chess.KING: 0.0}
DEFAULT_WEIGHTS = (100.0, 15.0, 10.0, 4.0)
FEATURE_NAMES = ("M_material", "P_peones", "K_rey", "A_actividad")
# Material no-peon inicial de ambos bandos: 2*(2*3.2 + 2*3.3 + 2*5 + 9)
_FULL_PHASE = 2 * (2 * 3.2 + 2 * 3.3 + 2 * 5.0 + 9.0)


def _passed_mask(color: chess.Color, sq: int) -> int:
    """Casillas delante del peon en su columna y las vecinas: si no hay peon rival ahi, es pasado."""
    f, r = chess.square_file(sq), chess.square_rank(sq)
    ahead = 0
    ranks = range(r + 1, 8) if color == chess.WHITE else range(0, r)
    for rr in ranks:
        for ff in (f - 1, f, f + 1):
            if 0 <= ff < 8:
                ahead |= chess.BB_SQUARES[chess.square(ff, rr)]
    return ahead


# Precalculadas una vez (2 x 64 enteros): la version que las construia en cada
# llamada gastaba ~la mitad del costo de E (bitacora S-13 y E-12).
_PASSED_MASK = {c: [_passed_mask(c, sq) for sq in chess.SQUARES] for c in (chess.WHITE, chess.BLACK)}


def _material(board: chess.Board, color: chess.Color) -> float:
    return sum(PIECE_VALUES[pt] * chess.popcount(board.pieces_mask(pt, color))
               for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


def _pawn_structure(board: chess.Board, color: chess.Color) -> float:
    own = board.pieces_mask(chess.PAWN, color)
    enemy = board.pieces_mask(chess.PAWN, not color)
    score = 0.0
    for f in range(8):
        n = chess.popcount(own & chess.BB_FILES[f])
        if n == 0:
            continue
        if n > 1:
            score -= n - 1                       # doblados
        neighbours = 0
        if f > 0:
            neighbours |= chess.BB_FILES[f - 1]
        if f < 7:
            neighbours |= chess.BB_FILES[f + 1]
        if not own & neighbours:
            score -= n                           # aislados
    masks = _PASSED_MASK[color]
    for sq in chess.scan_forward(own):
        if not enemy & masks[sq]:                # pasado: bono creciente con el avance
            r = chess.square_rank(sq)
            advance = r if color == chess.WHITE else 7 - r
            score += 1.0 + advance / 6.0
    return score


def _phase(board: chess.Board) -> float:
    non_pawn = sum(PIECE_VALUES[pt] * chess.popcount(board.pieces_mask(pt, c))
                   for c in (chess.WHITE, chess.BLACK)
                   for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))
    return min(1.0, non_pawn / _FULL_PHASE)


def _king_safety(board: chess.Board, color: chess.Color) -> float:
    king = board.king(color)
    if king is None:
        return 0.0
    f, r = chess.square_file(king), chess.square_rank(king)
    step = 1 if color == chess.WHITE else -1
    shield = 0
    own_pawns = board.pieces_mask(chess.PAWN, color)
    for dr in (step, 2 * step):
        rr = r + dr
        if 0 <= rr < 8:
            for ff in (f - 1, f, f + 1):
                if 0 <= ff < 8 and own_pawns & chess.BB_SQUARES[chess.square(ff, rr)]:
                    shield += 1
    shield = min(shield, 3)
    zone = chess.BB_KING_ATTACKS[king] | chess.BB_SQUARES[king]
    attacked = sum(1 for sq in chess.scan_forward(zone) if board.is_attacked_by(not color, sq))
    return float(shield - attacked)


def _activity(board: chess.Board, color: chess.Color) -> float:
    own_occ = board.occupied_co[color]
    total = 0
    for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        for sq in chess.scan_forward(board.pieces_mask(pt, color)):
            total += chess.popcount(board.attacks_mask(sq) & ~own_occ)
    return float(total)


def features(board: chess.Board) -> tuple[float, float, float, float]:
    """Vector (M, P, K, A) desde blancas. Base del ajuste de pesos (busqueda local)."""
    w, b = chess.WHITE, chess.BLACK
    phase = _phase(board)
    return (
        _material(board, w) - _material(board, b),
        _pawn_structure(board, w) - _pawn_structure(board, b),
        phase * (_king_safety(board, w) - _king_safety(board, b)),
        _activity(board, w) - _activity(board, b),
    )


def evaluate(board: chess.Board, weights=DEFAULT_WEIGHTS) -> float:
    """E(s) en centipeones desde blancas, recortada a +-EVAL_BOUND. No mira terminales."""
    value = sum(wi * fi for wi, fi in zip(weights, features(board)))
    return max(-EVAL_BOUND, min(EVAL_BOUND, value))


class Evaluator:
    """Evaluador con pesos fijos. Es invocable: `ev(board)` -> centipeones desde blancas."""

    def __init__(self, weights=DEFAULT_WEIGHTS, name: str = "E0"):
        if len(weights) != 4:
            raise ValueError("se esperan 4 pesos (wm, wp, wk, wa)")
        self.weights = tuple(float(x) for x in weights)
        self.name = name

    def __call__(self, board: chess.Board) -> float:
        return evaluate(board, self.weights)

    def features(self, board: chess.Board):
        return features(board)

    def __repr__(self) -> str:
        return f"Evaluator({self.name}, weights={self.weights})"


DEFAULT_EVALUATOR = Evaluator(DEFAULT_WEIGHTS, "E0")
