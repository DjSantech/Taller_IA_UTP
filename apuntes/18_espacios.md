### A. Integrantes, entorno y decisiones (completado)

**Integrantes:** Santiago y Januar Mena (trabajo en pareja, la modalidad que propone el enunciado).

**Presupuestos y límites congelados** (todos viven en `FROZEN`, en la sección 14):

| Concepto | Valor |
|---|---|
| Semillas de evaluación | 0 a 9 (la calibración usó 100 a 104) |
| Escala B: evaluaciones y tiempo por ejecución | 30000 evaluaciones y 30 s, lo que ocurra primero |
| Escala A: evaluaciones y tiempo por ejecución (aproximados) | 5000 evaluaciones y 30 s |
| Exactos (A\* y RBFS) | 30 s, 100000 expansiones o 256 MiB de memoria incremental |
| Subinstancias | los primeros k = 6, 8, 10 y 12 identificadores ordenados |
| SA | α = 0,97; p0 = 0,8; Tmin = 10⁻³·T0; propuestas por temperatura derivadas del presupuesto |
| GA | población 40; 2 élites; pc = 0,9; pm = 0,3; torneo 3 |

**Políticas de desempate.** A\*: se extrae el nodo con menor `f`; si empatan, el de menor `h` (más cercano a la meta) y después el contador de inserción (determinista). RBFS: orden por `(f, h)` con desempate estable por orden de generación. HC: gana el primer vecino con el mejor delta estricto. GA: torneo por costo mínimo; ante un empate gana el primer participante sorteado.

**Decisiones.** Están todas en `BITACORA.md`, con sus alternativas, motivos y consecuencias, y con los errores que cometí y corregí (D-09 numeración de nodos, D-13 contraejemplo de la clave de estado, A-09 el `max` de RBFS, entre otros).

**Ayuda externa declarada.** Usamos un asistente de IA (**Claude**, mediante Claude Code) para programar los módulos, escribir las pruebas, ejecutar los experimentos y redactar estos apuntes; el trabajo se repartió entre agentes en paralelo por módulo y nosotros revisamos los resultados. Además usamos: `tsplib95` (lectura de instancias y pesos oficiales, sin resolver nada), las páginas de TSP Solve y de TSPLIB y el cuaderno de Peter Norvig sobre TSP como lectura de apoyo, y el pseudocódigo de AIMA para RBFS. Ninguna búsqueda ni optimización delega en SimpleAI, DEAP ni un solver. Ambos integrantes podemos explicar y modificar cualquier fragmento durante la sustentación; para eso preparamos guías de estudio por etapa.

**Entorno de ejecución.** Se imprime a continuación, con la herramienta de medición de memoria y sus límites.
