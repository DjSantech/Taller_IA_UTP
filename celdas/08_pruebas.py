# ===== PRUEBAS DE NUESTROS AGENTES (las 7 de la celda anterior), ejecutadas aqui con asserts =====
# Las pruebas de comportamiento usan time_limit_s=0 (sin plazo) o simulaciones fijas, para que
# el resultado NO dependa de la velocidad de la maquina; las de plazo solo afirman invariantes.
import time as _time

_INTERMEDIAS = {
    "piezas_menores": "r3k3/ppp2ppp/2n5/3p4/3P4/2N5/PPP2PPP/R3K3 w Qq - 0 1",
    "captura_caballo": "4k3/pp3ppp/2n5/3p4/3N4/8/PP3PPP/4K3 w - - 0 1",
    "negras_en_jaque": "r3k3/ppp2ppp/8/1B6/8/8/PPP2PPP/4K2R b K - 0 1",
    "final_torres": "8/5k2/8/3R4/8/2K5/5r2/8 w - - 0 1",
    "final_peones": "8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1",
}
_NO_TERMINALES = {k: POSITIONS[k] for k in ("initial", "castling", "promotion", "en_passant",
                                            "mate_in_one")}
_EVASION = "k3r3/8/8/7Q/8/8/8/4K3 w - - 0 1"      # blancas en jaque por la torre e8


def _seis_agentes():
    """Los seis agentes, configurados para pruebas reproducibles (sin plazo de reloj)."""
    return [RandomAgent(), GreedyAgent(), MinimaxAgent(depth=2), AlphaBetaAgent(depth=2),
            AlphaBetaImprovedAgent(max_depth=2), MCTSAgent(simulations=200)]


def _foto(board):
    return board.fen(), list(board.move_stack)


def _con_historia():
    board = chess.Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]:
        board.push_uci(uci)
    return board


def _valor_tras(board, move, depth):
    """Valor minimax desde blancas de jugar `move` y buscar depth-1 plies (mate medido desde la raiz)."""
    ctx = SearchContext(DEFAULT_EVALUATOR)
    board.push(move)
    try:
        return _search_minimax(board, depth - 1, 1, ctx)
    finally:
        board.pop()


_resultados_pruebas = []


def _registrar(numero, nombre, casos, detalle):
    _resultados_pruebas.append((numero, nombre, casos, detalle))


# --- 1. Minimax frente a alfa-beta (natural y ordenado) a igual profundidad y evaluacion
_casos, _difieren, _ahorro = 0, 0, []
for _nombre, _fen in {**_NO_TERMINALES, **_INTERMEDIAS}.items():
    for _prof in ((1, 2, 3) if _nombre in ("promotion", "en_passant", "mate_in_one", "final_torres",
                                            "final_peones") else (1, 2)):
        _b = chess.Board(_fen)
        _mm = search_root(_b, "minimax", _prof)
        for _orden in (False, True):
            _ab = search_root(_b, "alphabeta", _prof, ordering=_orden)
            assert _ab.value == _mm.value, (_nombre, _prof, _orden)       # igualdad exacta
            assert _ab.stats.nodes <= _mm.stats.nodes
            if _ab.move != _mm.move:        # empate: la jugada de alfa-beta alcanza el mismo valor
                _difieren += 1
                assert _valor_tras(_b, _ab.move, _prof) == _valor_tras(_b, _mm.move, _prof)
            _ahorro.append(1 - _ab.stats.nodes / _mm.stats.nodes)
            _casos += 1
_registrar(1, "minimax = alfa-beta en valor", _casos,
           f"valor identico (==) en {_casos} comparaciones (prof. 1-3); jugadas distintas por empate: "
           f"{_difieren}; ahorro medio de nodos {100 * sum(_ahorro) / len(_ahorro):.0f} %")

# --- 2. Decisiones legales de los seis agentes en posiciones no terminales (y terminales sin jugada)
_casos = 0
for _nombre, _fen in {**_NO_TERMINALES, "piezas_menores": _INTERMEDIAS["piezas_menores"],
                      "negras_en_jaque": _INTERMEDIAS["negras_en_jaque"]}.items():
    for _ag in _seis_agentes():
        _b = chess.Board(_fen)
        _d = _ag.choose(_b, time_limit_s=0, seed=7)
        assert _d.move in _b.legal_moves, (_ag.name, _nombre)
        _casos += 1
for _nombre, _esperado in (("checkmate", -MATE_SCORE), ("stalemate", 0.0)):
    for _ag in _seis_agentes():
        _d = _ag.choose(chess.Board(POSITIONS[_nombre]), time_limit_s=0, seed=0)
        assert _d.move is None and _d.score == _esperado, (_ag.name, _nombre, _d.score)
        _casos += 1
_registrar(2, "jugadas legales de los 6 agentes", _casos,
           "jugada legal en 7 posiciones x 6 agentes; en mate y ahogado: move=None con utilidad "
           "-100000 (derrota de negras) y 0")

# --- 3. Victoria inmediata y evasion de jaque (tambien con negras al turno)
_casos = 0
for _ag in _seis_agentes()[1:]:                          # el aleatorio no busca: no se le exige
    for _b in (chess.Board(POSITIONS["mate_in_one"]), chess.Board(POSITIONS["mate_in_one"]).mirror()):
        _d = _ag.choose(_b, time_limit_s=0, seed=0)
        _b.push(_d.move)
        assert _b.is_checkmate(), _ag.name
        _casos += 1
for _ag in _seis_agentes():
    _b = chess.Board(_EVASION)
    _d = _ag.choose(_b, time_limit_s=0, seed=0)
    _b.push(_d.move)
    assert not _b.was_into_check()                       # evasion legal
    if _ag.name not in ("Aleatorio", "MCTS"):
        assert _d.move == chess.Move.from_uci("h5e8"), _ag.name   # la mejor: capturar la torre
    _casos += 1
_registrar(3, "victoria inmediata y evasion", _casos,
           "5 agentes que evaluan dan mate en uno con blancas y con negras (tablero reflejado); "
           "todos evaden el jaque y los de busqueda capturan la torre que lo da (Dxe8+)")

# --- 4. Tablero e historia intactos tras busqueda normal e interrumpida
_casos = 0
for _ag in _seis_agentes():
    _b = _con_historia()
    _antes = _foto(_b)
    _ag.choose(_b, time_limit_s=0, seed=1)
    assert _foto(_b) == _antes, _ag.name
    _casos += 1
_b = _con_historia(); _antes = _foto(_b)
for _fn in (lambda ctx: _search_minimax(_b, 4, 0, ctx),
            lambda ctx: _search_alphabeta(_b, 4, 0, -float("inf"), float("inf"), ctx)):
    _ctx = SearchContext(DEFAULT_EVALUATOR, deadline=Deadline(0.02))
    try:
        _fn(_ctx)
        raise AssertionError("se esperaba SearchTimeout")
    except SearchTimeout:
        pass
    assert _ctx.stats.nodes > 1 and _foto(_b) == _antes   # cortada a mitad del arbol
    _casos += 1
for _ag, _plazo in ((AlphaBetaImprovedAgent(max_depth=10), 0.05), (MCTSAgent(simulations=None), 0.03),
                    (GreedyAgent(), 1e-9)):
    _d = _ag.choose(_b, time_limit_s=_plazo, seed=0)
    assert _foto(_b) == _antes and _d.move in _b.legal_moves, _ag.name
    _casos += 1
_n = {"n": 0}


def _evaluador_roto(board):
    _n["n"] += 1
    if _n["n"] > 50:
        raise RuntimeError("fallo simulado de la evaluacion")
    return DEFAULT_EVALUATOR(board)


for _ag in (AlphaBetaAgent(depth=3, evaluator=_evaluador_roto), MCTSAgent(simulations=200, evaluator=_evaluador_roto)):
    _n["n"] = 0
    try:
        _ag.choose(_b, time_limit_s=0, seed=0)
        raise AssertionError("se esperaba RuntimeError")
    except RuntimeError:
        pass
    assert _foto(_b) == _antes, _ag.name
    _casos += 1
_registrar(4, "tablero e historia intactos", _casos,
           "FEN y pila iguales tras buscar (6 agentes), tras SearchTimeout a mitad del arbol "
           "(minimax y alfa-beta), con plazo vencido (mejorado, MCTS, voraz) y si E lanza una excepcion")

# --- 5. Reproducibilidad: misma semilla / mismas simulaciones -> mismo resultado
_casos = 0
for _ag_cls in (RandomAgent, GreedyAgent):
    for _fen in (POSITIONS["initial"], _INTERMEDIAS["piezas_menores"]):
        _m = {_ag_cls().choose(chess.Board(_fen), time_limit_s=0, seed=11).move for _ in range(3)}
        assert len(_m) == 1
        _casos += 1
_a1, _a2, _a3 = MCTSAgent(simulations=150), MCTSAgent(simulations=150), MCTSAgent(simulations=150)
_d1 = _a1.choose(chess.Board(), time_limit_s=0, seed=5)
_d2 = _a2.choose(chess.Board(), time_limit_s=0, seed=5)
_a3.choose(chess.Board(), time_limit_s=0, seed=6)
assert _d1.move == _d2.move and _a1.last_info["root_visits"] == _a2.last_info["root_visits"]
assert _a1.last_info["root_visits"] != _a3.last_info["root_visits"]     # otra semilla, otro arbol
_casos += 2
_partidas = []
for _ in range(2):        # partida completa (20 plies) con el controlador: misma semilla base
    _cfg = AgentConfig(depth=1, time_limit_s=0, seed=3, simulations=30)
    _ctl = GameController(ChessEnvironment(max_plies=20), make_agent("Voraz", _cfg),
                          make_agent("MCTS", _cfg), _cfg)
    _ctl.play_until_stop()
    _partidas.append([r.move_uci for r in _ctl.records])
assert _partidas[0] == _partidas[1] and len(_partidas[0]) == 20
_casos += 1
_registrar(5, "reproducibilidad por semilla", _casos,
           "aleatorio y voraz: misma jugada con la misma semilla; MCTS con 150 simulaciones: mismas "
           "visitas en la raiz (otra semilla, otras visitas); partida Voraz-MCTS de 20 plies identica")

# --- 6. Profundizacion iterativa: jugada legal al agotarse el presupuesto
_casos = 0
for _fen in (POSITIONS["initial"], _INTERMEDIAS["piezas_menores"], _INTERMEDIAS["negras_en_jaque"]):
    _b = chess.Board(_fen)
    _d = AlphaBetaImprovedAgent().choose(_b, time_limit_s=1e-9, seed=0)
    assert _d.move in _b.legal_moves and _d.stats.completed_depth == 0 and _d.score is None
    _ag = AlphaBetaImprovedAgent(max_depth=10)
    _d = _ag.choose(_b, time_limit_s=0.1, seed=0)
    _hechas = [it for it in _ag.last_iterations if it["completed"]]
    assert _d.move in _b.legal_moves and _d.stats.completed_depth == len(_hechas) >= 1
    assert _d.move.uci() == _hechas[-1]["move"]          # la de la ULTIMA iteracion completa
    assert _d.score == search_root(_b, "alphabeta", _d.stats.completed_depth).value
    assert sum(it["nodes"] for it in _ag.last_iterations) == _d.stats.nodes
    _casos += 2
_registrar(6, "profundizacion con plazo agotado", _casos,
           "plazo 1e-9 s: jugada de respaldo legal, score None, completed_depth 0; plazo 0.1 s: "
           "jugada y valor de la ultima iteracion completa (= alfa-beta a esa profundidad)")


# --- 7. MCTS elige para el rival sin maximizar accidentalmente al jugador raiz
class _MCTSPerspectivaBlancas(MCTSAgent):
    """Variante con el ERROR de la pregunta 6: todo W desde blancas (negras maximizan para blancas)."""

    def _reward_for(self, mover, reward_white):
        return reward_white


_tac = {t["id"]: t for t in MCTS_TACTICS}
_casos = 0
for _id in ("T3_mate1_b_backrank", "T6_queen_b"):              # negras al turno
    for _semilla in range(3):
        _bien = MCTSAgent(simulations=300).choose(chess.Board(_tac[_id]["fen"]), time_limit_s=0,
                                                  seed=_semilla)
        _mal = _MCTSPerspectivaBlancas(simulations=300).choose(chess.Board(_tac[_id]["fen"]),
                                                              time_limit_s=0, seed=_semilla)
        assert _bien.move.uci() in _tac[_id]["solutions"] and _mal.move.uci() not in _tac[_id]["solutions"]
        _casos += 1
_ag = MCTSAgent(simulations=300)
_ag.choose(chess.Board(_tac["T3_mate1_b_backrank"]["fen"]), time_limit_s=0, seed=0)
_pila = [(_ag.last_root, chess.Board(_tac["T3_mate1_b_backrank"]["fen"]))]
_nodos_revisados = 0
while _pila:                                       # cada hijo "pertenece" a quien mueve en el padre
    _nodo, _bb = _pila.pop()
    for _hijo in _nodo.children:
        assert _hijo.mover == _bb.turn
        _nb = _bb.copy(stack=False); _nb.push(_hijo.move)
        _pila.append((_hijo, _nb)); _nodos_revisados += 1
_registrar(7, "perspectiva de MCTS", _casos + 1,
           f"negras al turno (T3 mate Ta1#, T6 dama colgada), 3 semillas: el agente acierta y la variante "
           f"'todo desde blancas' falla siempre; {_nodos_revisados} nodos del arbol con dueno correcto")

# --- Posiciones propias (seccion 8): reglas especiales y comportamiento de los agentes
_PROPIAS = {
    "ep_clavada": "8/8/8/K2pP2r/8/8/8/7k w - d6 0 2",
    "enroque_atacado": "4k3/8/8/8/8/8/6b1/R3K2R w KQ - 0 1",
    "mate_en_dos": "k7/8/2K5/8/8/8/8/7R w - - 0 1",
    "pieza_envenenada": "6k1/pp3ppp/4p3/3n4/8/8/PP3PPP/3Q2K1 w - - 0 1",
}
for _fen in _PROPIAS.values():
    assert chess.Board(_fen).is_valid()
_b = chess.Board(_PROPIAS["ep_clavada"])
assert _b.has_legal_en_passant() is False and chess.Move.from_uci("e5d6") not in _b.legal_moves
assert chess.Move.from_uci("e5e6") in _b.legal_moves
_b = chess.Board(_PROPIAS["enroque_atacado"])
assert chess.Move.from_uci("e1g1") not in _b.legal_moves and chess.Move.from_uci("e1c1") in _b.legal_moves
_b = chess.Board(_PROPIAS["mate_en_dos"])
assert search_root(_b, "minimax", 2).value < MATE_SCORE - 1000
assert search_root(_b, "alphabeta", 3).value == MATE_SCORE - 3 == search_root(_b, "minimax", 3).value
_b = chess.Board(_PROPIAS["pieza_envenenada"])
assert GreedyAgent().choose(_b, time_limit_s=0, seed=0).move == chess.Move.from_uci("d1d5")
assert MinimaxAgent(depth=2).choose(_b, time_limit_s=0, seed=0).move != chess.Move.from_uci("d1d5")
_registrar("8", "posiciones propias", 4,
           "captura al paso ilegal por clavada; enroque corto prohibido por casilla atacada; mate en dos "
           "(prof. 3 = 100000-3, prof. 2 no lo ve); pieza envenenada (el voraz la toma, minimax-2 no)")

print(f"{'#':>2}  {'prueba':<34}{'casos':>6}  resultado  detalle")
for _num, _nom, _cas, _det in _resultados_pruebas:
    print(f"{_num:>2}  {_nom:<34}{_cas:>6}  PASA       {_det}")
print(f"\nTodas las afirmaciones se verificaron con assert ({len(_resultados_pruebas)} grupos, "
      f"{sum(r[2] for r in _resultados_pruebas)} casos).")
