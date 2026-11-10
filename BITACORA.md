# Bitácora de decisiones — Taller 3 (ajedrez gráfico y agentes)

**Integrantes:** Santiago Guevara y Januar Mena · **Curso:** Inteligencia Artificial (UTP)

Registro de las decisiones de diseño, los errores cometidos y su corrección.
Formato de cada entrada: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores
reales llevan la marca **ERROR CORREGIDO** (*Qué pasó / Diagnóstico / Corrección / Lección*):
son el material de la conclusión individual que pide la sección 12.

Prefijos: `D-` decisiones generales; `E-` evaluación y agentes básicos; `S-` minimax,
alfa-beta y profundización; `M-` MCTS; `T-` ajuste de pesos (mejora); `G-` interfaz y
controlador; `I-` actividades de integración (torre, AND-OR, expectiminimax, Kriegspiel);
`X-` experimentos y torneo.

---

## Etapa 0 — Estructura, entorno y contrato

### D-01 · El entregable es el propio cuaderno del profesor, construido desde módulos probados
- **Decisión:** el código vive en el paquete `chess_ai/` (un módulo por responsabilidad, con
  pruebas en `tests/`) y `tools/construir_cuaderno.py` lo inserta en las celdas del enunciado,
  conservando todas sus secciones y su pseudocódigo.
- **Alternativas:** escribir todo en celdas; entregar un cuaderno delgado que solo importe el paquete.
- **Por qué:** el mismo esquema funcionó en el Taller 2: los módulos se prueban con `pytest`,
  se pueden desarrollar en paralelo, y el cuaderno sigue siendo autocontenido. Además la lista
  de entrega pide expresamente «módulos propios y README».
- **Consecuencia:** cada módulo solo importa de los anteriores en el orden
  `contract → environment → evaluation → agents_basic → search → mcts → tuning → controller → gui → tournament → experiments`.

### D-02 · Primer commit con el enunciado intacto
- El primer commit de la rama `taller-3` contiene el cuaderno exactamente como lo entregó el
  profesor. Separa en el historial lo del docente de lo propio y es la base idempotente del constructor.

### D-03 · Entorno virtual fuera de OneDrive, versiones fijadas
- `C:\Users\santi\venvs\ia-taller3` (misma razón que en los talleres 1 y 2: OneDrive sincronizaría
  miles de archivos del entorno). `requirements.txt` fija las versiones realmente probadas.

### D-04 · Mismo repositorio, rama independiente `taller-3`
- Repositorio `DjSantech/Taller_IA_UTP`: el Taller 1 está en `main`, el Taller 2 en `taller-2`.
  El Taller 3 va en su propia rama para no mezclar historiales. No se hace `push` sin orden explícita.

### D-05 · Identificadores en inglés, explicaciones en español
- El contrato suministrado ya usa nombres en inglés (`ChessEnvironment`, `SearchStats`,
  `Decision`…); se mantiene la convención del Taller 2.

### D-06 · Perspectiva única: E(s) desde blancas; `Decision.score` desde quien decide
- **Decisión:** la evaluación y las utilidades terminales «absolutas» son siempre desde blancas
  (positivo = bueno para blancas). Cada agente multiplica por `perspective_sign(color)` para
  obtener el valor del jugador que decide en la raíz, y así reporta `Decision.score`.
- **Alternativas:** evaluación relativa al jugador al turno (estilo negamax).
- **Por qué:** con una sola convención absoluta, minimax MAX/MIN se escribe tal como en AIMA
  y un error de signo se detecta con una prueba simple de antisimetría (reflejar el tablero
  invierte el signo). La pregunta 4 de la sustentación trata exactamente de este error.
- **Consecuencia:** la evaluación de negras «favorece a negras» porque, cuando negras deciden,
  se minimiza E (equivalente a maximizar −E).

### D-07 · Terminales antes que E, mates más cortos preferidos
- `MATE_SCORE = 100000`; una victoria a distancia `ply` vale `MATE_SCORE − ply`; tablas, 0.
  `E` se recorta a ±10000, así que cualquier mate domina a cualquier estimación.
- **Interacción con la caché (si se usa tabla de transposición):** el valor de mate depende de la
  distancia a la raíz; si alguna vez se guarda en una tabla hay que convertirlo a «distancia
  desde el nodo» al guardar y deshacer la conversión al leer.

### D-08 · Dos pruebas terminales: la de la partida y la de la búsqueda
- **Decisión:** la partida real usa `board.outcome(claim_draw=True)` (política del enunciado).
  Dentro de la búsqueda se usa `search_outcome`: sin jugadas legales (mate/ahogado), material
  insuficiente, `halfmove_clock ≥ 100` y `is_repetition(3)`.
- **Alternativas:** usar `claim_draw=True` en cada nodo.
- **Por qué:** `can_claim_threefold_repetition` prueba además cada jugada legal posible (empuja
  y deshace todas), lo que multiplica el costo de cada nodo. Esos reclamos «antes de mover»
  aparecen en el árbol como repetición triple del hijo correspondiente, así que el valor de la
  búsqueda no cambia. Se verifica en las pruebas que ambas políticas coinciden en mate y ahogado.
- **Consecuencia:** la clave de la historia importa: un FEN aislado no detecta la repetición
  (prueba `test_repetition_is_detected_from_history_not_from_fen`, pregunta 7).

### D-09 · «Truncada» no es tablas
- `ChessEnvironment.status()` devuelve `ongoing | terminal | truncated`. El límite de plies
  produce `truncated` con resultado oficial `*`, separado de las tablas reglamentarias.

### D-10 · Plazo cooperativo (`Deadline`), no interrupción
- La búsqueda pregunta por el plazo; nadie la detiene desde fuera. Si una búsqueda de
  profundidad fija se pasa, el controlador mide y registra `time_exceeded`; no puede
  interrumpir un agente bloqueado. El aislamiento en otro proceso queda fuera del alcance mínimo
  (sección 6 del enunciado) y se documenta como tal.

### D-11 · Evaluación común E = wm·M + wp·P + wk·K + wa·A
- M material (P=1, N=3.2, B=3.3, R=5, Q=9); P pasados (con bono por avance) − doblados − aislados;
  K (escudo de peones − casillas de la zona del rey atacadas) × fase, que se apaga en finales;
  A casillas atacadas por N, B, R, Q no ocupadas por piezas propias.
- Pesos iniciales `(100, 15, 10, 4)` centipeones por unidad. La tabla completa (escala, signo,
  costo y qué decisión induce cada término) está en el docstring de `chess_ai/evaluation.py`.
- **Por qué estos términos:** son baratos con bitboards y cada uno induce una decisión
  distinta (no regalar material, empujar pasados, enrocar, desarrollar). El vector de
  características `features()` se reutiliza para el ajuste de pesos por búsqueda local.
