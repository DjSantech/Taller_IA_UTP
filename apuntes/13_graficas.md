### G.2. Visualizaciones: cómo se leen y qué permiten concluir

Todas las figuras salen de los registros de las ejecuciones (los `RunResult` o el CSV), ninguna de números escritos a mano, y se dibujan después de medir, nunca dentro de la región cronometrada. Cada algoritmo conserva el mismo color en todas las figuras.

<!-- celda -->

#### Figura 1: rutas inicial y final

Muestro la ruta de partida y la final de cada instancia. Con coordenadas (att48, berlin52) es un dibujo geográfico. Para las instancias de matriz explícita (gr48, brazil58) no hay coordenadas: uso una disposición **circular rotulada como esquemática, no geografía real**, más un mapa de calor de la matriz de pesos. Concluyo que la ruta final tiene menos costo y menos cruces que la inicial; **no** concluyo que una ruta sin cruces visibles sea óptima, ni que el círculo represente geografía.

<!-- celda -->

#### Figura 2: mejor costo acumulado frente a evaluaciones y frente a tiempo

Para HC, SA y GA grafico la **mediana** entre las diez semillas y una banda entre el primer y el tercer cuartil. Cada traza es una función escalonada (el mejor costo solo cambia en una mejora estricta) evaluada en una rejilla común. El trazo continuo indica que al menos la mitad de las semillas seguía ejecutando; el discontinuo es un valor **conservado** tras la parada, no evaluaciones ejecutadas. Presento las dos vistas porque el ranking por evaluaciones puede no coincidir con el ranking por tiempo: una evaluación no cuesta lo mismo en cada método. No generalizo a otras instancias ni afirmo superioridad cuando las bandas se solapan.

<!-- celda -->

#### Figura 3: gap por algoritmo e instancia

Cajas con los puntos individuales de cada semilla. Es la forma de comparar calidad **entre instancias**, porque el gap es relativo. Las ejecuciones sin gap (`N/A`) no se dibujan; por eso esta figura siempre se lee junto con la tabla de repeticiones válidas/previstas.

<!-- celda -->

#### Figura 4: tiempo y memoria de A* y RBFS frente a $k$

Muestro cómo crecen el tiempo (escala logarítmica) y la memoria incremental al aumentar el tamaño de la subinstancia. Una X roja marca las ejecuciones **interrumpidas** por un límite: su valor es una cota inferior de lo que habría costado terminar. Con esto comparo la memoria reducida de RBFS con su recomputación, sin suponer que menos memoria significa menos tiempo ni extrapolar a $k$ que no medí.

<!-- celda -->

#### Figura 5: recocido simulado

Tres paneles de una corrida: temperatura (escala logarítmica), costo actual junto al mejor costo acumulado, y tasa de aceptación de empeoramientos en una **ventana** cuyo tamaño está declarado en el eje. Sirve para ver que el enfriamiento controla cuánto empeoramiento se acepta: al inicio explora y al final se comporta como HC. No concluyo que SA mejore siempre a HC ni juzgo el método por una sola semilla.

<!-- celda -->

#### Figura 6: algoritmo genético

Mejor costo y costo mediano de la población por generación, junto con la diversidad (fracción de individuos únicos y diversidad de aristas). Una convergencia prematura se vería como una caída temprana de la diversidad, con la mediana pegada al mejor y el costo estancado lejos del óptimo. No atribuyo toda la mejora al cruce: también hay elitismo y mutación.

<!-- celda -->

#### Animación didáctica

Cuadros con las mejoras sucesivas de una ruta de berlin52, cada uno con el algoritmo, el costo y el trabajo acumulado. Se genera **después** de ejecutar, a partir del historial de rutas guardado. Ayuda a entender cómo se deshacen los cruces, pero no es una medición: no permite concluir velocidad ni comparar métodos.
