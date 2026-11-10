# ===== 7.D: plan AND-OR en SAN, expectiminimax frente a minimax y estado de creencia de Kriegspiel =====
print("D1. Mate forzado como busqueda AND-OR (plan condicional verificado con las reglas)")
for _nombre, _fen in MATE_POSITIONS.items():
    _b = chess.Board(_fen)
    _st = AndOrStats()
    _plan = and_or_mate_search(_b, 2, _st)
    _ver = verify_mate_plan(_b, _plan) if _plan else {"ok": False, "leaves": 0}
    _sin_n1 = and_or_mate_search(_b, 1) is None
    assert _plan is not None and _ver["ok"]
    print(f"\n{_nombre}  {_fen}")
    print(f"  plan verificado: {_ver['ok']}; jugadas del atacante: {_ver['max_attacker_moves']}; "
          f"hojas (mates): {_ver['leaves']}; nodos OR/AND: {_st.or_nodes}/{_st.and_nodes}; "
          f"sin plan de 1 jugada: {_sin_n1}")
    print(format_mate_plan(_b, _plan, indent="  "))

# Un plan que no cubre todas las defensas se rechaza.
_b = chess.Board(MATE_POSITIONS["mate_en_2_dama"])
_lineal = {chess.Move.from_uci("e7f6"): {chess.Move.from_uci("h6h7"): {chess.Move.from_uci("g2g7"): {}}}}
print("\nSecuencia lineal 1.Kf6 Kh7 2.Qg7# como si fuera plan:", verify_mate_plan(_b, _lineal))

print("\nD2. Arbol con azar (separado del ajedrez): expectiminimax frente a minimax")
for _titulo, _arbol in (("segura / arriesgada (p = 0.75 / 0.25, utilidad en [-10, 10])",
                         chance_tree_safe_vs_risky()),
                        ("escala original (p = 0.9 / 0.1)", chance_tree_scale()),
                        ("misma escala transformada u -> 4^u",
                         transform_utilities(chance_tree_scale(), chance_scale_transform))):
    _ex, _vex = chance_root_decision(_arbol, expectiminimax)
    _mm, _vmm = chance_root_decision(_arbol, worst_case_minimax)
    print(f"  {_titulo}:")
    print(f"     expectiminimax {{{', '.join(f'{k}: {v:g}' for k, v in _vex.items())}}} -> {_ex}")
    print(f"     minimax (azar = adversario) {{{', '.join(f'{k}: {v:g}' for k, v in _vmm.items())}}} -> {_mm}")

print("\nD3. Kriegspiel: crecimiento del estado de creencia de blancas (arbitro: sin captura, sin jaque)")
for _fila in kriegspiel_belief_demo():
    print(f"  {_fila['paso']:<38} mundos posibles: {_fila['mundos_posibles']}")
_b = chess.Board()
_b.push_uci("e2e4")
_creencia = belief_after_hidden_move({_b.epd(): _b})
_legal, _ilegal = belief_after_own_try(_creencia, "e4e5")
print(f"  Tras 1.e4 y la respuesta oculta, intentar e4-e5: 'ilegal' en {len(_ilegal)} mundo(s) y "
      f"'legal' en {len(_legal)}; un intento fallido deja un solo tablero posible.")
