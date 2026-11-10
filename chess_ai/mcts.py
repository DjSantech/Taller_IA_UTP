"""MCTS-UCT (AIMA 5.4): seleccion, expansion, simulacion (rollout) y retropropagacion.

Convenciones (ver apuntes/bitacora_M.md, entradas M-01 .. M-10):

* RECOMPENSA en [0, 1]: victoria 1, tablas 0.5, derrota 0. Un rollout que llega al
  limite de plies sin terminar se puntua con sigmoide(E / ROLLOUT_SCALE_CP), con E la
  evaluacion comun desde blancas; se cuenta como TRUNCADO, nunca como tablas.
* PERSPECTIVA. Cada nodo guarda `wins` (W) desde el jugador que HIZO la jugada que
  lleva a ese nodo (`node.mover`). Asi, al elegir entre los hijos de un nodo, UCT
  maximiza W/N para el jugador que esta AL TURNO en el padre: blancas maximizan para
  blancas en sus nodos y negras para negras en los suyos (pregunta 6).
* PRESUPUESTO. `simulations=N` fija el numero de simulaciones (reproducible exacto con
  la misma semilla). `simulations=None` usa el plazo `time_limit_s` del contrato:
  el numero de simulaciones depende entonces de la maquina y de su carga.
* JUGADA FINAL: hijo de la raiz con mas visitas; empate -> mayor valor medio;
  empate -> menor UCI (orden lexicografico, determinista).
* `Decision.score`: valor medio q del hijo elegido (probabilidad estimada de ganar
  del jugador raiz) llevado a centipeones con el logit inverso de la sigmoide:
  ROLLOUT_SCALE_CP * ln(q / (1 - q)), recortado a +-EVAL_BOUND. q tambien queda en
  `last_info["win_probability"]`. Si el hijo elegido es terminal se reporta su valor
  exacto (MATE_SCORE - 1 si gana el jugador raiz), igual que los agentes de minimax.
"""
from __future__ import annotations

import csv
import math
import random
import statistics
import time

import chess

from chess_ai.contract import Decision, SearchStats
from chess_ai.environment import (EVAL_BOUND, MATE_SCORE, Deadline, perspective_sign,
                                  search_outcome, terminal_value_white)
from chess_ai.evaluation import DEFAULT_EVALUATOR

# Escala de la sigmoide que lleva centipeones a [0, 1] (rollouts truncados) y del logit
# inverso que lleva el valor medio de vuelta a centipeones (Decision.score).
# Con 400 cp: +1 peon -> 0.56, +pieza menor -> 0.69, +dama -> 0.91 (< 1 = victoria real).
ROLLOUT_SCALE_CP = 400.0
MCTS_DEFAULT_SIMULATIONS = 200      # si no hay ni simulaciones ni plazo
MCTS_ROLLOUT_POLICIES = ("uniform", "captures")


def _mcts_sigmoid(cp: float, scale: float = ROLLOUT_SCALE_CP) -> float:
    """Centipeones desde blancas -> recompensa de blancas en (0, 1)."""
    x = max(-60.0, min(60.0, cp / scale))
    return 1.0 / (1.0 + math.exp(-x))


def _mcts_logit_cp(q: float, scale: float = ROLLOUT_SCALE_CP) -> float:
    """Inversa de la sigmoide: probabilidad en [0, 1] -> centipeones, recortada."""
    eps = 1e-6
    q = min(1.0 - eps, max(eps, q))
    return max(-EVAL_BOUND, min(EVAL_BOUND, scale * math.log(q / (1.0 - q))))


def _mcts_terminal_reward_white(outcome: chess.Outcome) -> float:
    """Recompensa exacta de un terminal desde blancas: 1, 0.5 o 0."""
    if outcome.winner is None:
        return 0.5
    return 1.0 if outcome.winner == chess.WHITE else 0.0


class _MCTSNode:
    """Nodo del arbol. `wins` se mide desde `mover` (quien jugo `move` para llegar aqui).

    `terminal` es la recompensa exacta desde blancas si el estado es terminal (o None).
    `untried` guarda las jugadas aun no expandidas (orden UCI barajado con la semilla;
    se expanden sacandolas del final de la lista).
    """

    __slots__ = ("move", "parent", "children", "untried", "visits", "wins", "mover",
                 "terminal", "depth")

    def __init__(self, move, parent, mover, depth):
        self.move = move
        self.parent = parent
        self.children = []
        self.untried = []
        self.visits = 0
        self.wins = 0.0
        self.mover = mover
        self.terminal = None
        self.depth = depth

    def mean(self) -> float:
        return self.wins / self.visits if self.visits else 0.0


class MCTSAgent:
    """Agente MCTS-UCT con recompensas en [0, 1] y perspectiva por nodo.

    Parametros:
        simulations: simulaciones por jugada (None -> usar `time_limit_s`).
        exploration: constante c de UCT. sqrt(2) es el valor de UCB1 para
            recompensas en [0, 1] (Kocsis y Szepesvari, 2006); ver M-03.
        rollout_limit: plies maximos del rollout antes de truncar (0 = evaluar la hoja).
        rollout_policy: "uniform" (uniforme entre legales) o "captures" (con
            probabilidad `capture_bias` elige al azar entre capturas si las hay).
        evaluator: E(s) desde blancas para puntuar rollouts truncados.
        restore: "push_pop" (por defecto, mas rapido; ver M-08) o "copy"
            (cada simulacion trabaja sobre `board.copy(stack=True)`).
    """

    def __init__(self, simulations: int | None = None, exploration: float = math.sqrt(2),
                 rollout_limit: int = 4, rollout_policy: str = "captures",
                 evaluator=DEFAULT_EVALUATOR, name: str = "MCTS",
                 capture_bias: float = 0.75, restore: str = "push_pop"):
        if rollout_policy not in MCTS_ROLLOUT_POLICIES:
            raise ValueError(f"rollout_policy debe ser una de {MCTS_ROLLOUT_POLICIES}")
        if restore not in ("push_pop", "copy"):
            raise ValueError("restore debe ser 'push_pop' o 'copy'")
        if simulations is not None and simulations < 1:
            raise ValueError("simulations debe ser >= 1 o None")
        self.simulations = simulations
        self.exploration = float(exploration)
        self.rollout_limit = int(rollout_limit)
        self.rollout_policy = rollout_policy
        self.capture_bias = float(capture_bias)
        self.evaluator = evaluator
        self.name = name
        self.restore = restore
        self.last_info: dict = {}
        self.last_root = None

    # ------------------------------------------------------------ perspectiva
    def _reward_for(self, mover: chess.Color, reward_white: float) -> float:
        """Recompensa desde el jugador `mover`. Punto unico de la perspectiva (prueba P6)."""
        return reward_white if mover == chess.WHITE else 1.0 - reward_white

    # ------------------------------------------------------------ piezas del ciclo
    def _new_node(self, board: chess.Board, move, parent, rng: random.Random) -> _MCTSNode:
        node = _MCTSNode(move, parent, not board.turn,
                         0 if parent is None else parent.depth + 1)
        outcome = search_outcome(board)
        if outcome is not None:
            node.terminal = _mcts_terminal_reward_white(outcome)
        else:
            moves = sorted(board.legal_moves, key=lambda m: m.uci())
            rng.shuffle(moves)
            node.untried = moves
        return node

    def _select_child(self, node: _MCTSNode) -> _MCTSNode:
        """UCT: argmax W/N + c*sqrt(ln N_padre / N_hijo); empate -> primer hijo expandido."""
        log_n = math.log(node.visits)
        c = self.exploration
        best, best_val = None, -math.inf
        for child in node.children:
            val = child.wins / child.visits + c * math.sqrt(log_n / child.visits)
            if val > best_val:
                best, best_val = child, val
        return best

    def _rollout(self, board: chess.Board, rng: random.Random, pushed: list) -> tuple[float, str]:
        """Juega hasta terminal o `rollout_limit` plies. Devuelve (recompensa blancas, tipo).

        Cada push se anota en `pushed[0]` para que `choose` deshaga todo en su finally.
        """
        for _ in range(self.rollout_limit):
            moves = list(board.legal_moves)
            if not moves:
                break
            choice = None
            if self.rollout_policy == "captures" and rng.random() < self.capture_bias:
                captures = [m for m in moves if board.is_capture(m)]
                if captures:
                    choice = rng.choice(captures)
            if choice is None:
                choice = rng.choice(moves)
            board.push(choice)
            pushed[0] += 1
            outcome = search_outcome(board)
            if outcome is not None:
                return _mcts_terminal_reward_white(outcome), "terminal"
        outcome = search_outcome(board)      # sin jugadas legales o rollout_limit == 0
        if outcome is not None:
            return _mcts_terminal_reward_white(outcome), "terminal"
        return _mcts_sigmoid(self.evaluator(board)), "truncated"

    def _simulate(self, root: _MCTSNode, board: chess.Board, rng: random.Random,
                  counters: dict) -> None:
        """Una simulacion completa. Deja `board` exactamente como lo recibio."""
        pushed = [0]
        try:
            node = root
            # 1. seleccion: bajar mientras el nodo este totalmente expandido y no sea terminal
            while node.terminal is None and not node.untried and node.children:
                node = self._select_child(node)
                board.push(node.move)
                pushed[0] += 1
            # 2. expansion de UNA accion no explorada
            if node.terminal is None and node.untried:
                move = node.untried.pop()
                board.push(move)
                pushed[0] += 1
                child = self._new_node(board, move, node, rng)
                node.children.append(child)
                node = child
                counters["nodes"] += 1
                counters["max_depth"] = max(counters["max_depth"], child.depth)
            # 3. simulacion
            if node.terminal is not None:
                reward_white, kind = node.terminal, "terminal"
            else:
                reward_white, kind = self._rollout(board, rng, pushed)
            counters[kind] += 1
            # 4. retropropagacion: cada nodo suma desde SU jugador (quien movio para llegar)
            while node is not None:
                node.visits += 1
                node.wins += self._reward_for(node.mover, reward_white)
                node = node.parent
        finally:
            for _ in range(pushed[0]):
                board.pop()

    # ------------------------------------------------------------ contrato
    def choose(self, board: chess.Board, *, time_limit_s: float = 0.0, seed: int = 0) -> Decision:
        """Decide una jugada. Restaura `board` (FEN y pila) incluso si hay excepcion."""
        deadline = Deadline(time_limit_s)
        stats = SearchStats()
        root_color = board.turn
        rng = random.Random(seed)
        outcome = search_outcome(board)
        if outcome is not None:
            stats.elapsed_s = deadline.elapsed()
            self.last_info = {"terminal": True}
            self.last_root = None
            return Decision(None, perspective_sign(root_color) * terminal_value_white(outcome, 0),
                            stats)

        root = self._new_node(board, None, None, rng)
        counters = {"nodes": 1, "max_depth": 0, "terminal": 0, "truncated": 0}
        if self.simulations is not None:
            budget, mode = self.simulations, "simulations"
        elif deadline.limit is not None:
            budget, mode = None, "time"
        else:
            budget, mode = MCTS_DEFAULT_SIMULATIONS, "default_simulations"
        work = board if self.restore == "push_pop" else None
        done = 0
        while True:
            if budget is not None and done >= budget:
                break
            if budget is None and deadline.expired():
                break
            if work is None:
                self._simulate(root, board.copy(stack=True), rng, counters)
            else:
                self._simulate(root, work, rng, counters)
            done += 1

        if root.children:
            best = max(root.children,
                       key=lambda ch: (ch.visits, ch.mean(), _mcts_uci_desc_key(ch.move)))
            move, q = best.move, best.mean()
            if best.terminal is not None:
                # el hijo elegido ES terminal: valor exacto con la escala comun (mate a 1 ply)
                r = self._reward_for(root_color, best.terminal)
                score = 0.0 if r == 0.5 else (MATE_SCORE - 1 if r == 1.0 else -(MATE_SCORE - 1))
            else:
                score = _mcts_logit_cp(q)
        else:
            # vencio el plazo antes de la primera simulacion: primera jugada del orden
            # barajado (legal) y la evaluacion estatica como mejor estimacion disponible.
            move, q = root.untried[-1], None
            score = perspective_sign(root_color) * self.evaluator(board)

        stats.simulations = done
        stats.nodes = counters["nodes"]
        stats.leaves = counters["terminal"] + counters["truncated"]
        stats.completed_depth = counters["max_depth"]
        stats.elapsed_s = deadline.elapsed()
        ordered = sorted(root.children, key=lambda ch: (-ch.visits, ch.move.uci()))
        self.last_root = root
        self.last_info = {
            "terminal": False,
            "budget_mode": mode,
            "simulations": done,
            "truncated_rollouts": counters["truncated"],
            "terminal_rollouts": counters["terminal"],
            "root_visits": {ch.move.uci(): ch.visits for ch in ordered},
            "root_values": {ch.move.uci(): round(ch.mean(), 4) for ch in ordered},
            "win_probability": q,
            "sims_per_s": done / stats.elapsed_s if stats.elapsed_s > 0 else float("nan"),
        }
        return Decision(move, score, stats)


def _mcts_uci_desc_key(move: chess.Move) -> tuple:
    """Clave para que, a igualdad de visitas y valor, `max` prefiera el MENOR UCI."""
    return tuple(-ord(ch) for ch in move.uci())


# ====================================================================== Experimento 4
# Tacticas verificadas por reglas (ver `mcts_verify_tactics`). `kind` define como se
# calcula el conjunto correcto: mate_in_1 = jugadas que dan mate; win_queen = capturas
# de la dama rival; avoid_mate_in_1 = jugadas tras las cuales el rival NO tiene mate en uno;
# mate_in_2 = jugadas (que no son mate) tras las cuales TODA respuesta permite mate en uno.
MCTS_TACTICS = [
    {"id": "T1_mate1_w_queen", "kind": "mate_in_1",
     "fen": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", "solutions": {"g6g7"}},
    {"id": "T2_mate1_w_backrank", "kind": "mate_in_1",
     "fen": "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1", "solutions": {"a1a8"}},
    {"id": "T3_mate1_b_backrank", "kind": "mate_in_1",
     "fen": "r5k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1", "solutions": {"a8a1"}},
    {"id": "T4_mate1_w_scholar", "kind": "mate_in_1",
     "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
     "solutions": {"h5f7"}},
    {"id": "T5_queen_w", "kind": "win_queen",
     "fen": "r3k2r/ppp2ppp/2n5/3q4/8/2N5/PPP2PPP/R3K2R w KQkq - 0 1", "solutions": {"c3d5"}},
    {"id": "T6_queen_b", "kind": "win_queen",
     "fen": "r3k2r/ppp2ppp/2n5/8/3Q4/8/PPP2PPP/R3K2R b KQkq - 0 1", "solutions": {"c6d4"}},
    {"id": "T7_avoid_b_scholar", "kind": "avoid_mate_in_1",
     "fen": "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3",
     "solutions": {"d7d5", "d8e7", "d8f6", "d8g5", "d8h4", "e8e7", "g7g6", "g8h6"}},
    {"id": "T8_avoid_w_qh4", "kind": "avoid_mate_in_1",
     "fen": "rnb1k1nr/pppp1ppp/8/2b1p3/4P2q/2N5/PPPP1PPP/R1BQKBNR w KQkq - 4 4",
     "solutions": {"d1e2", "d1f3", "d1g4", "d1h5", "d2d4", "e1e2", "g1h3", "g2g3"}},
    {"id": "T9_mate2_w_rooks", "kind": "mate_in_2",
     "fen": "2r3k1/1p3ppp/p7/8/8/3R4/P2R1PPP/6K1 w - - 0 1", "solutions": {"d3d8"}},
    {"id": "T10_mate2_b_rooks", "kind": "mate_in_2",
     "fen": "6k1/p2r1ppp/3r4/8/8/P7/1P3PPP/2R3K1 b - - 0 1", "solutions": {"d6d1"}},
]


def _mcts_has_mate_in_one(board: chess.Board) -> bool:
    for m in board.legal_moves:
        board.push(m)
        try:
            if board.is_checkmate():
                return True
        finally:
            board.pop()
    return False


def _mcts_forces_mate_next(board: chess.Board) -> bool:
    """Tras la jugada candidata (rival al turno, aun no es mate): TODA respuesta legal
    permite un mate en uno. Asi se define 'mate en dos' sin contar los mates en uno."""
    if board.is_checkmate():
        return False
    replies = list(board.legal_moves)
    if not replies:
        return False
    for r in replies:
        board.push(r)
        try:
            if not _mcts_has_mate_in_one(board):
                return False
        finally:
            board.pop()
    return True


def mcts_tactic_solutions(fen: str, kind: str) -> set:
    """Calcula con las REGLAS (no con el agente) el conjunto de jugadas correctas."""
    board = chess.Board(fen)
    out = set()
    for m in list(board.legal_moves):
        if kind == "win_queen":
            target = board.piece_at(m.to_square)
            if target is not None and target.piece_type == chess.QUEEN:
                out.add(m.uci())
            continue
        board.push(m)
        try:
            if kind == "mate_in_1" and board.is_checkmate():
                out.add(m.uci())
            elif kind == "avoid_mate_in_1" and not _mcts_has_mate_in_one(board):
                out.add(m.uci())
            elif kind == "mate_in_2" and _mcts_forces_mate_next(board):
                out.add(m.uci())
        finally:
            board.pop()
    return out


def mcts_verify_tactics(tactics=None) -> list[str]:
    """Devuelve la lista de discrepancias entre `solutions` y las reglas (vacia = todo bien)."""
    problems = []
    for t in tactics or MCTS_TACTICS:
        board = chess.Board(t["fen"])
        if not board.is_valid():
            problems.append(f"{t['id']}: FEN invalido")
            continue
        rules = mcts_tactic_solutions(t["fen"], t["kind"])
        if rules != set(t["solutions"]):
            problems.append(f"{t['id']}: reglas={sorted(rules)} declaradas={sorted(t['solutions'])}")
    return problems


def mcts_tactics_benchmark(positions_with_solutions=None, budgets=(50, 200, 800),
                           seeds=range(5), agent_factory=None, label: str = "",
                           **agent_kwargs) -> list[dict]:
    """Experimento 4: cada tactica x presupuesto (simulaciones fijas) x semilla -> una fila.

    `agent_factory(budget)` permite cambiar el agente; por defecto
    `MCTSAgent(simulations=budget, **agent_kwargs)`.
    """
    rows = []
    for t in positions_with_solutions or MCTS_TACTICS:
        for budget in budgets:
            agent = (agent_factory(budget) if agent_factory is not None
                     else MCTSAgent(simulations=budget, **agent_kwargs))
            for seed in seeds:
                board = chess.Board(t["fen"])
                t0 = time.perf_counter()
                d = agent.choose(board, time_limit_s=0.0, seed=seed)
                wall = time.perf_counter() - t0
                info = agent.last_info
                uci = d.move.uci() if d.move is not None else ""
                visits = info.get("root_visits", {})
                rows.append({
                    "config": label, "tactic": t["id"], "kind": t["kind"], "budget": budget, "seed": seed,
                    "move": uci, "correct": int(uci in t["solutions"]),
                    "elapsed_s": round(wall, 5), "simulations": d.stats.simulations,
                    "nodes": d.stats.nodes, "leaves": d.stats.leaves,
                    "max_depth": d.stats.completed_depth,
                    "best_visits": visits.get(uci, 0),
                    "visit_share": round(visits.get(uci, 0) / max(1, d.stats.simulations), 4),
                    "truncated_rollouts": info.get("truncated_rollouts", 0),
                    "terminal_rollouts": info.get("terminal_rollouts", 0),
                    "win_probability": round(info.get("win_probability") or 0.0, 4),
                    "score_cp": round(d.score, 1) if d.score is not None else "",
                    "n_solutions": len(t["solutions"]),
                    "n_legal": chess.Board(t["fen"]).legal_moves.count(),
                })
    return rows


def mcts_benchmark_summary(rows) -> list[dict]:
    """Por configuracion y presupuesto: tasa de acierto, tiempo medio y su desviacion."""
    out = []
    for config, budget in sorted({(r.get("config", ""), r["budget"]) for r in rows}):
        sel = [r for r in rows if r.get("config", "") == config and r["budget"] == budget]
        times = [r["elapsed_s"] for r in sel]
        out.append({
            "config": config, "budget": budget, "trials": len(sel),
            "hit_rate": sum(r["correct"] for r in sel) / len(sel),
            "time_mean_s": statistics.mean(times),
            "time_std_s": statistics.stdev(times) if len(times) > 1 else 0.0,
        })
    return out


def mcts_non_monotonic_cases(rows) -> list[tuple]:
    """(config, tactica, semilla, aciertos por presupuesto) donde un presupuesto mayor
    FALLA despues de que uno menor acerto: la curva media no garantiza mejora por semilla."""
    budgets = sorted({r["budget"] for r in rows})
    table = {}
    for r in rows:
        table.setdefault((r.get("config", ""), r["tactic"], r["seed"]), {})[r["budget"]] = r["correct"]
    cases = []
    for key, hits in sorted(table.items()):
        seq = [hits.get(b) for b in budgets]
        if any(a == 1 and b == 0 for a, b in zip(seq, seq[1:])):
            cases.append((key[0], key[1], key[2], seq))
    return cases


def mcts_rows_to_csv(rows, path: str) -> None:
    """Escribe las filas del benchmark en CSV (UTF-8, encabezado = claves de la fila)."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
