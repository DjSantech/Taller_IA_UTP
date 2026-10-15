### 11.A Comparación controlada HC vs. SA (sección 11.1)

**Control.** Para cada semilla, HC y SA parten de **la misma ruta inicial** (la tabla lo verifica con una aserción) y usan la misma vecindad 2-opt; el generador de la inicialización es independiente del que toma las decisiones de cada algoritmo. Así, cualquier diferencia se debe al algoritmo y no a la ruta de partida. El trabajo de calibración de T0 de SA se **cuenta** dentro de las 30000 evaluaciones (no es gratis).

**Resultado en eil51** (óptimo 426): con la misma ruta inicial, HC termina entre 542 y 615 y SA entre 441 y 460, en las cinco semillas. HC se detiene por agotar el presupuesto (`EVAL_LIMIT`) y SA por enfriarse (`COOLED`).

**Respuestas a las preguntas de 11.1**, con la evidencia de este cuaderno:

- *¿SA mejora siempre a HC?* En la escala B, en las 40 ejecuciones de SA contra las 40 de HC con la misma semilla e instancia, SA gana en las 40 (verificado pareja por pareja). Pero no es una ley: en las subinstancias pequeñas (k = 6 y 8) ambos alcanzan el óptimo en el 100 % de los casos y empatan. Y SA no conserva su ventaja si su calendario no cabe en el presupuesto (hallazgo B-10 de la bitácora).
- *¿Qué ocurre con una temperatura inicial demasiado baja?* SA se comporta como un HC aleatorizado: casi no acepta empeoramientos y se atasca en el primer óptimo local. La calibración con `p0` ∈ {0,5; 0,8} lo refleja: con `p0 = 0,5` la aceptación inicial es menor y el resultado en eil51 es peor (4,69 % contra 3,52 % con α = 0,97).
- *¿Cómo afecta el enfriamiento a la aceptación?* La figura 5 muestra la tasa de aceptación de empeoramientos cayendo junto con la temperatura: alta al inicio (se explora), cercana a cero al final (se refina).
- *¿Una mejora final compensa necesariamente el trabajo adicional?* No necesariamente: SA gasta más evaluaciones en aceptar movimientos que no mejoran y en calibrar T0. Compensa cuando el presupuesto es lo bastante grande para completar el enfriamiento, como aquí (todas las ejecuciones terminan en `COOLED`).
