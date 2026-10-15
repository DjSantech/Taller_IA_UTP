# Bitácora A — algoritmos exactos (MST, A\*, RBFS)

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores reales llevan la marca **ERROR CORREGIDO** con *Qué pasó / Diagnóstico / Corrección / Lección*.

---

### A-01 · Pendientes como máscara de bits
- **Decisión:** `remaining` es un entero (bit *v* encendido = la ciudad *v* falta). El bit del origen nunca se enciende.
- **Alternativas:** `frozenset` de ciudades; tupla ordenada.
- **Por qué:** es inmutable y hashable, quitar una ciudad es `mask ^ bit` en O(1) y ocupa mucho menos memoria que un `frozenset` por nodo, y la memoria es una variable medida en el taller.
- **Consecuencia:** hace falta `mask_cities` para pasar a lista cuando se calcula el MST (O(n)); el costo es menor que el del propio MST.

### A-02 · Clave de estado `(last, remaining, closed)`
- **Decisión:** la clave del enunciado, sin añadir profundidad ni costo.
- **Alternativas:** solo la última ciudad; última ciudad + profundidad.
- **Por qué:** dos nodos con esta clave tienen exactamente las mismas continuaciones, así que se conserva el de menor $g$. Con solo la ciudad se descartan rutas parciales que sí llegan al óptimo (contraejemplo de 5 ciudades, A-11).
- **Consecuencia:** el diccionario `bestG` crece con el número de estados distintos (hasta $n2^{n-2}$).

### A-03 · Prim O(|U|²) con "mejor costo de conexión"
- **Decisión:** vector `best[j]` con la arista más barata de cada pendiente hacia lo ya conectado, eliminando por intercambio con el último elemento.
- **Alternativas:** Prim conceptual O(|U|³); Kruskal con ordenación.
- **Por qué:** es el O(|U|²) que pide la sección 6.1 y es el más natural con matriz densa.
- **Consecuencia:** `mst_edges` es una segunda implementación (con origen de cada arista) para validar que es árbol; ambas se contrastan con un Kruskal escrito en el test.

### A-04 · Desempate `(f, h, contador)`
- **Decisión:** a igual $f$, menor $h$; a igual, FIFO. Sucesores por posición ascendente.
- **Alternativas:** solo contador; mayor $g$ explícito.
- **Por qué:** menor $h$ con igual $f$ equivale a mayor $g$ y favorece nodos avanzados y cerrados; el contador además impide comparar nodos.
- **Consecuencia:** en el microcaso $B$ ($h=10$) se expande antes que $E$ ($h=11$), ambos con $f=14$. El costo no depende del desempate.

### A-05 · Memoria cada 256 expansiones — ERROR CORREGIDO (antes de ejecutar)
- **Decisión:** `MEM_CHECK_EVERY = 256`; tiempo y expansiones se consultan en cada iteración.
- **Alternativas:** medir memoria en cada expansión; cada 1 000.
- **Por qué:** `tracemalloc.get_traced_memory` en cada iteración añade ruido; 256 expansiones es granularidad suficiente. Consecuencia declarada: la memoria puede rebasar el límite hasta ~256 expansiones antes de detectarse.
- **ERROR CORREGIDO — Qué pasó:** mi primera versión comprobaba `expanded % 256 == 0` en cada vuelta del bucle.
- **Diagnóstico:** al revisar el código vi que, si la frontera tiene muchas entradas obsoletas seguidas, `expanded` no cambia y la condición se cumple repetidamente: se mediría la memoria decenas de veces seguidas.
- **Corrección:** `next_mem_check`: se mide cuando `expanded >= next_mem_check` y se avanza 256. Misma lógica en RBFS.
- **Lección:** una condición sobre un contador que no avanza en todas las iteraciones puede dispararse en rachas.

### A-06 · Qué es "regeneración" en RBFS y registro de auditoría
- **Decisión:** regeneración = expandir un nodo (identificado por su camino) ya expandido antes. `audit=True` guarda un conjunto de hashes de 64 bits de los caminos; `audit=False` cuenta solo la re-expansión del mismo registro vivo (cota inferior).
- **Alternativas:** identificar por estado `(last, remaining)`; guardar caminos completos.
- **Por qué:** por estado confundiría ramas distintas con regeneración; caminos completos gastarían mucha más memoria. El hash de 64 bits es compacto y su probabilidad de colisión es despreciable.
- **Consecuencia:** el registro cuesta ~70 B por camino distinto (brazil58, k=8: pico 76 532 B con auditoría, 10 736 B sin ella) y la cota inferior es floja (826 frente a 56 374 exactas). Las tablas de memoria de RBFS usan `audit=False`.

### A-07 · `upper_bound` en A\*
- **Decisión:** podar hijos con $g+h>$ cota. Si sale un cerrado, es óptimo; si se agota la frontera, solo se afirma que no existe ruta ≤ cota (`EXHAUSTED`, `NO_ROUTE`, nota en `extras`).
- **Por qué:** $h$ admisible hace segura la poda, y no confundir la ruta de la cota con una descubierta por A\* (sección 4).

### A-08 · Hallazgo: la heurística MST es consistente
- **Decisión:** analizar la consistencia con demostración y con comprobación.
- **Resultado:** 0 violaciones en 37 998 transiciones y en 2 394 204 de una búsqueda previa de contraejemplos; la demostración usa MST($U$) ≤ MST($U\setminus w$) + mín $d(w,u)$, mín $d(v,u)\le d(v,w)$ y que el mínimo sobre un conjunto mayor no sube.
- **Consecuencia:** $g+h$ no baja a lo largo de una ruta, pero se conserva `bestG` y las entradas obsoletas (un estado puede generarse antes por un camino caro y mejorar mientras sigue en la frontera).

### A-09 · ERROR CORREGIDO — "el máximo de RBFS es neutro con una cota consistente"
- **Qué pasó:** en una primera redacción de la prueba y de la guía de estudio escribí que, al ser $h$ consistente, `max(g+h, node.f)` nunca cambiaba el valor.
- **Diagnóstico:** al preparar el ejemplo de por qué se usa el máximo vi que después de un retroceso el $f$ respaldado de un nodo (14 en la traza de 4 ciudades) supera su $g+h$ (12), y los hijos regenerados lo heredan. Lo comprobé instrumentando el código: en att48 k=8 el máximo elevó 235 de 1 493 hijos.
- **Corrección:** renombré la prueba (ahora solo afirma que $g+h$ no decrece), añadí el contador `raised_by_max` y la prueba `test_rbfs_el_maximo_transmite_el_valor_respaldado`, y corregí la guía.
- **Lección:** consistencia de $h$ no es consistencia del $f$ respaldado; hay que distinguir el $f$ estático del $f$ aprendido.

### A-10 · ERROR CORREGIDO — número equivocado en una aserción
- **Qué pasó:** en la prueba de las dos rutas parciales fusionables escribí a ojo que el total de la ruta $X$ era 23.
- **Diagnóstico:** la prueba falló (14 ≠ 23). Recalculé: $X=A\!-\!B\!-\!D$ tiene $g=2$ y mejor continuación $D\!-\!C\!-\!E\!-\!A=1+10+1=12$, total 14.
- **Corrección:** valor 14 en la aserción; sigue siendo mayor que el óptimo 5 de $Y$, que es lo que demuestra el contraejemplo.
- **Lección:** los números de las pruebas salen de calcularlos con el oráculo, no de estimarlos mentalmente.

### A-11 · ERROR CORREGIDO — qué falla con la clave "solo ciudad"
- **Qué pasó:** esperaba que la variante con clave `(última ciudad, closed)` devolviera una ruta *más cara*. Mi primer script de búsqueda de contraejemplos además lanzó `KeyError` porque inicialicé `bestG` con una clave distinta de la que consultaba.
- **Diagnóstico:** tras unificar la clave, probé miles de matrices de 5 a 7 ciudades: la variante nunca dio una ruta más cara; o acertaba o **no hallaba ninguna** (frontera vacía).
- **Corrección:** el contraejemplo del test afirma exactamente eso (`malo is None or malo.g > óptimo`) y la explicación dice que el daño es perder rutas y la garantía. La demostración conceptual sigue siendo el par $X$/$Y$ con totales 14 y 5.
- **Lección:** no afirmar un modo de falla que no se pudo reproducir.

### A-12 · ERROR CORREGIDO — medición con tiempo imposible
- **Qué pasó:** en la primera tanda de medidas, A\* en att48 completa con tope de 10 s reportó `elapsed_seconds = 3975` con solo 16 expansiones.
- **Diagnóstico:** 3975 s no es coherente con 16 expansiones ni con el tope; el reloj saltó (probablemente el equipo se suspendió mientras corría en segundo plano; no lo pude verificar). Las expansiones y los contadores no se afectan, el tiempo sí.
- **Corrección:** repetí esa ejecución sola: 765 expansiones, 10.04 s, `TIME_LIMIT`. Las demás filas de la tanda son coherentes.
- **Lección:** validar cada medición contra otra variable (aquí, expansiones por segundo) antes de citarla.

### A-13 · Viabilidad de los límites propuestos (30 s, 100 000 expansiones, 256 MiB)
- **Hallazgo:** A\*+MST termina todas las subinstancias k ≤ 12 de las cuatro instancias (máximo 4 478 expansiones, 2.4 MB, 0.55 s). RBFS no: en brazil58 k=10 llega a 100 000 expansiones (13.5 s) y en k=12 al tiempo (30 s), y berlin52 k=12 tarda 28.1 s (casi el límite). El límite de memoria nunca se alcanza en estas pruebas (máximo ≈ 14 MB de A\* en instancias completas a 10 s).
- **Decisión:** mantener los límites propuestos y tratar las interrupciones de RBFS como resultados censurados, no como errores; reportarlos con denominador.
- **Consecuencia:** la medición con `tracemalloc` multiplica el tiempo por ≈ 5–9; por eso existe `measure_memory=False`. Las cifras de memoria varían entre corridas (p. ej. 487 KB y 628 KB para el mismo caso).
