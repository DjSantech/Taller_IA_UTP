### Autoevaluación con la rúbrica (evidencia y huecos)

| Criterio | Puntos | Evidencia en este cuaderno y el repositorio | Huecos honestos |
|---|---:|---|---|
| Formulación, PEAS y arquitectura | 10 | §2 PEAS, estado con historia, clasificación e invariantes con su prueba; §4 tabla de módulos; contrato del enunciado sin cambios | — |
| Interfaz y reglas | 15 | §3 y §6: `ChessApp` con los tres modos, selector por color con los 6 agentes y Humano, Jugar turno / Iniciar-Pausar / Nueva / Deshacer (política explícita), profundidad, plazo y semilla, registro por turno, PGN y CSV; §8 reglas especiales (enroque, al paso, promoción, repetición, mate y ahogado) | La interacción es por listas, no por clic en casillas (mejora opcional). Pausar actúa entre turnos, no dentro de una búsqueda (documentado). |
| Seis agentes | 30 | §5 A–D: aleatorio, voraz, minimax, alfa-beta, alfa-beta mejorado (ordenación + profundización con plazo) y MCTS-UCT; §8 pruebas 1–7 | — |
| Integración caps. 3–4 | 10 | §7: torre con BFS/DFS/UCS, A\* y voraz con admisibilidad verificada exhaustivamente; búsqueda local de pesos; AND-OR, expectiminimax y Kriegspiel | — |
| Mejora adicional y ablación | 10 | Ajuste de pesos (§5 D y §7C, ablación por peso y en prueba); §9 Exp. 3: E0 contra E\* en partidas y ordenación sí/no | La mejora en la función objetivo es pequeña y no significativa (lo decimos); el resultado en partidas depende del Exp. 3. |
| Experimentos reproducibles | 15 | §9: Exp. 1 en vivo (valores y nodos idénticos a los guardados); torneo con aperturas y semillas comunes, colores intercambiados, CSV, PGN y JSON de configuración; Exp. 4 con 5 semillas y 4 presupuestos | MCTS y el mejorado con plazo de reloj no se repiten jugada a jugada en otra máquina (por diseño, lo decimos). |
| Informe y sustentación individual | 10 | §12 respuestas con evidencia y conclusiones individuales; guías de estudio personales | Se demuestra en la sustentación: cada integrante debe ejecutar una prueba nueva y modificar el código en vivo. |
