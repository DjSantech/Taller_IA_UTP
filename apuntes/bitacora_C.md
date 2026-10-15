# Bitácora C — Algoritmo genético (Taller 2)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan **ERROR CORREGIDO**.

---

### C-01 · Cromosoma sin el origen
- **Decisión:** el cromosoma tiene las n−1 ciudades distintas del origen; se decodifica anteponiendo el origen.
- **Alternativas:** permutación completa con el origen dentro; rotar al origen tras cada operador.
- **Por qué:** con el origen fuera, ningún operador puede moverlo o duplicarlo y no hace falta reparar rutas.
- **Consecuencia:** el parámetro `origin` funciona para la prueba de invarianza (`test_otro_origen_es_valido`).

### C-02 · OX literal del pseudocódigo
- **Decisión:** `_ox(parent1, parent2, left, right)` copia el segmento en las mismas posiciones y rellena desde right+1 en círculo con los genes de parent2 leídos desde right+1.
- **Alternativas:** variantes de OX que rellenan desde el inicio del cromosoma.
- **Por qué:** el enunciado fija ese pseudocódigo, y la actividad manual (hijo `[G,C,D,E,F,B]`) debe poder comprobarse a mano.
- **Consecuencia:** función pura, genérica sobre cualquier tipo de gen, probada con letras y con miles de cortes.

### C-03 · Contabilidad: copias heredadas no cuentan
- **Decisión:** las élites y las copias exactas de un padre (sin cruce ni mutación) heredan su costo y no suman evaluaciones; se anotan en `reused_costs`.
- **Alternativas:** reevaluar todo hijo; cache general por ruta.
- **Por qué:** 14.1 dice que las élites con costo conservado no se reevalúan, y una copia sin cambios es el mismo caso; una cache general añadiría una política que habría que medir.
- **Consecuencia:** el costo exacto de una generación varía (≤ población − élites); la prueba de presupuesto exacto usa `pc=1`, `pm=0`.

### C-04 · Reserva del peor caso antes de cada generación
- **Decisión:** si `evals + (población − élites) > max_evals`, paro antes con `EVAL_LIMIT`.
- **Alternativas:** generar a medias y descartar; usar todo el presupuesto.
- **Por qué:** 14.1: «no exceda el presupuesto para completar una generación».
- **Consecuencia:** con 30000 evaluaciones y población 80 sobran decenas de evaluaciones sin usar (p. ej. 29922–29976 usadas); es un costo asumido y documentado.

### C-05 · Duplicados permitidos; diversidad canónica
- **Decisión:** no filtro duplicados; mido `unique_fraction` con forma canónica (rotada al origen, menor entre ruta e inversa) y `edge_diversity`.
- **Alternativas:** rechazar hijos repetidos; contar rutas tal cual.
- **Por qué:** filtrar gasta evaluaciones y oculta la convergencia; contar rutas sin canonizar trata como distintos dos ciclos iguales.
- **Consecuencia:** la canonización no altera costo porque `D` es simétrica (probado).

### C-06 · Memético en archivo aparte
- **Decisión:** `tsp/memetico.py` (algorithm `GA+2opt`) con 2-opt de primera mejora, cada delta cuenta 1 evaluación y se desglosa en `ls_evals`/`child_evals`.
- **Alternativas:** un flag en `genetic_algorithm`.
- **Por qué:** 12.1 pide compararlo aparte y no atribuir al cruce la mejora de la búsqueda local; la reserva del peor caso no es posible porque el trabajo de 2-opt no se conoce de antemano.
- **Consecuencia:** puede terminar a mitad de generación (nunca excede el presupuesto). Hallazgo: en eil51 con 30000 evaluaciones gasta casi todo en la población inicial (0 generaciones); queda `ls_max_evals` como palanca para la calibración.

### ERROR CORREGIDO · Restos de código en el bucle de generaciones
- **Qué pasó:** en la primera versión de `ga.py` quedaron líneas provisionales (`if ... if False else False: pass`, una variable `p1_idx` que no estaba definida y una variable `inherited` sin uso).
- **Diagnóstico:** lo vi al releer el archivo, antes de ejecutarlo; habría fallado con `NameError` en cuanto una copia de padre no se cruzara ni mutara.
- **Corrección:** el torneo guarda los índices `p1_idx`/`p2_idx` y se eliminaron las líneas provisionales.
- **Lección:** releer el código recién escrito antes de la primera ejecución; los marcadores temporales no se dejan en el archivo.

### ERROR CORREGIDO · Prueba de «mejoras estrictas» incluía el punto final de la traza
- **Qué pasó:** `test_ruta_valida_y_costo_coherente` falló al exigir que todos los costos de `trace` fueran estrictamente decrecientes.
- **Diagnóstico:** el último punto de la traza es el cierre (mismas evaluaciones finales) y repite el mejor costo; no es una mejora.
- **Corrección:** la prueba compara solo `trace[:-1]` y verifica aparte que el último punto coincide con el resultado.
- **Lección:** la especificación de la traza (inicio, mejoras y final) hace que el final sea un punto distinto; la prueba debía reflejarla.

### Nota de entorno
- Mi script de cordura compartía la carpeta temporal de sesión con otro agente, que sobrescribió un archivo del mismo nombre. Mis cifras salieron de la ejecución anterior a ese cambio (impresas en pantalla y copiadas a los apuntes); no hubo efecto en el código del proyecto.
