## Interfaz gráfica: `ChessApp`

Ampliamos la base suministrada `ChessView` en una clase nueva, `ChessApp` (`chess_ai/gui.py`).
No heredamos de `ChessView` para que el paquete funcione también fuera del cuaderno, pero
conservamos su forma de jugar: listas de origen, destino y promoción, botón **Mover**, destinos
posibles de la casilla elegida y tablero SVG con el último movimiento y el jaque resaltados.
Toda la lógica de turnos está en `GameController` (sección 6); la vista solo llama a sus métodos.

### Cómo usarla

```python
app = ChessApp({"Humano": None,
                "Aleatorio": lambda cfg: RandomAgent(),
                "Alfa-beta": lambda cfg: AlphaBetaAgent(depth=cfg.depth, ordering=True),
                "MCTS": lambda cfg: MCTSAgent(simulations=cfg.simulations)},
               white="Humano", black="Alfa-beta", max_plies=160)
app.display()
```

| Zona | Controles |
|---|---|
| Tablero | SVG con último movimiento, rey en jaque, destinos posibles de la casilla de origen (azul) y, opcionalmente, una flecha con la jugada elegida por el agente. «Ver desde negras» gira el tablero. |
| Jugada humana | Origen, Destino, Promoción y **Mover**. Debajo se listan los destinos legales de la casilla de origen. |
| Partida | **Jugar turno del agente**, **Iniciar/Pausar**, **Nueva partida**, **Deshacer**, **Actualizar vista**, campo FEN (vacío = posición inicial), **Exportar PGN**, **Exportar CSV**. |
| Jugadores y presupuesto | Selector de agente para blancas y para negras (incluye «Humano»), profundidad, plazo en segundos, semilla base, simulaciones MCTS (0 = usar el plazo), máximo de plies (0 = sin límite), pausa entre turnos del bucle y «El agente responde solo». |
| Estado | Modo, turno y de quién es, jaque, último movimiento, estado (en curso / terminal / truncada), resultado oficial, terminación, plies, búsqueda activa y bucle. |
| Historial y registro | Historial SAN numerado y una tabla con cada decisión: ply, color, agente, jugada, valor, nodos, hojas, podas, profundidad completada, tiempo, simulaciones, semilla y si excedió el plazo. |

Las exportaciones se guardan en `resultados/interfaz/<id de partida>.pgn|csv` y además se
muestran en el cuadro de texto inferior. El PGN lleva en los encabezados los agentes, la semilla
base, la política de semillas, el plazo, la tolerancia, la profundidad y las simulaciones. El CSV
tiene exactamente las columnas `CSV_FIELDS` del enunciado.

### Los tres modos

El modo sale de los dos selectores; no hay un selector de modo aparte.

- **Humano contra humano:** ambos selectores en «Humano». Cada jugada se hace con **Mover**.
- **Humano contra agente:** un selector en «Humano» y el otro en un agente. Si «El agente
  responde solo» está activo, tras cada jugada humana válida el agente responde automáticamente
  (con el mismo bucle cooperativo, que se detiene al volver el turno humano). Si está desactivado,
  el agente juega al pulsar **Jugar turno del agente**, útil para mostrar decisiones paso a paso.
  Si el agente lleva blancas, se pulsa **Jugar turno del agente** o **Iniciar** para la primera jugada.
- **Agente contra agente:** ambos selectores en agentes. **Jugar turno del agente** juega un
  solo ply; **Iniciar** juega seguido hasta pausar, terminar o llegar al límite de plies.

El turno se respeta siempre: en el turno de un agente, **Mover** se rechaza, y en un turno humano
**Jugar turno del agente** solo informa que le toca a un humano. Toda jugada humana pasa por
`ChessEnvironment.apply`, que valida la legalidad; una jugada ilegal no cambia el tablero.

### Política de Deshacer

- **Humano contra agente:** deshace hasta devolver el turno al humano. Si el agente ya
  respondió, se deshace la pareja de turnos (respuesta del agente y jugada humana); si el agente
  todavía no había respondido, solo la jugada humana. Así el humano puede corregir su jugada;
  deshacer un solo ply dejaría el turno al agente, que respondería lo mismo.
- **Humano contra humano y agente contra agente:** un ply.
- **Prohibido con una búsqueda activa o con el bucle en marcha:** hay que pausar primero. Esto
  cumple la regla de no alterar el estado mientras una búsqueda está activa sin cancelarla.

### El bucle cooperativo y sus límites

**Iniciar** lanza una tarea `asyncio` en el bucle de eventos del kernel (`run_async`). Cada
vuelta juega un turno, redibuja y cede el control con `await asyncio.sleep(pausa)`. En esa cesión
el kernel procesa los clics pendientes: si se pulsó **Pausar**, el bucle se detiene antes del
siguiente turno. También se detiene si la partida termina, si llega al máximo de plies (estado
**truncada**, resultado `*`), si le toca a un humano o si un agente devuelve algo inválido.

Limitaciones que declaramos:

1. **Un turno individual es síncrono.** Mientras un agente busca (aproximadamente el plazo
   configurado), el kernel está ocupado y no atiende clics; **Pausar** surte efecto al terminar
   ese turno. Con plazos de décimas de segundo la interfaz responde bien; con profundidad fija
   alta un turno puede tardar mucho más.
2. **La cancelación es cooperativa entre turnos**, no dentro de la búsqueda. Dentro de la
   búsqueda, el plazo también es cooperativo (`Deadline`): el agente pregunta y devuelve su
   mejor jugada completa.
3. **El controlador mide después de que el agente devuelve.** Si un agente excede el plazo, se
   registra `time_exceeded` y la jugada se aplica (política uniforme), pero no se puede
   interrumpir a un agente bloqueado. Para eso haría falta aislar al agente en otro proceso, que
   queda fuera del alcance mínimo (sección 6).

### Prueba manual del enunciado

1. Con ambos jugadores en «Humano»: Origen `e2`, Destino `e4`, **Mover**; luego `e7`→`e5` y
   `g1`→`f3`. El historial muestra `1. e4 e5 2. Nf3` y el turno es de negras.
2. **Mover pieza fuera de turno:** con turno de negras, Origen `d2`, Destino `d4`, **Mover**.
   Aparece «Movimiento ilegal… El tablero conserva su estado»; el tablero, el turno y el
   historial no cambian. La lista de destinos ya lo anticipaba: «Sin jugadas legales desde d2».
3. **Promoción cargando una posición:** escribimos en FEN `7k/P7/8/8/8/8/8/7K w - - 0 1` y
   pulsamos **Nueva partida**. Elegimos Origen `a7`, Destino `a8`, Promoción «Caballo» y
   **Mover**: aparece un caballo blanco en a8 (`a8=N`). **Actualizar vista** redibuja sin cambiar
   el estado.

Estas mismas comprobaciones están automatizadas en `tests/test_controller.py`
(`test_human_human_mode_plays_statement_manual_test`, `test_promotion_from_loaded_position`,
`test_gui_smoke_human_moves_and_agent_button`, `test_gui_promotion_and_new_game_from_fen`).
