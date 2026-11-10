"""Interfaz grafica (ipywidgets) del taller: `ChessApp`.

Amplia la base suministrada `ChessView` (celda 5 del enunciado) SIN heredar de
ella: el cuaderno del profesor ya define `ChessView` y el paquete debe funcionar
tambien fuera del cuaderno. Se conserva su idea (listas origen/destino/promocion,
boton Mover, destinos posibles, SVG con ultimo movimiento y jaque) y se agregan
las ampliaciones obligatorias: selector de agente por color (incluido «Humano»),
«Jugar turno del agente», «Iniciar/Pausar», «Nueva partida», «Deshacer»,
profundidad, plazo, semilla y simulaciones, estado de la partida, historial SAN,
registro visible de cada decision y exportacion PGN/CSV.

Toda la logica de turnos vive en `chess_ai.controller.GameController`; esta clase
solo traduce clics en llamadas al controlador y redibuja en `on_update`.
No se crea ningun widget al importar el modulo, solo al instanciar `ChessApp`.

Uso en el cuaderno:

    app = ChessApp({"Humano": None, "Aleatorio": lambda cfg: RandomAgent(),
                    "Alfa-beta": lambda cfg: AlphaBetaAgent(depth=cfg.depth)},
                   white="Humano", black="Alfa-beta")
    app.display()
"""
from __future__ import annotations

import asyncio
import html
import os

import chess
import chess.svg
import ipywidgets as widgets

from chess_ai.controller import (HUMAN_LABEL, AgentConfig, GameController, TurnReport,
                                 agent_label, build_agent)
from chess_ai.environment import ChessEnvironment

_GUI_STATUS_ES = {"ongoing": "en curso", "terminal": "terminal", "truncated": "truncada"}
_GUI_REPORT_COLORS = {"applied": "#1b5e20", "error": "#b71c1c", "rejected": "#b71c1c",
                      "stale": "#e65100", "busy": "#e65100", "over": "#4a148c"}
_GUI_PROMOTIONS = {"q": chess.QUEEN, "r": chess.ROOK, "b": chess.BISHOP, "n": chess.KNIGHT}


class ChessApp:
    """Aplicacion de ajedrez con los tres modos: humano-humano, humano-agente y
    agente-agente.

    `factories`: {etiqueta: fabrica(AgentConfig) -> Agent}; la etiqueta «Humano»
    se agrega siempre con valor None. Las fabricas se vuelven a llamar cuando
    cambia el selector o la configuracion (profundidad, plazo, semilla, sims).
    """

    def __init__(self, factories: dict | None = None, *, white: str = HUMAN_LABEL,
                 black: str = HUMAN_LABEL, config: AgentConfig | None = None,
                 fen: str | None = None, max_plies: int | None = None,
                 export_dir: str = os.path.join("resultados", "interfaz"),
                 board_size: int = 440, auto_reply: bool = True, delay_s: float = 0.3):
        self.factories = {HUMAN_LABEL: None}
        for label, factory in (factories or {}).items():
            if label != HUMAN_LABEL:
                self.factories[label] = factory
        for label in (white, black):
            if label not in self.factories:
                raise KeyError(f"agente desconocido: {label!r}")
        cfg = config if config is not None else AgentConfig()
        self.env = ChessEnvironment(fen, max_plies=max_plies)
        self.controller = GameController(self.env, None, None, cfg,
                                         on_update=self._gui_on_update)
        self.export_dir = export_dir
        self.board_size = board_size
        self._task = None
        self._loop_active = False   # True desde Iniciar hasta que la tarea termina
        self._agents_key = None
        self._message = ""
        self._message_color = "#333333"
        self._gui_build(white, black, cfg, max_plies, auto_reply, delay_s)
        self._gui_sync_agents()
        self._message = "Listo. Elija agentes o juegue con Mover."
        self.render()

    # ------------------------------------------------------------ widgets
    def _gui_build(self, white, black, cfg, max_plies, auto_reply, delay_s):
        W = widgets
        wide = {"description_width": "110px"}
        lay = W.Layout(width="260px")
        labels = list(self.factories)
        self.white_select = W.Dropdown(options=labels, value=white, description="Blancas",
                                       style=wide, layout=lay)
        self.black_select = W.Dropdown(options=labels, value=black, description="Negras",
                                       style=wide, layout=lay)
        self.depth = W.BoundedIntText(value=cfg.depth, min=1, max=10, description="Profundidad",
                                      style=wide, layout=lay)
        self.time_limit = W.BoundedFloatText(value=cfg.time_limit_s, min=0.0, max=600.0, step=0.1,
                                             description="Plazo (s)", style=wide, layout=lay)
        self.seed = W.IntText(value=cfg.seed, description="Semilla base", style=wide, layout=lay)
        self.simulations = W.BoundedIntText(value=cfg.simulations or 0, min=0, max=10_000_000,
                                            description="Sims MCTS (0=plazo)", style=wide, layout=lay)
        self.max_plies = W.BoundedIntText(value=max_plies or 0, min=0, max=10_000,
                                          description="Máx. plies (0=∞)", style=wide, layout=lay)
        self.delay = W.BoundedFloatText(value=delay_s, min=0.0, max=10.0, step=0.1,
                                        description="Pausa bucle (s)", style=wide, layout=lay)
        self.auto_reply = W.Checkbox(value=auto_reply, description="El agente responde solo",
                                     indent=False)
        self.show_arrow = W.Checkbox(value=True, description="Flecha de la decisión", indent=False)
        self.flip = W.Checkbox(value=False, description="Ver desde negras", indent=False)

        self.origin = W.Dropdown(options=chess.SQUARE_NAMES, value="e2", description="Origen",
                                 layout=W.Layout(width="150px"))
        self.target = W.Dropdown(options=chess.SQUARE_NAMES, value="e4", description="Destino",
                                 layout=W.Layout(width="150px"))
        self.promotion = W.Dropdown(options=[("Dama", "q"), ("Torre", "r"), ("Alfil", "b"),
                                             ("Caballo", "n")], description="Promoción",
                                    layout=W.Layout(width="200px"))
        self.move_button = W.Button(description="Mover", button_style="primary")
        self.destinations = W.HTML()

        self.agent_button = W.Button(description="Jugar turno del agente", button_style="info",
                                     layout=W.Layout(width="190px"))
        self.run_button = W.Button(description="Iniciar", button_style="success")
        self.new_button = W.Button(description="Nueva partida")
        self.undo_button = W.Button(description="Deshacer")
        self.refresh_button = W.Button(description="Actualizar vista")
        self.pgn_button = W.Button(description="Exportar PGN")
        self.csv_button = W.Button(description="Exportar CSV")
        self.fen_text = W.Text(value="", placeholder="vacío = posición inicial",
                               description="FEN", layout=W.Layout(width="440px"))

        self.board_html = W.HTML(layout=W.Layout(width=f"{self.board_size + 10}px"))
        self.status_html = W.HTML()
        self.message_html = W.HTML()
        self.history_html = W.HTML()
        self.log_html = W.HTML()
        self.export_area = W.Textarea(value="", layout=W.Layout(width="100%", height="120px"),
                                      placeholder="Aquí aparece el PGN o CSV exportado")

        self.move_button.on_click(self.on_move)
        self.agent_button.on_click(self.on_agent_turn)
        self.run_button.on_click(self.on_toggle_run)
        self.new_button.on_click(self.on_new_game)
        self.undo_button.on_click(self.on_undo)
        self.refresh_button.on_click(lambda _: self.render())
        self.pgn_button.on_click(self.on_export_pgn)
        self.csv_button.on_click(self.on_export_csv)
        self.origin.observe(self._gui_on_origin, names="value")
        self.white_select.observe(self._gui_on_selector, names="value")
        self.black_select.observe(self._gui_on_selector, names="value")
        self.max_plies.observe(self._gui_on_max_plies, names="value")
        for w in (self.show_arrow, self.flip):
            w.observe(lambda _: self.render(), names="value")

        players = W.VBox([W.HTML("<b>Jugadores y presupuesto</b>"), self.white_select,
                          self.black_select, self.depth, self.time_limit, self.seed,
                          self.simulations, self.max_plies, self.delay, self.auto_reply,
                          self.show_arrow, self.flip])
        human = W.VBox([W.HTML("<b>Jugada humana</b>"),
                        W.HBox([self.origin, self.target]),
                        W.HBox([self.promotion, self.move_button]), self.destinations])
        actions = W.VBox([W.HTML("<b>Partida</b>"),
                          W.HBox([self.agent_button, self.run_button]),
                          W.HBox([self.new_button, self.undo_button, self.refresh_button]),
                          self.fen_text,
                          W.HBox([self.pgn_button, self.csv_button])])
        right = W.VBox([self.status_html, self.message_html, human, actions, players])
        self.ui = W.VBox([W.HBox([self.board_html, right]),
                          W.HTML("<b>Historial SAN</b>"), self.history_html,
                          W.HTML("<b>Registro de decisiones</b> (más reciente arriba)"),
                          self.log_html, self.export_area])

    def display(self):
        from IPython.display import display as _ipy_display
        _ipy_display(self.ui)

    def _ipython_display_(self):
        self.display()

    # ---------------------------------------------------- configuracion
    def current_config(self) -> AgentConfig:
        sims = int(self.simulations.value)
        return AgentConfig(depth=int(self.depth.value), time_limit_s=float(self.time_limit.value),
                           seed=int(self.seed.value), simulations=sims if sims > 0 else None)

    def _gui_sync_agents(self) -> bool:
        """(Re)construye los agentes si cambiaron selectores o configuracion."""
        cfg = self.current_config()
        key = (self.white_select.value, self.black_select.value, cfg.depth, cfg.time_limit_s,
               cfg.seed, cfg.simulations)
        if key == self._agents_key:
            return True
        if self.controller.searching:
            return False
        try:
            white = build_agent(self.factories, self.white_select.value, cfg)
            black = build_agent(self.factories, self.black_select.value, cfg)
        except Exception as exc:
            self._gui_set_message(f"No se pudo crear el agente: {type(exc).__name__}: {exc}",
                                  "#b71c1c")
            return False
        self._agents_key = key
        self.controller.set_agents(white, black, cfg)
        return True

    def _gui_on_selector(self, _change):
        self._gui_sync_agents()

    def _gui_on_max_plies(self, change):
        self.env.max_plies = int(change["new"]) or None
        self.render()

    def _gui_on_origin(self, _change):
        dests = self._gui_destinations()
        if dests and chess.parse_square(self.target.value) not in dests:
            self.target.value = chess.square_name(dests[0])
        self.render()

    # ---------------------------------------------------------- acciones
    def on_move(self, _=None) -> TurnReport:
        """Jugada humana con las listas (como la base). Siempre pasa por env.apply."""
        board = self.env.board
        src = chess.parse_square(self.origin.value)
        dst = chess.parse_square(self.target.value)
        piece = board.piece_at(src)
        promo = None
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(dst) in (0, 7):
            promo = _GUI_PROMOTIONS[self.promotion.value]
        self._gui_sync_agents()
        report = self.controller.human_move(chess.Move(src, dst, promotion=promo))
        if (report.status == "applied" and self.auto_reply.value and not self.env.is_over()
                and not self.controller.is_human_turn()):
            self._gui_start_loop()    # respuesta automatica: juega hasta el turno humano
        return report

    def on_agent_turn(self, _=None) -> TurnReport | None:
        if self.controller.running:
            self._gui_set_message("El bucle automático está en marcha; use Pausar.", "#e65100")
            return None
        if not self._gui_sync_agents():
            return None
        return self.controller.request_turn()

    def on_toggle_run(self, _=None):
        if self.controller.running or self._loop_active:
            self.controller.pause()
            self._gui_set_message("Pausa solicitada: se atiende al terminar el turno en curso.",
                                  "#e65100")
            return
        self._gui_start_loop(require_loop=True)

    def on_new_game(self, _=None) -> TurnReport:
        fen = self.fen_text.value.strip() or None
        self.env.max_plies = int(self.max_plies.value) or None
        self._gui_sync_agents()
        return self.controller.new_game(fen)

    def on_undo(self, _=None) -> TurnReport:
        return self.controller.undo()

    def on_export_pgn(self, _=None) -> str:
        path = self._gui_export_path("pgn")
        text = self.controller.export_pgn(path)
        self.export_area.value = text
        self._gui_set_message(f"PGN guardado en {path}", "#1b5e20")
        return path

    def on_export_csv(self, _=None) -> str:
        path = self._gui_export_path("csv")
        text = self.controller.export_csv(path)
        self.export_area.value = text
        self._gui_set_message(f"CSV ({len(self.controller.records)} filas) guardado en {path}",
                              "#1b5e20")
        return path

    def _gui_export_path(self, ext: str) -> str:
        os.makedirs(self.export_dir, exist_ok=True)
        return os.path.join(self.export_dir, f"{self.controller.game_id}.{ext}")

    # ------------------------------------------------ bucle cooperativo
    def _gui_start_loop(self, require_loop: bool = False):
        if not self._gui_sync_agents():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            # Fuera de un kernel no hay bucle de eventos al que ceder.
            if require_loop:
                self._gui_set_message("No hay bucle de eventos activo (fuera de Jupyter): "
                                      "use 'Jugar turno del agente'.", "#e65100")
            else:
                self.controller.play_until_stop()
            return
        self._loop_active = True
        self.run_button.description = "Pausar"
        self.run_button.button_style = "warning"
        self._task = loop.create_task(self._gui_run_task(float(self.delay.value)))

    async def _gui_run_task(self, delay_s: float) -> str:
        reason = "error"
        try:
            reason = await self.controller.run_async(delay_s=delay_s)
        except Exception as exc:   # en una tarea los errores serian silenciosos
            self._message = f"Error en el bucle: {type(exc).__name__}: {exc}"
            self._message_color = "#b71c1c"
        else:
            reasons = {"paused": "pausado", "terminal": "partida terminada",
                       "truncated": "límite de plies (truncada)", "human": "turno humano",
                       "error": "error del agente", "stale": "decisión obsoleta",
                       "busy": "ya había un bucle activo"}
            self._message += f" · Bucle detenido: {reasons.get(reason, reason)}."
        finally:
            # OJO: aqui la tarea aun no esta 'done()'; por eso se usa una bandera.
            self._loop_active = False
            self.render()
        return reason

    # ------------------------------------------------------- vista
    def _gui_on_update(self, report: TurnReport):
        self._message = report.message
        self._message_color = _GUI_REPORT_COLORS.get(report.status, "#333333")
        self.render()

    def _gui_set_message(self, text: str, color: str = "#333333"):
        self._message, self._message_color = text, color
        self.render()

    def _gui_destinations(self) -> list[int]:
        src = chess.parse_square(self.origin.value)
        seen, out = set(), []
        for m in self.env.board.legal_moves:
            if m.from_square == src and m.to_square not in seen:
                seen.add(m.to_square)
                out.append(m.to_square)
        return sorted(out)

    def render(self):
        ctl, env, board = self.controller, self.env, self.env.board
        running = ctl.running or self._loop_active
        self.run_button.description = "Pausar" if running else "Iniciar"
        self.run_button.button_style = "warning" if running else "success"

        # --- tablero
        src = chess.parse_square(self.origin.value)
        dests = self._gui_destinations()
        fill = {sq: "#7fb3d5aa" for sq in dests}
        if dests:
            fill[src] = "#f4d03faa"
        arrows = []
        last = board.peek() if board.move_stack else None
        last_rec = ctl.records[-1] if ctl.records else None
        if (self.show_arrow.value and last is not None and last_rec is not None
                and last_rec.agent != HUMAN_LABEL and last_rec.move_uci == last.uci()):
            arrows.append(chess.svg.Arrow(last.from_square, last.to_square, color="#1565c0cc"))
        check = board.king(board.turn) if board.is_check() else None
        self.board_html.value = chess.svg.board(
            board, size=self.board_size, lastmove=last, check=check, arrows=arrows, fill=fill,
            orientation=chess.BLACK if self.flip.value else chess.WHITE)

        # --- destinos posibles
        if dests:
            names = ", ".join(chess.square_name(s) for s in dests)
            self.destinations.value = f"Destinos de <b>{self.origin.value}</b>: {names}"
        else:
            self.destinations.value = (f"Sin jugadas legales desde <b>{self.origin.value}</b> "
                                       "(casilla vacía, pieza del rival o bloqueada).")

        # --- estado
        turn = "blancas" if board.turn == chess.WHITE else "negras"
        status = env.status()
        limit = f"/{env.max_plies}" if env.max_plies else ""
        last_txt = "—"
        if last_rec is not None:
            last_txt = f"{last_rec.san} ({last_rec.move_uci}) por {html.escape(last_rec.agent)}"
        check_txt = " · <b style='color:#b71c1c'>¡Jaque!</b>" if board.is_check() else ""
        self.status_html.value = (
            f"<div style='line-height:1.5'>"
            f"<b>Modo:</b> {ctl.mode()} · <b>Partida:</b> {html.escape(ctl.game_id)}<br>"
            f"<b>Turno:</b> {turn} ({html.escape(agent_label(ctl.current_agent()))}){check_txt}<br>"
            f"<b>Último movimiento:</b> {last_txt}<br>"
            f"<b>Estado:</b> {_GUI_STATUS_ES.get(status, status)} · "
            f"<b>Resultado:</b> {env.official_result()} · <b>Terminación:</b> {env.termination()}"
            f" · <b>Plies:</b> {env.ply_count}{limit}<br>"
            f"<b>Búsqueda activa:</b> {'sí' if ctl.searching else 'no'} · "
            f"<b>Bucle:</b> {'en marcha' if running else 'detenido'}</div>")
        self.message_html.value = (f"<div style='color:{self._message_color}'>"
                                   f"{html.escape(self._message)}</div>")

        # --- historial SAN
        san = chess.Board(env.start_fen).variation_san(board.move_stack) if board.move_stack else ""
        self.history_html.value = f"<code>{html.escape(san) or 'Sin jugadas'}</code>"

        # --- registro de decisiones
        head = ("<tr><th>Ply</th><th>Color</th><th>Agente</th><th>Jugada</th><th>Valor</th>"
                "<th>Nodos</th><th>Hojas</th><th>Podas</th><th>Prof.</th><th>Tiempo (s)</th>"
                "<th>Sims</th><th>Semilla</th><th>Exceso</th></tr>")
        rows = []
        for r in reversed(ctl.records[-20:]):
            score = "—" if r.score is None else f"{r.score:.1f}"
            exceeded = "<b style='color:#b71c1c'>sí</b>" if r.time_exceeded else "no"
            rows.append(
                f"<tr><td>{r.ply}</td><td>{'B' if r.color == 'white' else 'N'}</td>"
                f"<td>{html.escape(r.agent)}</td><td>{r.san} ({r.move_uci})</td><td>{score}</td>"
                f"<td>{r.nodes}</td><td>{r.leaves}</td><td>{r.cutoffs}</td>"
                f"<td>{r.completed_depth}</td><td>{r.elapsed_s:.3f}</td><td>{r.simulations}</td>"
                f"<td>{r.seed}</td><td>{exceeded}</td></tr>")
        style = ("<style>.chessapp-log td,.chessapp-log th{padding:2px 6px;"
                 "border-bottom:1px solid #ddd;text-align:right}</style>")
        self.log_html.value = (style + "<table class='chessapp-log'>" + head + "".join(rows)
                               + "</table>") if rows else "<i>Sin decisiones todavía.</i>"
