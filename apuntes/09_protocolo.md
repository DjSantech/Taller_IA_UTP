### Protocolo experimental: configuración y políticas

Todo lo pesado lo ejecutamos con `tools/correr_experimentos.py` (`--solo exp1|torneo|ablacion|mcts|profundidad|figuras`,
`--rapido` para una prueba de 11 s). El cuaderno **lee** los CSV de `resultados/` y no vuelve a jugar el torneo;
solo el Experimento 1 es lo bastante rápido (≈12 s) para repetirlo en vivo.

**Diseño previo con dos agentes.** Como pide el enunciado, primero jugamos una partida corta Minimax contra
Alfa-beta mejorado (Italiana, 40 plies, ambos colores): 10 s en total, sin excesos. Con eso estimamos la
duración y luego un piloto de 120 partidas (4 aperturas, 4 procesos) que tardó 135 s.

| Parámetro | Valor | Justificación |
|---|---|---|
| Agentes | los 6 del registro | Aleatorio, Voraz, Minimax d=2, Alfa-beta natural d=2, Alfa-beta mejorado (plazo), MCTS (plazo) |
| Presupuesto | 0.2 s por decisión, tolerancia 0.05 s | Minimax d=2 tarda 0.05–0.16 s; el mejorado completa 2–3 plies; MCTS hace ~300–600 simulaciones |
| Aperturas | 8 líneas teóricas (A1–A8), las mismas para todos los pares | Italiana, GD rehusado, Najdorf, Inglesa, Española, Francesa, Caro-Kann, Eslava; E0 entre −28 y +24 cp |
| Colores | cada apertura con ambos colores | 15 pares × 8 × 2 = **240 partidas** (mínimo 60) |
| Límite | 160 plies de los agentes, sin contar la apertura | al llegar: «truncada», resultado `*`, fuera de los puntos |
| Semillas | partida k: 1000·k; jugada: base + ply | todas distintas; en el CSV, el PGN y `torneo_config.json` |
| Excesos | tiempo real > 0.25 s → `time_exceeded = 1`; la jugada se aplica igual | política uniforme; no se inventan derrotas por tiempo |
| Tablas | reclamo automático (`claim_draw=True`) | convención de la sección 2 |
| Procesos | 1 (en serie) | con 4 procesos MCTS perdía 18 % de simulaciones (477 → 391) y el mejorado 0.11 plies |
| Puntos | 1 / 0.5 / 0 solo en terminadas | nunca se adjudica por evaluación estática |

Archivos: `torneo_decisiones.csv` (una fila por jugada, columnas exactas `CSV_FIELDS`), `torneo_partidas.csv`
(una fila por partida), `torneo.pgn` (encabezados de agentes, apertura, semilla, presupuesto; cada jugada con
`[%emt]` y profundidad o simulaciones), `torneo_config.json` (agentes y parámetros, políticas, semillas, versiones,
hardware, fecha y duración). La ablación usa los mismos formatos con el prefijo `exp3_ablacion`.

**Reproducibilidad.** Las semillas reproducen exactamente a Aleatorio, Voraz, Minimax y Alfa-beta. El mejorado y
MCTS dependen del reloj (profundidad completada y número de simulaciones), así que la misma semilla puede dar otra
partida en otra máquina: es la consecuencia esperada de comparar fuerza con presupuesto temporal. Para
reproducibilidad exacta de MCTS usamos simulaciones fijas en el Experimento 4.
