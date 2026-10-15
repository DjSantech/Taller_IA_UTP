### 14.C Lectura de la Escala A (subinstancias de 6, 8, 10 y 12 ciudades)

Esta escala sirve para algo que la escala B no puede hacer: **tener un óptimo certificado** y medir con él a los métodos aproximados y el costo real de los exactos.

**1. Los óptimos están triplemente certificados.** Para k = 6, 8 y 10, A\*, RBFS y la programación dinámica de Held-Karp (un tercer método, independiente, escrito en `experimentos.py`) dan el mismo costo en las cuatro instancias; para k = 12 el certificado viene de A\* (y de RBFS cuando terminó). Si dos de ellos hubieran discrepado, el registro habría lanzado `AuditError`. Además hice 32 ejecuciones extra de A\* y RBFS con **otro origen** (la última ciudad): el costo óptimo es el mismo en todas, que es lo que debe ocurrir si la formulación de estados es correcta (y justamente lo que la página TSP Solve no cumple).

**2. A\* contra RBFS: la memoria se compra con recomputación.** En la tabla anterior:

| Caso | Expansiones A\* | Expansiones RBFS | Memoria A\* | Memoria RBFS |
|---|---:|---:|---|---|
| att48, k = 10 | 170 | 2793 | 237,7 KiB | 33,1 KiB |
| att48, k = 12 | 376 | 31961 | 568,3 KiB | 80,2 KiB |
| brazil58, k = 8 | 225 | 57313 | 82,6 KiB | 74,6 KiB |
| brazil58, k = 12 | 4478 | interrumpido | 2,3 MiB | 84,0 KiB |
| gr48, k = 12 | 38 | 79 | 61,9 KiB | 22,3 KiB |

En att48 con k = 12, RBFS expande **85 veces** más nodos que A\* y usa unas **7 veces** menos memoria. En brazil58 con k = 12 la diferencia de memoria es de unas 28 veces, pero RBFS no termina dentro de los límites. En gr48, en cambio, RBFS casi no retrocede (79 contra 38 expansiones): cuando la cota MST es muy ajustada, los valores respaldados casi nunca obligan a regenerar. **Lo que mide la regeneración es la estructura de la instancia**, no solo el tamaño.

**3. El tiempo crece muy distinto.** Con k = 12 A\* tarda del orden de décimas de segundo, mientras que RBFS necesita decenas de segundos y en varios casos alcanza el límite. El resultado más duro está en brazil58: RBFS se interrumpe en k = 10 por el límite de 100000 expansiones y en k = 12 por el de 30 s, y en esos casos **no devuelve ruta**; la tabla lo marca como «interrumpido», no como fracaso ni como óptimo. El caso berlin52 con k = 12 está **en el borde del límite de tiempo** (RBFS tarda del orden de 28 a 30 s según la carga del equipo), así que su censura depende de la máquina y no debe usarse para comparar.

**4. Límite de la medición.** Medir la memoria con `tracemalloc` multiplica el tiempo de los exactos por un factor de entre ≈ 5 y 9 en los tres casos medidos (×5,3 a ×8,7 en la ejecución registrada) (celda anterior). Los tiempos de A\* y RBFS son comparables **entre sí** porque ambos se miden igual, pero no son tiempos «limpios» ni se pueden comparar con los de HC, SA y GA. Los métodos locales no miden memoria (columna «no medida»).

**5. Los aproximados en subinstancias.** Contra el óptimo certificado, con 10 semillas por caso y 5000 evaluaciones:

| k | HC | HC con reinicios | SA | GA |
|---:|---|---|---|---|
| 6 | 100 % óptimos | 100 % | 100 % | 100 % |
| 8 | 100 % | 100 % | 100 % | 100 % |
| 10 | 78 % (gap máximo 3,21 %) | 100 % | 100 % | 88 % (máx. 1,54 %) |
| 12 | 80 % (máx. 3,71 %) | 100 % | 100 % | 92 % (máx. 3,71 %) |

(Cada porcentaje es sobre 40 ejecuciones: 4 instancias × 10 semillas.) A tamaños de 6 y 8 ciudades todos los métodos resuelven todo, así que ahí no hay nada que comparar; las diferencias aparecen desde k = 10. Esto **no** autoriza a extrapolar a 48 ciudades: lo que ocurre allí está en la escala B.
