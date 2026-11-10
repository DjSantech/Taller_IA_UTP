# ===== Aplicacion grafica: selector con los seis agentes y Humano para cada color =====
# Cambie los selectores Blancas/Negras para elegir el modo (humano-humano, humano-agente o
# agente-agente). "Nueva partida" reinicia; "Iniciar/Pausar" juega seguido entre agentes.
app = ChessApp(AGENT_FACTORIES, white=HUMAN_LABEL, black="Alfa-beta mejorado",
               config=AgentConfig(depth=2, time_limit_s=0.2, seed=0, simulations=None),
               max_plies=160, auto_reply=False)
print("Agentes en el selector:", ", ".join(app.white_select.options))

# Dos turnos jugados por programa con los mismos metodos que llaman los botones, para que la
# salida guardada muestre un tablero con jugadas: Mover (humano e2-e4) y "Jugar turno del agente".
app.origin.value, app.target.value = "e2", "e4"
_r_humano = app.on_move()
_r_agente = app.on_agent_turn()
_rec = app.controller.records[-1]
print(f"Humano: {_r_humano.status}; agente: {_r_agente.status}. Historial SAN: "
      f"{' '.join(app.env.san_history())}")
print(f"Decision de {_rec.black_agent}: {_rec.move_uci}, nodos={_rec.nodes}, podas={_rec.cutoffs}, "
      f"profundidad completada={_rec.completed_depth}, tiempo={_rec.elapsed_s:.3f} s, "
      f"excedio plazo={_rec.time_exceeded}")
assert app.controller.mode() == "humano-agente" and len(app.env.board.move_stack) == 2
app.display()
