## Cómo leer este cuaderno (guion de mi exposición)

Este cuaderno es el enunciado del taller **completado**: conservé todos los enunciados y pseudocódigos tal como los entregó el docente (primer commit del repositorio, `e10a4f7`) y, debajo de cada sección, agregué mi código, mis pruebas, mis mediciones y mis apuntes. Cada afirmación remite a una celda de código, una tabla, una figura o una prueba de este mismo cuaderno.

**La pregunta central del taller** es *¿qué se gana y qué se pierde al cambiar garantía de optimalidad por rapidez, diversidad o menor consumo de memoria?* Mi respuesta se construye en cuatro pasos:

| Paso | Qué demuestro | Dónde |
|---|---|---|
| 1. Datos y modelo | Los pesos son los oficiales y el costo incluye el cierre del ciclo | §3, §4 |
| 2. Exactos (A\* y RBFS con MST) | Garantizan el óptimo; A\* gasta memoria, RBFS gasta recomputación | §5–§8, §13, §14 escala A |
| 3. Locales (HC, SA, GA) | Sin garantía, pero dan buenas rutas con un presupuesto fijo | §9–§12, §14 escala B |
| 4. Comparación | Con el mismo presupuesto, repeticiones y gap, ¿qué conviene cuándo? | §15–§16 |

**Cómo está construido (reproducibilidad).** El código vive en el paquete `tsp/` con pruebas en `tests/` (`pytest`); la herramienta `tools/construir_cuaderno.py` inserta ese mismo código en las celdas, por eso el cuaderno se ejecuta de arriba abajo sin importar nada del repositorio salvo los datos locales de `datos/`. Los resultados se guardan como registros (`resultados/*.csv`) y **todas** las tablas y figuras se generan a partir de ellos; no hay cifras escritas a mano como si fueran mediciones. La bitácora (`BITACORA.md`) recoge cada decisión de diseño y cada error que cometí y corregí.

**Reglas que me impuse y que se verifican en el cuaderno**

1. Los cinco algoritmos están escritos desde cero; solo uso `tsplib95` para leer datos y pesos oficiales.
2. Una sola función de costo (`tour_cost`) para todos; el delta de 2-opt se valida contra ella.
3. Un gap negativo detiene la ejecución y obliga a auditar (`AuditError`).
4. La calibración de parámetros se hace en instancias **distintas** de las de evaluación (gr17, burma14 y eil51) y los parámetros se congelan antes de la evaluación principal.
5. «Interrumpido» no es «fracaso» ni «óptimo»; solo A\* y RBFS terminados sin interrupción llevan certificado.
