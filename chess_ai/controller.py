"""Controlador de partida (seccion 6 del enunciado): alternancia, presupuesto,
cancelacion cooperativa, terminacion, registro de metricas y exportacion.

No crea widgets: la vista (`chess_ai.gui.ChessApp`) solo llama a estos metodos y
se suscribe a `on_update`. Asi la logica se prueba con pytest sin Jupyter.

AL_SOLICITAR_TURNO (pseudocodigo del enunciado) -> `GameController.request_turn`:

    si hay busqueda activa o partida terminada: informar y salir    -> "busy" / "over"
    identificar agente segun el color al turno
    si es humano: esperar una jugada por la interfaz                -> "human"
    si es agente:
        capturar `env.version`                                       (version vigente)
        copiar el tablero conservando la historia                    (copy_for_agent)
        solicitar Decision al agente                                 (seed = seed_base + ply)
        comprobar plazo, legalidad y que la version siga vigente     -> "error" / "stale"
        aplicar exactamente una jugada al tablero real               (env.apply)
        registrar metricas y actualizar vista                        (MoveRecord + on_update)

Politicas (ver apuntes/bitacora_G.md):

* SEMILLA POR JUGADA: `seed = config.seed + ply_count` (ply_count antes de mover).
  La misma semilla base reproduce la partida; cada jugada recibe una semilla
  distinta y conocida.
* PLAZO: cooperativo. El controlador mide el tiempo real de `choose` y marca
  `time_exceeded` si supera `time_limit_s + tolerance_s`. La jugada SE APLICA de
  todos modos (politica uniforme para todos los agentes); el exceso queda en el
  registro. Medir despues de devolver no interrumpe un agente bloqueado: el
  aislamiento en otro proceso queda fuera del alcance minimo (seccion 6).
* JUGADA INVALIDA: si un agente devuelve `None` en un estado no terminal, una
  jugada ilegal o lanza una excepcion, el turno se registra como ERROR, el estado
  real NO cambia, el bucle automatico se detiene y no se inventa ningun resultado.
* DECISION OBSOLETA: si `env.version` cambio mientras el agente pensaba, la
  decision se descarta sin aplicarla (estado "stale").
* DESHACER: humano contra agente -> deshace hasta devolver el turno al humano (una
  pareja de turnos si el agente ya respondio); otros modos -> un ply. Prohibido con
  busqueda activa o con el bucle automatico en marcha (hay que pausar primero).
"""
from __future__ import annotations

import asyncio
import csv
import io
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

import chess
import chess.pgn

from chess_ai.contract import Decision, SearchStats
from chess_ai.environment import ChessEnvironment, IllegalMoveError

# Columnas del CSV de decisiones, exactamente las del enunciado (seccion 9).
CSV_FIELDS = ["game_id", "opening_id", "seed", "white_agent", "black_agent", "ply",
              "move_uci", "nodes", "leaves", "cutoffs", "completed_depth",
              "elapsed_s", "simulations", "time_exceeded", "termination", "official_result"]

HUMAN_LABEL = "Humano"          # etiqueta reservada: en el diccionario de fabricas vale None
DEFAULT_TIME_TOLERANCE_S = 0.05  # margen sobre el presupuesto antes de marcar exceso


@dataclass
class AgentConfig:
    """Configuracion que la interfaz entrega a cada fabrica de agentes.

    `depth`: profundidad para agentes de profundidad fija (minimax, alfa-beta).
    `time_limit_s`: presupuesto por decision (<= 0: sin plazo).
    `seed`: semilla BASE; cada jugada recibe `seed + ply` (ver `seed_for_ply`).
    `simulations`: simulaciones fijas de MCTS (None: usar el plazo temporal).
    """
    depth: int = 2
    time_limit_s: float = 0.2
    seed: int = 0
    simulations: Optional[int] = None

    def seed_for_ply(self, ply: int) -> int:
        return int(self.seed) + int(ply)


AgentFactory = Callable[[AgentConfig], object]


def build_agent(factories: dict, label: str, config: AgentConfig):
    """Construye el agente `label` con su fabrica; `None` significa humano."""
    if label not in factories:
        raise KeyError(f"agente desconocido: {label!r}")
    factory = factories[label]
    return None if factory is None else factory(config)


def agent_label(agent) -> str:
    """Nombre a mostrar y registrar: `agent.name` o 'Humano' si es None."""
    if agent is None:
        return HUMAN_LABEL
    return str(getattr(agent, "name", type(agent).__name__))


@dataclass
class MoveRecord:
    """Una jugada aplicada al estado real (agente o humano).

    Las primeras columnas son exactamente CSV_FIELDS. `elapsed_s` es el tiempo
    REAL medido por el controlador alrededor de `choose` (incluye la copia);
    `agent_elapsed_s` es el que reporta el propio agente en SearchStats.
    `termination` y `official_result` son el estado de la partida justo despues
    de esta jugada; al exportar se sustituyen por el estado final (ver export_csv).
    """
    game_id: str
    opening_id: str
    seed: int
    white_agent: str
    black_agent: str
    ply: int                     # 1, 2, 3, ... (numero de la jugada en la partida)
    move_uci: str
    nodes: int = 0
    leaves: int = 0
    cutoffs: int = 0
    completed_depth: int = 0
    elapsed_s: float = 0.0
    simulations: int = 0
    time_exceeded: bool = False
    termination: str = "ongoing"
    official_result: str = "*"
    # --- extra (no van al CSV del enunciado) ---
    color: str = "white"
    agent: str = HUMAN_LABEL
    san: str = ""
    score: Optional[float] = None
    agent_elapsed_s: float = 0.0
    fen_before: str = ""

    def csv_row(self, final_termination: str | None = None,
                final_result: str | None = None) -> dict:
        row = {name: getattr(self, name) for name in CSV_FIELDS}
        if final_termination is not None:
            row["termination"] = final_termination
        if final_result is not None:
            row["official_result"] = final_result
        row["elapsed_s"] = round(float(row["elapsed_s"]), 6)
        row["time_exceeded"] = int(bool(row["time_exceeded"]))
        return row


@dataclass
class TurnReport:
    """Respuesta de cada operacion del controlador (tambien se envia a on_update).

    status: 'applied' | 'human' | 'busy' | 'over' | 'stale' | 'error' | 'undone'
            | 'reset' | 'agents' | 'rejected'
    """
    status: str
    message: str
    record: Optional[MoveRecord] = None
    decision: Optional[Decision] = None


class GameController:
    """Coordina el entorno real con los dos jugadores (agente o humano = None)."""

    def __init__(self, env: ChessEnvironment | None = None, white=None, black=None,
                 config: AgentConfig | None = None, *, game_id: str = "gui-001",
                 opening_id: str = "", tolerance_s: float = DEFAULT_TIME_TOLERANCE_S,
                 on_update: Callable[[TurnReport], None] | None = None):
        self.env = env if env is not None else ChessEnvironment()
        self.white = white
        self.black = black
        self.config = config if config is not None else AgentConfig()
        self.game_id = game_id
        self.opening_id = opening_id
        self.tolerance_s = tolerance_s
        self.on_update = on_update
        self.records: list[MoveRecord] = []
        self.errors: list[str] = []
        self.last_report: TurnReport | None = None
        self.searching = False        # True solo mientras un agente ejecuta choose()
        self.running = False          # True mientras el bucle cooperativo esta activo
        self._pause_requested = False
        self._games_started = 1

    # ------------------------------------------------------------- consultas
    def agent_for(self, color: chess.Color):
        return self.white if color == chess.WHITE else self.black

    def current_agent(self):
        return self.agent_for(self.env.board.turn)

    def is_human_turn(self) -> bool:
        return self.current_agent() is None

    def mode(self) -> str:
        humans = (self.white is None) + (self.black is None)
        return {2: "humano-humano", 1: "humano-agente", 0: "agente-agente"}[humans]

    def busy(self) -> bool:
        return self.searching

    # ---------------------------------------------------------- notificacion
    def _ctl_emit(self, report: TurnReport) -> TurnReport:
        self.last_report = report
        if report.status == "error":
            self.errors.append(report.message)
        if self.on_update is not None:
            self.on_update(report)
        return report

    def _ctl_make_record(self, move: chess.Move, color: chess.Color, fen_before: str,
                         san: str, agent, seed: int, decision: Decision | None,
                         elapsed: float, exceeded: bool) -> MoveRecord:
        stats = decision.stats if decision is not None and decision.stats is not None else SearchStats()
        return MoveRecord(
            game_id=self.game_id, opening_id=self.opening_id, seed=seed,
            white_agent=agent_label(self.white), black_agent=agent_label(self.black),
            ply=self.env.ply_count, move_uci=move.uci(),
            nodes=int(stats.nodes), leaves=int(stats.leaves), cutoffs=int(stats.cutoffs),
            completed_depth=int(stats.completed_depth), elapsed_s=float(elapsed),
            simulations=int(stats.simulations), time_exceeded=bool(exceeded),
            termination=self.env.termination(), official_result=self.env.official_result(),
            color="white" if color == chess.WHITE else "black", agent=agent_label(agent),
            san=san, score=None if decision is None else decision.score,
            agent_elapsed_s=float(stats.elapsed_s), fen_before=fen_before)

    # ------------------------------------------------------- turno de agente
    def request_turn(self) -> TurnReport:
        """AL_SOLICITAR_TURNO: aplica como maximo UNA jugada de agente."""
        if self.searching:
            return self._ctl_emit(TurnReport("busy", "Hay una busqueda activa; espere o pause."))
        if self.env.is_over():
            return self._ctl_emit(TurnReport(
                "over", f"Partida terminada ({self.env.termination()}, "
                        f"resultado {self.env.official_result()}); no se pide jugada."))
        color = self.env.board.turn
        agent = self.agent_for(color)
        if agent is None:
            side = "blancas" if color == chess.WHITE else "negras"
            return self._ctl_emit(TurnReport("human", f"Turno humano ({side}): use Mover."))

        version = self.env.version
        board = self.env.copy_for_agent()
        fen_before = board.fen()
        seed = self.config.seed_for_ply(self.env.ply_count)
        name = agent_label(agent)
        self.searching = True
        start = time.perf_counter()
        try:
            decision = agent.choose(board, time_limit_s=self.config.time_limit_s, seed=seed)
        except Exception as exc:  # el agente fallo: no se toca el estado real
            return self._ctl_emit(TurnReport(
                "error", f"{name} lanzo {type(exc).__name__}: {exc}. Estado sin cambios."))
        finally:
            self.searching = False
        elapsed = time.perf_counter() - start
        limit = self.config.time_limit_s
        exceeded = bool(limit and limit > 0 and elapsed > limit + self.tolerance_s)

        if self.env.version != version:
            return self._ctl_emit(TurnReport(
                "stale", f"Decision de {name} descartada: el estado cambio mientras pensaba.",
                decision=decision))
        move = None if decision is None else decision.move
        if isinstance(move, str):
            try:
                move = chess.Move.from_uci(move)
            except ValueError:
                move = None
        if move is None:
            return self._ctl_emit(TurnReport(
                "error", f"{name} devolvio None en un estado no terminal. Estado sin cambios.",
                decision=decision))
        if move not in self.env.board.legal_moves:
            return self._ctl_emit(TurnReport(
                "error", f"{name} devolvio la jugada ilegal {move}. Estado sin cambios.",
                decision=decision))
        san = self.env.board.san(move)
        try:
            self.env.apply(move)
        except IllegalMoveError as exc:  # defensa redundante: apply valida de nuevo
            return self._ctl_emit(TurnReport("error", str(exc), decision=decision))
        record = self._ctl_make_record(move, color, fen_before, san, agent, seed,
                                       decision, elapsed, exceeded)
        self.records.append(record)
        msg = f"{name} jugo {san} ({move.uci()}) en {elapsed:.3f} s"
        if exceeded:
            msg += f" — EXCEDIO el presupuesto de {limit:g} s"
        return self._ctl_emit(TurnReport("applied", msg, record=record, decision=decision))

    # -------------------------------------------------------- jugada humana
    def human_move(self, move) -> TurnReport:
        """Valida y aplica una jugada humana. Toda jugada pasa por env.apply."""
        if self.searching:
            return self._ctl_emit(TurnReport("busy", "Hay una busqueda activa; espere."))
        if self.env.is_over():
            return self._ctl_emit(TurnReport(
                "over", f"Partida terminada ({self.env.termination()}); no se aceptan jugadas."))
        if not self.is_human_turn():
            return self._ctl_emit(TurnReport(
                "rejected", f"Le toca al agente {agent_label(self.current_agent())}; "
                            "use 'Jugar turno del agente'."))
        if isinstance(move, str):
            try:
                move = chess.Move.from_uci(move)
            except ValueError:
                return self._ctl_emit(TurnReport("rejected", f"Texto de jugada invalido: {move!r}."))
        if move is None or move not in self.env.board.legal_moves:
            return self._ctl_emit(TurnReport(
                "rejected", f"Movimiento ilegal {move}. El tablero conserva su estado."))
        color = self.env.board.turn
        fen_before = self.env.board.fen()
        san = self.env.board.san(move)
        self.env.apply(move)
        record = self._ctl_make_record(move, color, fen_before, san, None,
                                       self.config.seed_for_ply(self.env.ply_count - 1),
                                       None, 0.0, False)
        self.records.append(record)
        return self._ctl_emit(TurnReport("applied", f"Humano jugo {san} ({move.uci()}).",
                                         record=record))

    # -------------------------------------------------------------- deshacer
    def undo_plies_needed(self) -> int:
        """Cuantos plies deshace la politica en el estado actual."""
        stack = self.env.board.move_stack
        if not stack:
            return 0
        if self.mode() != "humano-agente":
            return 1
        # Al deshacer k plies le toca mover a quien hizo la jugada stack[-k].
        # Se deshace 1; si el que queda al turno es el agente, se deshace otro.
        mover_last = not self.env.board.turn          # quien hizo la ultima jugada
        if self.agent_for(mover_last) is not None and len(stack) >= 2:
            return 2
        return 1

    def undo(self) -> TurnReport:
        if self.searching:
            return self._ctl_emit(TurnReport("busy", "No se deshace con una busqueda activa."))
        if self.running:
            return self._ctl_emit(TurnReport(
                "busy", "El bucle automatico esta en marcha: pause primero y luego deshaga."))
        n = self.undo_plies_needed()
        if n == 0:
            return self._ctl_emit(TurnReport("rejected", "No hay jugadas para deshacer."))
        done = self.env.undo(n)
        self.records = [r for r in self.records if r.ply <= self.env.ply_count]
        return self._ctl_emit(TurnReport(
            "undone", f"Deshecho(s) {done} ply ({self.mode()}). Turno de "
                      f"{'blancas' if self.env.board.turn else 'negras'}."))

    # -------------------------------------------- nueva partida / agentes
    def new_game(self, fen: str | None = None, *, game_id: str | None = None,
                 opening_id: str | None = None) -> TurnReport:
        if self.searching:
            return self._ctl_emit(TurnReport("busy", "Hay una busqueda activa; espere."))
        if fen is not None:
            try:
                board = chess.Board(fen)
            except ValueError as exc:
                return self._ctl_emit(TurnReport("rejected", f"FEN invalido: {exc}."))
            if not board.is_valid():
                return self._ctl_emit(TurnReport("rejected", f"Posicion invalida: {board.status()!r}."))
        self._pause_requested = True   # un bucle activo termina en su proxima cesion
        self.env.reset(fen if fen is not None else chess.STARTING_FEN)
        self._games_started += 1
        self.game_id = game_id or f"gui-{self._games_started:03d}"
        if opening_id is not None:
            self.opening_id = opening_id
        self.records = []
        self.errors = []
        return self._ctl_emit(TurnReport("reset", f"Nueva partida {self.game_id}."))

    def set_agents(self, white=None, black=None, config: AgentConfig | None = None) -> TurnReport:
        """Cambia jugadores (None = humano). Permitido entre turnos, no durante choose()."""
        if self.searching:
            return self._ctl_emit(TurnReport("busy", "No se cambian agentes durante una busqueda."))
        self.white, self.black = white, black
        if config is not None:
            self.config = config
        return self._ctl_emit(TurnReport(
            "agents", f"Blancas: {agent_label(white)} · Negras: {agent_label(black)} ({self.mode()})."))

    # ------------------------------------------------- bucle cooperativo
    def pause(self) -> None:
        """Pide detener el bucle; se atiende en la siguiente cesion (entre turnos)."""
        self._pause_requested = True

    async def run_async(self, *, delay_s: float = 0.0, max_turns: int | None = None) -> str:
        """Juega turnos de agente seguidos cediendo el control entre turnos.

        Cada turno es SINCRONO (bloquea mientras el agente busca, ~presupuesto);
        entre turnos `await asyncio.sleep(delay_s)` devuelve el control al bucle de
        eventos del kernel, que asi procesa el clic de Pausar. Devuelve el motivo
        de parada: 'paused' | 'terminal' | 'truncated' | 'human' | 'error' |
        'stale' | 'busy' | 'max_turns'.
        """
        if self.running or self.searching:
            return "busy"
        self.running = True
        self._pause_requested = False
        turns = 0
        try:
            while True:
                if self._pause_requested:
                    return "paused"
                if self.env.is_over():
                    return self.env.status()
                if self.is_human_turn():
                    return "human"
                if max_turns is not None and turns >= max_turns:
                    return "max_turns"
                report = self.request_turn()
                if report.status != "applied":
                    return report.status
                turns += 1
                await asyncio.sleep(delay_s)   # cesion: aqui se atienden los clics
        finally:
            self.running = False

    def play_until_stop(self, max_turns: int | None = None) -> str:
        """Version sincronica (sin bucle de eventos): solo para pruebas y scripts."""
        turns = 0
        while not self.env.is_over() and not self.is_human_turn():
            if max_turns is not None and turns >= max_turns:
                return "max_turns"
            report = self.request_turn()
            if report.status != "applied":
                return report.status
            turns += 1
        return self.env.status() if self.env.is_over() else "human"

    # ---------------------------------------------------------- exportacion
    def pgn_headers(self) -> dict:
        cfg = self.config
        return {
            "Event": "Taller 3 IA UTP - interfaz grafica",
            "Site": "Jupyter",
            "Date": time.strftime("%Y.%m.%d"),
            "Round": self.game_id,
            "White": agent_label(self.white),
            "Black": agent_label(self.black),
            "GameId": self.game_id,
            "Opening": self.opening_id or "-",
            "SeedBase": cfg.seed,
            "SeedPolicy": "seed_base + ply",
            "TimeBudgetS": cfg.time_limit_s,
            "TimeToleranceS": self.tolerance_s,
            "Depth": cfg.depth,
            "Simulations": cfg.simulations if cfg.simulations is not None else "-",
            "Mode": self.mode(),
        }

    def export_pgn(self, path: str | None = None) -> str:
        text = str(self.env.to_pgn(self.pgn_headers())) + "\n"
        if path:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
        return text

    def export_csv(self, path: str | None = None, *, final: bool = True) -> str:
        """CSV con EXACTAMENTE las columnas CSV_FIELDS.

        Con `final=True` las columnas de partida `termination` y `official_result`
        llevan el estado actual de la partida en todas las filas (como game_id o
        white_agent); con `final=False`, el estado justo despues de cada jugada.
        """
        term = self.env.termination() if final else None
        res = self.env.official_result() if final else None
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for rec in self.records:
            writer.writerow(rec.csv_row(term, res))
        text = buf.getvalue()
        if path:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        return text
