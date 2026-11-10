"""Entorno de ajedrez: estado real, politica de terminacion, utilidades y plazos.

Convenciones del taller (ver BITACORA D-06 .. D-10):

* PERSPECTIVA. Toda evaluacion E(s) y toda utilidad "absoluta" se expresan desde
  BLANCAS (positivo = bueno para blancas), en centipeones. Cada agente convierte a
  la perspectiva del jugador que decide con `perspective_sign(color)`.
  `Decision.score` se reporta SIEMPRE desde el jugador que decide en la raiz.
* TERMINALES. Se resuelven ANTES de consultar E. Victoria a distancia `ply` vale
  MATE_SCORE - ply (se prefieren mates mas cortos); tablas valen 0. Como
  |E| <= EVAL_BOUND < MATE_SCORE - MAX_MATE_PLY, cualquier mate domina a
  cualquier estimacion no terminal.
* POLITICA DE TABLAS. En la partida real se usa `board.outcome(claim_draw=True)`
  (reclamo automatico, convencion experimental del enunciado). Dentro de la
  busqueda se usa `search_outcome`, equivalente en el arbol pero mas barata
  (ver D-08): no evalua los reclamos "antes de mover", porque ese caso aparece
  como repeticion triple o regla de 50 en el hijo correspondiente.
* TRUNCADA. El limite de plies del torneo NO es un resultado reglamentario: el
  entorno lo reporta como estado "truncated", separado de las tablas.
"""
from __future__ import annotations

import time

import chess
import chess.pgn

MATE_SCORE = 100_000.0
MAX_MATE_PLY = 1_000
EVAL_BOUND = 10_000.0
DRAW_SCORE = 0.0


class SearchTimeout(Exception):
    """Se lanza dentro de una busqueda cuando vence el plazo cooperativo."""


class IllegalMoveError(ValueError):
    """Intento de aplicar al estado real una jugada que no es legal."""


class Deadline:
    """Plazo cooperativo. La busqueda pregunta; nadie la interrumpe desde fuera.

    `time_limit_s` <= 0 o None significa "sin plazo" (profundidad fija pura).
    """

    __slots__ = ("start", "limit", "end")

    def __init__(self, time_limit_s: float | None):
        self.start = time.perf_counter()
        self.limit = time_limit_s if time_limit_s and time_limit_s > 0 else None
        self.end = self.start + self.limit if self.limit is not None else float("inf")

    def expired(self) -> bool:
        return time.perf_counter() >= self.end

    def check(self) -> None:
        if time.perf_counter() >= self.end:
            raise SearchTimeout()

    def elapsed(self) -> float:
        return time.perf_counter() - self.start


def perspective_sign(color: chess.Color) -> int:
    """+1 si `color` es blancas, -1 si es negras (convierte valores desde blancas)."""
    return 1 if color == chess.WHITE else -1


def game_outcome(board: chess.Board) -> chess.Outcome | None:
    """Resultado de la PARTIDA REAL segun la politica del taller (reclamo automatico)."""
    return board.outcome(claim_draw=True)


def search_outcome(board: chess.Board) -> chess.Outcome | None:
    """Prueba terminal usada DENTRO de las busquedas (mas barata que claim_draw=True).

    Orden: mate/ahogado (sin jugadas legales), material insuficiente, regla de 50
    (halfmove_clock >= 100) y repeticion triple de la posicion actual.
    """
    if not any(board.generate_legal_moves()):
        if board.is_check():
            return chess.Outcome(chess.Termination.CHECKMATE, not board.turn)
        return chess.Outcome(chess.Termination.STALEMATE, None)
    if board.is_insufficient_material():
        return chess.Outcome(chess.Termination.INSUFFICIENT_MATERIAL, None)
    if board.halfmove_clock >= 100:
        return chess.Outcome(chess.Termination.FIFTY_MOVES, None)
    if board.is_repetition(3):
        return chess.Outcome(chess.Termination.THREEFOLD_REPETITION, None)
    return None


def terminal_value_white(outcome: chess.Outcome, ply: int = 0) -> float:
    """Utilidad exacta desde blancas de un estado terminal alcanzado a `ply` de la raiz."""
    if outcome.winner is None:
        return DRAW_SCORE
    value = MATE_SCORE - min(ply, MAX_MATE_PLY)
    return value if outcome.winner == chess.WHITE else -value


def is_mate_score(value: float) -> bool:
    return abs(value) >= MATE_SCORE - MAX_MATE_PLY


class ChessEnvironment:
    """Estado REAL de la partida. Unico lugar donde se aplican jugadas.

    Invariantes: toda jugada aplicada es legal; el turno cambia una sola vez por
    jugada; una partida terminal o truncada no acepta mas jugadas; `version`
    aumenta en cada cambio para que el controlador descarte decisiones obsoletas.
    """

    def __init__(self, fen: str | None = None, max_plies: int | None = None):
        self.start_fen = fen or chess.STARTING_FEN
        self.board = chess.Board(self.start_fen)
        self.max_plies = max_plies
        self.version = 0

    # --- consultas -------------------------------------------------------
    @property
    def ply_count(self) -> int:
        return len(self.board.move_stack)

    def outcome(self) -> chess.Outcome | None:
        return game_outcome(self.board)

    def is_truncated(self) -> bool:
        return (self.max_plies is not None and self.ply_count >= self.max_plies
                and self.outcome() is None)

    def status(self) -> str:
        """'ongoing' | 'terminal' | 'truncated'."""
        if self.outcome() is not None:
            return "terminal"
        if self.is_truncated():
            return "truncated"
        return "ongoing"

    def is_over(self) -> bool:
        return self.status() != "ongoing"

    def official_result(self) -> str:
        """'1-0', '0-1', '1/2-1/2' o '*' (en curso o truncada: sin resultado oficial)."""
        out = self.outcome()
        return out.result() if out is not None else "*"

    def termination(self) -> str:
        out = self.outcome()
        if out is not None:
            return out.termination.name.lower()
        return "truncated" if self.is_truncated() else "ongoing"

    def copy_for_agent(self) -> chess.Board:
        """Copia con la pila completa: repeticiones y reclamos siguen siendo detectables."""
        return self.board.copy(stack=True)

    def san_history(self) -> list[str]:
        replay = chess.Board(self.start_fen)
        out = []
        for mv in self.board.move_stack:
            out.append(replay.san(mv))
            replay.push(mv)
        return out

    # --- cambios -----------------------------------------------------------
    def apply(self, move: chess.Move) -> None:
        if self.is_over():
            raise IllegalMoveError("la partida ya termino (" + self.termination() + ")")
        if move is None or move not in self.board.legal_moves:
            raise IllegalMoveError(f"jugada ilegal en {self.board.fen()}: {move}")
        self.board.push(move)
        self.version += 1

    def undo(self, plies: int = 1) -> int:
        """Deshace hasta `plies` jugadas; devuelve cuantas deshizo."""
        done = 0
        while done < plies and self.board.move_stack:
            self.board.pop()
            done += 1
        if done:
            self.version += 1
        return done

    def reset(self, fen: str | None = None) -> None:
        if fen is not None:
            self.start_fen = fen
        self.board = chess.Board(self.start_fen)
        self.version += 1

    def to_pgn(self, headers: dict | None = None) -> chess.pgn.Game:
        game = chess.pgn.Game.from_board(self.board)
        if self.start_fen != chess.STARTING_FEN:
            game.headers["FEN"] = self.start_fen
            game.headers["SetUp"] = "1"
        game.headers["Result"] = self.official_result()
        game.headers["Termination"] = self.termination()
        for k, v in (headers or {}).items():
            game.headers[k] = str(v)
        return game
