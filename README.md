# Taller 3: Ajedrez gráfico y agentes inteligentes

**Curso:** Inteligencia Artificial (UTP) · **Referencia:** Russell y Norvig, *AIMA* 4.ª ed., caps. 2–5
**Modalidad:** en pareja · **Integrantes:** Santiago Guevara y Januar Mena

Aplicación de ajedrez en Jupyter (humano contra humano, humano contra agente y agente contra agente) con seis agentes propios: aleatorio, voraz de un ply, minimax, alfa-beta, alfa-beta mejorado (ordenación y profundización iterativa con plazo) y MCTS-UCT. La mejora adicional es el ajuste de pesos de la evaluación por búsqueda local, con ablación. Se incluyen las actividades de integración (torre con BFS/DFS/UCS/A\*/voraz, AND-OR, expectiminimax y Kriegspiel) y cuatro experimentos reproducibles.

El entregable es [`Taller_Ajedrez_Grafico_Agentes_IA.ipynb`](Taller_Ajedrez_Grafico_Agentes_IA.ipynb): el enunciado del docente completado. El primer commit de la rama `taller-3` tiene el enunciado intacto; el cuaderno conserva todas sus celdas y agrega debajo nuestro código, pruebas, resultados y explicaciones.

## Estructura

| Ruta | Contenido |
|---|---|
| `Taller_Ajedrez_Grafico_Agentes_IA.ipynb` | Cuaderno entregable, generado por `tools/construir_cuaderno.py` y ejecutado |
| `chess_ai/` | Código fuente, un módulo por responsabilidad (fuente de verdad del cuaderno) |
| `tests/` | Pruebas `pytest` de todos los módulos |
| `celdas/` | Celdas de código propias del cuaderno (demostraciones, pruebas, carga de resultados) |
| `apuntes/` | Textos que se insertan en el cuaderno y bitácoras por etapa |
| `BITACORA.md` | Decisiones de diseño y errores corregidos (generada con `tools/unir_bitacora.py`) |
| `resultados/` | CSV, PGN, JSON y figuras de las corridas reales |
| `tools/` | Construir y ejecutar el cuaderno, correr los experimentos, unir la bitácora |
| `requirements.txt` | Versiones exactas del entorno probado |

## Instalación

```bash
# El entorno virtual se crea FUERA de la carpeta sincronizada por OneDrive.
python -m venv C:\Users\<usuario>\venvs\ia-taller3
C:\Users\<usuario>\venvs\ia-taller3\Scripts\activate
pip install -r requirements.txt
python -m ipykernel install --user --name ia-taller3 --display-name "Python (ia-taller3)"
```

## Uso (desde la raíz del proyecto, con el entorno activado)

```bash
python -m pytest tests -q -p no:cacheprovider   # pruebas de los módulos
python tools/construir_cuaderno.py               # regenera el cuaderno desde el enunciado y los módulos
python tools/ejecutar_cuaderno.py                # lo ejecuta en un kernel nuevo (falla en la primera celda con error)
python tools/ejecutar_cuaderno.py --guardar Taller_Ajedrez_Grafico_Agentes_IA.ipynb   # guarda las salidas
python tools/correr_experimentos.py              # torneo, ablación y benchmarks completos (tarda horas)
jupyter notebook Taller_Ajedrez_Grafico_Agentes_IA.ipynb   # interfaz: kernel "Python (ia-taller3)"
```

La interfaz está en la sección 6 del cuaderno (`ChessApp(AGENT_FACTORIES)`). Los widgets solo responden con un kernel en marcha: ejecute el cuaderno hasta esa celda. Las exportaciones de la interfaz van a `resultados/interfaz/` (no versionada).

`tools/ejecutar_cuaderno.py` debe lanzarse con el Python del entorno `ia-taller3`. El cuaderno tarda unos minutos: repite en vivo el Experimento 1 y una partida corta, y carga el torneo, la ablación y el benchmark de MCTS guardados en `resultados/` (con `EJECUTAR_COMPLETO = True` repite el torneo en el propio cuaderno).

**Entorno verificado:** Python 3.13.7 · Windows 11 · chess 1.11.2 · ipywidgets 8.1.9 · notebook 7.6.5 · ipykernel 7.4.0 · matplotlib 3.11.2 · numpy 2.5.4 · nbformat 5.11.1 · nbclient 0.11.0 · pytest 9.2.0.

**Semillas:** cada partida tiene una semilla base y cada jugada recibe `semilla base + ply`. Los agentes usan `random.Random(seed)` local, nunca el generador global. Ajuste de pesos: generadores 31 (entrenamiento) y 7919 (prueba), recocido 2026. Exp. 4: semillas 0–4. Torneo y ablación: ver `resultados/*_config.json`. MCTS con simulaciones fijas es exactamente reproducible; los agentes con plazo de reloj dependen de la máquina.

## Fuentes y ayuda externa

python-chess (solo reglas, FEN, PGN y SVG; ningún motor UCI), ipywidgets, matplotlib, numpy y el pseudocódigo de *AIMA*. Desarrollado con ayuda de un asistente de IA (**Claude**, mediante **Claude Code**) para programar, probar, correr experimentos y redactar; los integrantes revisaron los resultados. Ver la portada del cuaderno y la etapa N de `BITACORA.md`.
