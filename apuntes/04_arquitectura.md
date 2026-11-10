### Nuestra arquitectura (sección 4)

El código vive en el paquete `chess_ai/`, con un módulo por responsabilidad y pruebas `pytest` en `tests/`. Las celdas siguientes contienen **el mismo código** que esos módulos (el cuaderno se genera con `tools/construir_cuaderno.py`), así que el cuaderno es autocontenido y se ejecuta de arriba abajo. Las clases `SearchStats`, `Decision` y `Agent` son las de la celda anterior del enunciado, sin cambios.

| Componente del enunciado | Dónde está | Responsabilidad |
|---|---|---|
| `ChessEnvironment` | `chess_ai/environment.py` | Estado real, legalidad, `version`, deshacer, PGN, estado `ongoing/terminal/truncated` |
| `Agent` (seis) | `agents_basic.py`, `search.py`, `mcts.py` | Elegir una jugada sobre una copia y devolver `Decision` con métricas |
| `Evaluator` | `evaluation.py` | E(s) desde blancas, con 4 características y pesos |
| `SearchStats` | contrato del enunciado | Nodos, hojas, podas, profundidad completada, tiempo y simulaciones |
| `GameController` | `controller.py` | Alternancia, presupuesto, versión vigente, cancelación cooperativa, terminación, registro |
| `ChessApp` (vista) | `gui.py` | Controles, tablero SVG y mensajes; amplía la `ChessView` suministrada |
| `Tournament` | `tournament.py` | Emparejamientos, aperturas, semillas, CSV y PGN |
| Mejora | `tuning.py` | Ajuste de los pesos de E por búsqueda local (train/test separados) |
| Integración caps. 3–5 | `rook_problem.py`, `uncertainty.py` | Torre con BFS/DFS/UCS/A\*/voraz, AND-OR, expectiminimax |

**Flujo de una decisión.** Vista → `GameController.request_turn()` → copia con historia → `agent.choose(copia, time_limit_s, seed)` → `Decision` → el controlador comprueba plazo, legalidad y versión → `ChessEnvironment.apply(jugada)` → registro de métricas → la vista se actualiza.

**Convenciones que comparten todos los agentes** (bitácora D-06 a D-10):

- **Perspectiva:** E(s) y las utilidades terminales se expresan siempre desde **blancas**. Cada agente las convierte con `perspective_sign(color)`; `Decision.score` se reporta desde el jugador que decide.
- **Terminales:** se resuelven **antes** de consultar E. Un mate a `ply` jugadas vale ±(100000 − ply), lo que prefiere mates cortos, y E está acotada a ±10000, así que cualquier mate domina a cualquier estimación.
- **Plazo:** el plazo es **cooperativo** (`Deadline`): la búsqueda pregunta y, si vence, lanza `SearchTimeout`, que el agente captura para devolver la mejor jugada completa.
- **Aleatoriedad:** siempre con `random.Random(seed)` local; nunca el generador global.
