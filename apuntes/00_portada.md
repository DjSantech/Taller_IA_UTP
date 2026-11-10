## Cuaderno completado · Taller 3 de Inteligencia Artificial (UTP)

**Integrantes:** Santiago Guevara y Januar Mena (en pareja, la modalidad propuesta).

Este es el enunciado del docente **completado**. Conservamos todas sus celdas, tablas y pseudocódigo tal como vienen en el primer commit del repositorio. Debajo de cada sección agregamos nuestro código, pruebas, mediciones y explicaciones.

### Mapa del cuaderno

| Sección del enunciado | Qué agregamos |
|---|---|
| 1. Requisitos | Versiones reales del entorno comparadas con `requirements.txt` |
| 2. Análisis | PEAS, estado, clasificación del entorno, invariantes y política de tablas |
| 3. Base gráfica | Diseño de la interfaz `ChessApp` (tres modos, Deshacer, bucle cooperativo) |
| 4. Arquitectura | Módulos y su responsabilidad; `ChessEnvironment` |
| 5. Agentes | Evaluación E(s); A aleatorio y voraz; B minimax y alfa-beta; C profundización con plazo; D MCTS-UCT, mejora (ajuste de pesos) y registro de agentes |
| 6. Controlador | `GameController`, `ChessApp` y la aplicación con los seis agentes y Humano |
| 7. Integración | Torre (BFS, DFS, UCS, A\*, voraz), ajuste local de pesos, AND-OR, expectiminimax y Kriegspiel |
| 8. Pruebas | Las 7 pruebas pedidas, ejecutadas aquí con `assert`, posiciones propias y fallos corregidos |
| 9. Experimentos | Exp. 1 en vivo; torneo, ablación y MCTS desde los resultados guardados en `resultados/` |
| 11–12 | Autoevaluación con la rúbrica, respuestas de sustentación, conclusiones individuales y lista de entrega |

### Cómo está construido y cómo reproducirlo

El código vive en el paquete `chess_ai/`, con pruebas `pytest` en `tests/`. `tools/construir_cuaderno.py` inserta ese mismo código en las celdas (sin los imports internos), así que el cuaderno es autocontenido: se ejecuta de arriba abajo con un kernel nuevo (`tools/ejecutar_cuaderno.py`), desde la raíz del proyecto. Las tablas y figuras salen de ejecuciones reales: las rápidas se repiten aquí y las largas (torneo, ablación, benchmark de MCTS) se cargan de `resultados/`, donde las escribió `tools/correr_experimentos.py` con el mismo código. Cada decisión y cada error corregido están en `BITACORA.md`. El README explica la instalación.

### Fuentes y ayudas utilizadas (declaración)

- **python-chess** (reglas, jugadas legales, FEN, PGN y SVG). No decide jugadas: no usamos Stockfish ni ningún motor UCI.
- **ipywidgets** (interfaz), **matplotlib** (gráficas), **numpy** (ajuste de pesos), **nbformat/nbclient** (construir y ejecutar el cuaderno) y **pytest**.
- Russell y Norvig, *AIMA* 4.ª ed., caps. 2–5: pseudocódigo de minimax, alfa-beta, MCTS, AND-OR y expectiminimax. Kocsis y Szepesvári (2006) para la constante de UCT. La idea del ajuste estilo «Texel» es de conocimiento común en programación de ajedrez; la implementación es nuestra.
- **Asistente de IA:** usamos **Claude** (Anthropic), mediante **Claude Code**, para programar los módulos, escribir pruebas, correr experimentos y redactar estos apuntes, repartiendo el trabajo por módulo. Revisamos los resultados y preparamos guías de estudio para poder explicar, probar y modificar cualquier parte en la sustentación.
- Reutilizamos ideas y convenciones de nuestros talleres 1 y 2 (búsquedas no informadas, A\*, búsqueda local), citadas en la bitácora.
