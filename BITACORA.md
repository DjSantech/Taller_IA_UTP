# Bitácora de decisiones

Registro breve y fechado de las decisiones de diseño, los errores cometidos y su
corrección. El enunciado exige poder explicar en la defensa **una decisión que
produjo un error y cómo se corrigió**: esa evidencia se construye aquí, no al final.

Formato de cada entrada:

- **ID** — identificador estable para poder citarlo en el cuaderno.
- **Decisión** — qué se eligió.
- **Alternativas** — qué se descartó.
- **Por qué** — criterio que resolvió el empate.
- **Consecuencia** — qué habría que cambiar si la decisión fuera distinta.

---

## Etapa 0 — Estructura del repositorio (2026-09-21)

### D-01 · El entregable es la propia plantilla, no un cuaderno nuevo

- **Decisión:** completar el cuaderno recibido, conservando su numeración y sus
  secciones, en vez de escribir uno propio desde cero.
- **Alternativas:** cuaderno nuevo con estructura propia; código en módulos `.py`
  importados por un cuaderno delgado.
- **Por qué:** la sección 13 («Entrega») enumera las once partes esperadas en el
  orden de la plantilla, y penaliza «celdas fuera de orden» y «dependencias
  implícitas». Un cuaderno autocontenido es la lectura más literal y más segura
  de ese requisito.
- **Consecuencia:** el código vive en celdas, no en módulos; a cambio, hay que
  cuidar que cada celda dependa únicamente de celdas anteriores.

### D-02 · Primer commit con el enunciado intacto

- **Decisión:** el commit inicial contiene la plantilla tal como se recibió, sin
  una sola línea de solución.
- **Por qué:** hace verificable en el historial qué fue entregado por el docente
  y qué fue escrito por el estudiante. Sin ese punto de partida, el `diff` de
  autoría no existe.
- **Consecuencia:** ninguna; es gratis y solo se puede hacer una vez.

### D-03 · Entorno virtual fuera de la carpeta sincronizada

- **Decisión:** el entorno vive en `C:\Users\<usuario>\venvs\ia-taller1`, es decir **fuera** del proyecto, y
  `requirements.txt` fija las versiones exactas.
- **Alternativas:** `.venv` dentro del proyecto; instalar en el Python global.
- **Por qué:** dos razones distintas. (a) «Reproducible» incluye las versiones de
  las bibliotecas: SimpleAI y AIMA-Python son proyectos antiguos y su
  comportamiento cambia entre versiones, así que un entorno aislado y fijado
  evita que el cuaderno deje de ejecutarse. (b) El proyecto está dentro de
  OneDrive, y un entorno local son unos 3.000 archivos que OneDrive
  sincronizaría continuamente, con riesgo de corromperlo a mitad de una
  escritura.
- **Consecuencia:** hay que activar el entorno antes de abrir Jupyter, y el
  cuaderno debe usar el kernel `ia-taller1` registrado con `ipykernel`.

### D-04 · Los commits no llevan salidas de celda; la ejecución completa va al final

- **Decisión:** durante el desarrollo el cuaderno se versiona con las salidas
  limpias. El commit de entrega contiene una ejecución íntegra de arriba abajo.
- **Alternativas:** guardar las salidas en cada commit.
- **Por qué:** un `.ipynb` con salidas almacena las imágenes como base64 dentro
  del JSON, así que cada gráfica convierte el `diff` en miles de líneas
  ilegibles y el historial deja de servir como evidencia de proceso. Separar las
  dos cosas conserva lo que pide el enunciado —«todo el cuaderno debe ejecutarse
  desde el inicio en un entorno limpio»— y además un historial legible.
- **Consecuencia:** antes de entregar hay que hacer *Restart & Run All* y
  comprobar que no quede ninguna celda sin ejecutar ni fuera de orden.

### D-05 · AIMA-Python se vendoriza; SimpleAI se instala

- **Decisión:** SimpleAI entra por `pip`, porque está publicado en PyPI.
  AIMA-Python se copia al proyecto como `aima/search.py` y `aima/utils.py`, sin
  modificar una sola línea y con su procedencia citada.
- **Por qué:** AIMA-Python no se publica en PyPI, es un repositorio de
  referencia. Al 2026-09-21 sus módulos ya no están en la raíz del repositorio
  sino bajo `aima/`: la URL de la sección 14 del enunciado apunta a la ruta
  correcta, mientras que la ruta histórica devuelve 404. Vendorizar deja el
  cuaderno ejecutable sin depender de que el repositorio remoto no vuelva a
  reorganizarse.
- **Consecuencia:** el enunciado exige instrumentar «sin alterar permanentemente
  el repositorio», así que los contadores irán en subclases y envoltorios, nunca
  editando los archivos vendorizados. Tocarlos sería una falta.

### D-06 · Verificación temprana del riesgo de compatibilidad

- **Decisión:** antes de escribir cualquier algoritmo se comprobó que SimpleAI
  0.8.3 (publicado en 2021) importa y resuelve un `SearchProblem` mínimo de
  cuatro nodos bajo Python 3.13.7.
- **Por qué:** si la biblioteca no funcionara, la versión 2 del taller —12% de la
  nota— exigiría otra estrategia, y descubrirlo al final obligaría a rehacer
  trabajo. Comprobarlo ahora costó un minuto.
- **Resultado:** funciona. `breadth_first(..., graph_search=True)` devuelve el
  camino esperado como lista de pares `(acción, estado)`.

---

## Etapa 1 — Auditoría del generador Hunt-and-Kill (2026-09-21)

### D-07 · Las utilidades de verificación no reutilizan los buscadores

- **Decisión:** la inundación (`inundar`) y el detector de ciclos
  (`buscar_ciclo`) de la Actividad 1 se escriben aparte y no se comparten con
  los algoritmos de la Versión 1.
- **Alternativas:** implementar primero el BFS de la Versión 1 y usarlo para
  comprobar la conectividad del grafo, ahorrando código.
- **Por qué:** si el grafo se valida con el mismo buscador que después va a
  correr sobre ese grafo, un error compartido por ambos **se cancela** y la
  prueba pasa estando las dos cosas mal. Una prueba solo tiene valor si puede
  fallar de forma independiente de aquello que verifica. Además la auditoría
  debe poder ejecutarse antes de que exista un solo buscador, que es el orden
  en que el enunciado plantea las secciones.
- **Consecuencia:** hay duplicación deliberada de unas veinte líneas. Es el
  precio de la independencia y se asume a sabiendas.

### D-08 · Se audita la reproducibilidad entre procesos, no solo dentro de uno

- **Decisión:** además de comprobar que la misma semilla reproduce el mismo
  grafo en el proceso actual, se lanzan subprocesos con `PYTHONHASHSEED` en
  {0, 1, 42} y se comparan huellas SHA-256.
- **Por qué:** el generador ejecuta `rng.choice(tuple(no_visitadas))` y en la
  fase Hunt recorre `no_visitadas` con un `for`. El **orden de iteración de un
  conjunto alimenta al generador aleatorio**. Eso es reproducible solo porque
  las celdas son tuplas de enteros y CPython no aleatoriza el hash de enteros
  ni de tuplas de enteros. Con celdas representadas como cadenas, la semilla
  no garantizaría nada y una prueba de un solo proceso no lo detectaría nunca.
- **Consecuencia:** queda justificado por qué el enunciado exige estados
  inmutables y hashables: la representación del estado condiciona la
  reproducibilidad, no es una cuestión de estilo. Esta decisión fija la
  representación `(fila, columna)` como tupla de enteros para todo el taller.

### D-09 · ERROR CORREGIDO — la prueba de no idempotencia estaba mal planteada

- **Qué se hizo primero:** la comprobación 11 verifica que llamar `generar()`
  dos veces sobre el mismo objeto rompe el árbol (agrega otras |V|-1 aristas y
  crea ciclos). Se escribió asumiendo que eso vale para cualquier rejilla.
- **Qué falló:** al ejecutar la batería sobre los casos límite, la
  comprobación 11 **falló en una rejilla 1x5** y detuvo el cuaderno.
- **Diagnóstico:** en una rejilla degenerada 1xN o Nx1 la rejilla *es* un
  camino y su único árbol de expansión es ella misma. Tras la primera pasada
  todas las aristas posibles ya existen, así que la segunda intenta recrear
  **las mismas** aristas y `set.add` las descarta en silencio: el conteo
  permanece en |V|-1 y no aparece ningún ciclo.
- **Corrección:** el defecto no es universal. Se observa solo si la rejilla
  posee ciclos propios, es decir si filas >= 2 y columnas >= 2. La
  comprobación se marca **no aplicable** en rejillas degeneradas, en lugar de
  forzarla o de borrarla.
- **Lección:** el error estaba en la prueba, no en el código auditado. Los
  casos límite no sirven solo para encontrar fallos en el sujeto: también
  revelan supuestos no declarados en el instrumento de medición.

### D-10 · ERROR CORREGIDO — `inspect.getsource` no lee una celda bajo nbconvert

- **Qué se hizo primero:** la comprobación 10 necesita el fuente de
  `LaberintoHuntKill` para re-ejecutarlo en un subproceso limpio, y se obtenía
  con `inspect.getsource(clase)`.
- **Qué falló:** funcionaba al ejecutar el código como script y habría
  funcionado en una sesión interactiva de Jupyter, porque IPython registra el
  código de cada celda en `linecache`. Pero al comprobar que el cuaderno corre
  de arriba abajo con `jupyter nbconvert --execute` —justamente el modo que
  exige el enunciado— lanzó `OSError: source code not available`.
- **Por qué fue peor que un fallo:** el respaldo marcaba la comprobación como
  «no aplicable», así que la auditoría **parecía** pasar con un agujero dentro.
  Un fallo ruidoso habría sido preferible a una degradación silenciosa.
- **Corrección:** una función `fuente_del_generador` que intenta
  `inspect.getsource` y, si falla, lee el propio `.ipynb` del directorio de
  trabajo y localiza la celda que define la clase **por el nombre de la clase,
  no por su índice**, de modo que reordenar celdas no rompa la prueba. Y el
  resumen de la auditoría ahora imprime explícitamente cuántas comprobaciones
  quedaron sin aplicar, para que una degradación no pase desapercibida.
- **Lección:** «funciona en mi sesión de Jupyter» no equivale a «el cuaderno se
  ejecuta en un entorno limpio». Son dos entornos distintos y el enunciado
  evalúa el segundo.

### D-11 · Cada prueba de invariancia lleva su contra-experimento

- **Decisión:** la comprobación 10 no solo verifica que el laberinto sea
  invariante frente a `PYTHONHASHSEED`; ejecuta en paralelo el mismo
  experimento con las celdas representadas como **cadenas** y exige que ahí el
  orden **sí** cambie.
- **Por qué:** una prueba que no puede fallar no vale nada. Si `PYTHONHASHSEED`
  no llegara al subproceso —un error al construir el diccionario de entorno, o
  una versión de Python que lo ignorase—, las tres huellas coincidirían por una
  razón trivial y la comprobación pasaría sin haber comprobado nada. El
  contra-experimento demuestra que la variable surte efecto.
- **Evidencia medida:** con tuplas, las tres huellas son `a93509a735f498d8`;
  con cadenas, son `f53b8fdc…`, `8bdb23d1…` y `373d0253…`, tres órdenes
  distintos.
- **Consecuencia:** el patrón se reutiliza en la sección 8. Toda prueba de
  concordancia entre versiones incluirá un caso donde deba discrepar.

---

## Etapa 2 — Instancia individual y formulación formal (2026-09-23)

### D-12 · Una sola fuente de parámetros, validada antes de generar

- **Decisión:** semilla, filas, columnas, inicio y meta se definen una única
  vez, en la celda de la sección 2, y se agrupan en un objeto `INSTANCIA`
  inmutable. Toda sección posterior lee `INSTANCIA`; ninguna repite un valor.
  La semilla y las dimensiones se **derivan** del código estudiantil con la
  regla literal del enunciado, en vez de escribirse a mano.
- **Alternativas:** constantes sueltas repetidas en cada sección, o escribir
  directamente `97950, 20, 25`.
- **Por qué:** el enunciado anuncia una **modificación en vivo** de inicio,
  meta, semilla o costo durante la defensa. Con valores repetidos, un cambio
  en un sitio y no en otro produce resultados incoherentes sin ningún error
  visible. `construir_instancia` además valida antes de generar: un inicio
  escrito como lista, fuera de la rejilla o en un cuadrante no opuesto falla
  ahí con un mensaje claro, no diez celdas más abajo dentro de un buscador.
- **Verificado:** `[3, 4]` como lista, meta `(3, 20)` en el mismo lado y meta
  `(20, 20)` fuera de rango se rechazan con `ValueError`; una instancia
  `21 x 23` con semilla 12345 se construye y se resuelve sin tocar otra celda.
- **Consecuencia:** los ejemplos del cuaderno no pueden suponer propiedades de
  **esta** instancia. La demostración de una acción bloqueada por pared busca
  una celda que la tenga en vez de asumir que el inicio la tiene; la
  contra-prueba del validador invierte la primera acción, que falla con
  cualquier inicio.

### D-13 · El grafo compartido se congela

- **Decisión:** el diccionario que devuelve el generador se convierte en un
  `MappingProxyType` de `frozenset`. Cualquier intento de modificarlo lanza
  una excepción.
- **Alternativas:** confiar en que ningún algoritmo lo modifique, o entregar
  una copia a cada algoritmo.
- **Por qué:** las tres versiones y los siete algoritmos comparten el mismo
  grafo, como exige el enunciado. Un `grafo[celda].discard(...)` accidental en
  un algoritmo alteraría en silencio las métricas de todos los que corran
  después, y la comparación final dejaría de ser justa. Copiar por algoritmo
  evita el contagio pero no detecta el error; congelar hace las dos cosas.
- **Consecuencia:** las transformaciones de la sección 9 (abrir paredes,
  asignar costos) deberán construir un grafo **nuevo** a partir de este, que
  es lo que el enunciado pide de todos modos («sin modificar el generador»).

### D-14 · Las acciones son direcciones, en orden fijo N, E, S, O

- **Decisión:** una acción es una dirección `N`, `E`, `S` u `O`, no la celda
  destino. `ACCIONES(s)` las devuelve siempre en ese orden, filtrando las que
  tienen pared; no se itera `grafo[s]`.
- **Alternativas:** usar la celda destino como acción; iterar el conjunto de
  vecinos en el orden que dé Python.
- **Por qué:** el contrato de la sección 4 pide `camino` y `acciones` por
  separado. Si las acciones fueran celdas, `acciones` sería `camino[1:]`
  repetido. En cuanto al orden, el de un `set` de tuplas es reproducible
  (D-08) pero depende de la historia interna del generador y **no se puede
  explicar**. Con un orden declarado, «DFS prueba primero el norte» es una
  afirmación verificable, y las tres versiones desempatan igual. Sin eso, las
  pruebas de concordancia de la sección 8 compararían métricas que difieren
  por el orden de los vecinos y no por el algoritmo.
- **Consecuencia:** SimpleAI y AIMA-Python recibirán adaptadores sobre
  `ProblemaLaberinto` que respeten este orden, en lugar de una segunda
  formulación escrita a mano.

### D-15 · Inicio `(3, 4)` y meta `(16, 20)`; regla de cuadrantes declarada

- **Decisión:** puntos interiores en los cuadrantes noroeste y sureste, no las
  esquinas. Dos celdas están en cuadrantes opuestos si difieren en ambos ejes.
  Con una dimensión impar, la línea central pertenece a la mitad norte u oeste
  (`2*i < n`).
- **Por qué:** la sección 1 ya auditó el recorrido esquina a esquina
  `(0, 0) → (19, 24)`; repetirlo no aportaría un caso nuevo. Con 25 columnas la
  columna 12 no pertenece a ninguna mitad de forma natural, así que el
  desempate se declara en vez de dejarlo implícito, y los puntos elegidos
  están lejos de las líneas centrales para no depender de él.
- **Medido:** el camino único entre ambos tiene 60 celdas (profundidad 59), y
  la auditoría completa de la instancia con esos extremos da 11/11.

### D-16 · Un camino de referencia obtenido sin buscadores

- **Decisión:** la sección 2 calcula `CAMINO_REFERENCIA` con `caminos_simples`,
  la utilidad de verificación de la sección 1, y la sección 3 lo valida
  formalmente con `validar_solucion`.
- **Por qué:** como el laberinto es un árbol, existe un único camino simple, y
  la búsqueda en grafo nunca repite estados en el camino que devuelve. Por lo
  tanto **todo algoritmo completo de la Versión 1 debe devolver exactamente
  este camino**, aunque lo encuentre expandiendo nodos distintos. Eso
  proporciona un oráculo independiente de los buscadores (D-07) para las
  pruebas de la sección 8.
- **Consecuencia:** en el laberinto perfecto los algoritmos solo pueden
  diferir en sus métricas, no en la solución. La optimalidad solo se pondrá a
  prueba en la sección 9, donde hay ciclos y costos.

---

## Etapa 3 — Contrato, núcleo de búsqueda en grafo, BFS y DFS (2026-09-23)

### D-17 · BFS y DFS son una sola función con la frontera inyectada

- **Decisión:** `busqueda_en_grafo(problema, frontera, ...)` implementa el
  bucle una única vez. `bfs` le pasa una `FronteraFIFO` (un `deque`) y `dfs`
  una `FronteraLIFO` (una lista usada como pila). Las dos clases exponen la
  misma interfaz: `agregar_hijos`, `extraer` y `len`.
- **Alternativas:** dos funciones casi idénticas; o una sola con
  `if politica == "BFS"` repartidos por el cuerpo.
- **Por qué:** el enunciado pide que «la diferencia no quede dispersa por todo
  el programa». Con la frontera inyectada la diferencia entre BFS y DFS está
  en dos clases de diez líneas y en ningún otro sitio. Además, cualquier
  corrección al control de repetidos o a las métricas vale para las dos a la
  vez. Con dos copias, una corrección aplicada a una sola haría que la
  comparación entre ambas midiera el error y no la estrategia.
- **Consecuencia:** UCS **no** reutiliza este núcleo. Su control de repetidos
  es distinto (mejor costo y entradas obsoletas, no «ya alcanzado») y forzarlo
  en la misma función exigiría justo los `if` dispersos que se querían evitar.

### D-18 · La pila apila los hijos en orden inverso

- **Decisión:** `FronteraLIFO.agregar_hijos` apila los hijos invertidos, de
  modo que el primero en salir es el de la primera acción (N).
- **Por qué:** una pila devuelve primero lo último que entró. Sin invertir, la
  DFS exploraría en orden O-S-E-N y el orden fijo N-E-S-O (D-14) dejaría de
  describir lo que hace el algoritmo. La inversión vive en la frontera, no en
  el núcleo, porque es un detalle de la disciplina LIFO.
- **Evidencia:** contra-experimento en la 3x3. Con la pila invertida DFS
  extrae `(0,0) (0,1) (0,2) (1,1) (1,2) (2,2)`; con una pila sin invertir
  extrae `(0,0) (1,0) (2,0) (2,1) (0,1) (1,1) (1,2) (2,2)`, dos estados más.
  El cuaderno exige que ambos órdenes difieran.

### D-19 · Marcar al generar en BFS y DFS; prueba de objetivo al extraer

- **Decisión:** un estado entra en `alcanzados` en el momento en que se genera
  por primera vez. Los hijos repetidos se construyen, se cuentan como
  generados y se descartan. La meta se reconoce al **extraerla**, no al
  generarla.
- **Alternativas:** marcar al expandir (la frontera puede contener
  duplicados); en BFS, probar el objetivo al generar, lo que ahorra un nivel.
- **Por qué:** marcar al generar acota la frontera por |V| y en BFS es seguro,
  porque la cola extrae en orden de profundidad no decreciente. En DFS cambia
  el recorrido respecto de una DFS recursiva **solo si hay ciclos**; en el
  laberinto perfecto coinciden. La prueba al generar habría reducido los
  expandidos de BFS, pero el enunciado fija la convención y las métricas de
  los siete algoritmos tienen que ser comparables.
- **Predicción comprobada:** en un árbol, con marcado al generar, cada nodo
  expandido salvo la raíz genera exactamente un repetido: su padre. Por tanto
  `repetidos_descartados = expandidos − 1`. Se cumple para BFS (248 = 249 − 1)
  y DFS (296 = 297 − 1) en la instancia. Si fallara, el laberinto tendría un
  ciclo o el control de repetidos estaría mal. En la sección 9, con ciclos, la
  igualdad debe **dejar** de cumplirse.

### D-20 · Valores centinela del fracaso y definición de «generado»

- **Decisión:** sin solución se devuelve `costo = ∞` y `profundidad = −1`. El
  nodo inicial no cuenta como generado.
- **Por qué:** `0` no sirve como marca de fracaso, porque es la profundidad
  real del caso *inicio = meta*. Con `0` las dos situaciones serían
  indistinguibles en una tabla. `∞` es además el costo que usa AIMA para el
  nodo de fracaso, y hace que `min()` sobre costos funcione sin casos
  especiales. En cuanto a *generado*, el enunciado lo define como «nodo
  sucesor construido» y la raíz no es sucesor de nadie. Así *inicio = meta* da
  0 expandidos y 0 generados, como se comprueba en el cuaderno.
- **Hallazgo en revisión:** la primera versión de `verificar_resultado`
  exigía `expandidos ≤ |V|`. Es cierto en la búsqueda en grafo, pero IDDFS
  (etapa 5) vuelve a expandir los mismos estados en cada iteración y lo
  violaría de forma legítima. Se detectó al releer el código antes de
  ejecutarlo: la cota se trasladó a las pruebas de BFS y DFS, que es donde
  vale.

---

## Etapa 4 — Búsqueda de costo uniforme (2026-09-23)

### D-21 · UCS con eliminación perezosa y desempate por orden de inserción

- **Decisión:** la frontera es un montículo `heapq` de tuplas
  `(g, orden, nodo)`. `mejor_costo[s]` guarda el menor `g` conocido de cada
  estado, y un hijo entra a la frontera solo si lo mejora. La entrada vieja
  de un estado mejorado no se borra: queda **obsoleta** y se descarta al
  extraerla, porque su `g` supera a `mejor_costo[s]`. La prueba de objetivo
  se hace al extraer.
- **Alternativas:** *decrease-key* sobre la entrada existente, que `heapq`
  no ofrece y que exigiría buscarla en O(n) o mantener un índice aparte; un
  conjunto de «cerrados» además de `mejor_costo`.
- **Por qué:** la eliminación perezosa es el esquema que pide el propio
  pseudocódigo («ignorar entradas obsoletas»). Cuesta a lo sumo una entrada
  por arista mejorada, O(|E| log |E|) en total, y no necesita otra estructura.
  `orden`, un contador creciente, cumple dos funciones. Desempata los `g`
  iguales en orden de inserción, que es determinista. Y evita que `heapq`,
  ante dos `g` iguales, intente comparar dos `Nodo`, que no definen `<`: sin
  el contador el primer empate lanzaría `TypeError`.
- **Métricas:** una entrada obsoleta descartada cuenta en
  `repetidos_descartados`, igual que un hijo que no mejora. Cada hijo
  generado se descarta a lo sumo una vez, así que se mantiene
  `repetidos ≤ generados`. `frontera_maxima` incluye las entradas obsoletas,
  porque ocupan memoria de verdad. En el grafo ponderado de prueba UCS llega a
  4 y BFS a 3.
- **Contra-experimento:** una frontera ordenada por `g` dentro de
  `busqueda_en_grafo`, que marca al generar, devuelve una solución válida de
  costo 17 en lugar de 12. Justifica D-17: UCS no puede compartir el núcleo
  de BFS y DFS, porque su diferencia está en el control de repetidos, no solo
  en la frontera.

### D-22 · Predicción: con costo unitario, UCS recorre como BFS

- **Predicción:** con costo unitario `g` coincide con la profundidad, y el
  desempate FIFO del contador reproduce el orden de la cola de BFS. Por tanto
  UCS debe expandir **los mismos estados en el mismo orden** que BFS. En un
  árbol, además, no puede haber entradas obsoletas, porque nunca hay dos
  caminos hacia un mismo estado.
- **Resultado:** se cumple. Ambos expanden 249 estados en el mismo orden y
  UCS no registra ninguna entrada obsoleta. UCS tarda algo más (montículo:
  O(log n) por operación, frente a O(1) de la cola).
- **Consecuencia:** si el desempate fuera LIFO, o por estado, UCS encontraría
  el mismo costo pero expandiría otros nodos. La igualdad de métricas con BFS
  depende de una decisión de implementación, no solo de la teoría, y así debe
  explicarse en el análisis de la sección 11.

### D-23 · Los costos se asignan a aristas no dirigidas (decisión provisional)

- **Decisión:** en el grafo de prueba el costo pertenece al **corredor**: se
  indexa por `frozenset({s, s'})`, así que `c(s, a, s') = c(s', a', s)`.
  `costo_por_arista` convierte ese diccionario en la función `c(s, a, s')`
  que recibe `ProblemaLaberinto`.
- **Alternativas:** costo por **celda** («terreno»: se paga al entrar); costo
  por **acción** (por ejemplo, subir cuesta más que bajar).
- **Por qué:** con costo por celda o por acción, ir y volver por el mismo
  corredor costaría distinto. La búsqueda bidireccional (etapa 6) recorre las
  aristas **al revés** desde la meta, y con costos asimétricos tendría que
  usar los costos del grafo inverso, que es una fuente de error que no hace
  falta abrir. Con costos por arista el grafo sigue siendo simétrico también
  en costos, y la comprobación de simetría de la etapa 1 sigue significando
  lo mismo.
- **Consecuencia:** la sección 9 debe mantener esta decisión en las tres
  versiones, como exige el enunciado. Se registra ahora porque ya la usa el
  primer grafo ponderado del cuaderno.

---

## Etapa 5 — Búsqueda limitada y profundización iterativa (2026-09-23)

### D-24 · DLS controla repetidos sobre el camino actual, no con un conjunto global

- **Decisión:** DLS es una búsqueda en **árbol** con control de ciclos: un
  hijo se descarta solo si su estado ya está en el camino actual
  (`en_camino`), y ese estado se libera al retroceder. Se implementa de forma
  iterativa con una pila de pares `(nodo, iterador de acciones pendientes)`:
  los hijos se generan de a uno y la pila **es** el camino, así que la
  memoria es O(límite).
- **Alternativas:** reutilizar el conjunto de alcanzados de BFS/DFS; un
  diccionario `mejor_profundidad[s]` que permita reabrir un estado alcanzado
  a menor profundidad; una versión recursiva.
- **Por qué:** con un conjunto global, un estado alcanzado primero por una
  rama profunda queda marcado, y al llegar a él después por un camino más
  corto ya no se puede usar. Se pierden soluciones que sí caben en el límite.
  `mejor_profundidad` lo arregla, pero cuesta O(|V|) de memoria y anula la
  ventaja que justifica IDDFS. La versión iterativa evita el límite de
  recursión de Python en límites grandes.
- **Contra-experimento:** en una rejilla abierta de 2×4, de `(1,0)` a
  `(1,3)` con límite exacto 3, el control por camino halla
  `(1,0) (1,1) (1,2) (1,3)`. El control global visita `(0,0) (0,1) (0,2)
  (1,1)`, deja `(1,1)` marcado a profundidad 3 y devuelve **corte**, una
  respuesta falsa porque existe una solución de profundidad 3. El caso se
  encontró buscando de forma exhaustiva en rejillas abiertas pequeñas: en
  2×2, 2×3 y 3×3 no aparece ninguno con límite exacto.
- **Predicción comprobada:** con un límite que nunca se alcanza, DLS en un
  árbol recorre el mismo preorden N-E-S-O que la DFS de la etapa 3 y expande
  **los mismos 297 estados**, aunque son dos implementaciones distintas.
  Genera menos (562 frente a 597) porque produce los hijos de a uno y no
  llega a construir los hermanos que DFS apila y nunca visita.
- **Métricas:** un nodo que llega al límite se genera pero no se expande ni
  entra en la pila, así que `frontera_maxima ≤ límite`. La primera redacción
  del docstring decía `límite + 1`. La tabla mostró `DLS(58)` con frontera 58
  y la cota se corrigió antes del commit.

### D-25 · Corte y fracaso se distinguen en el propio resultado

- **Decisión:** `ResultadoBusqueda` gana un campo `corte: bool = False`.
  `encontrado = False, corte = True` significa «no hay solución dentro del
  límite, pero algo quedó sin explorar». `encontrado = False,
  corte = False` es un fracaso definitivo. `Metricas.resultado` fuerza
  `corte = False` cuando hay solución, y `verificar_resultado` lo comprueba.
- **Alternativas:** devolver un centinela aparte (una cadena `"corte"`, como
  hace AIMA); devolver una tupla `(resultado, corte)`.
- **Por qué:** el contrato exige que todos los algoritmos devuelvan el mismo
  registro, y un centinela de otro tipo rompería esa uniformidad justo en
  DLS. El campo tiene valor por omisión, así que los otros cinco algoritmos
  no cambian. Es la información que IDDFS necesita para decidir si sigue.
- **Criterio de corte:** el de AIMA, es decir, cualquier nodo que no es meta
  y llega al límite. Es algo conservador: un callejón sin salida justo en el
  límite cuenta como corte aunque no tenga nada debajo. Solo cuesta una
  iteración extra antes de declarar el fracaso, y a cambio el criterio es
  simple de enunciar y de defender.
- **Predicción comprobada:** con la meta inalcanzable (un corredor cortado),
  la componente del inicio llega a profundidad 32. IDDFS corta en los
  límites 0..32 y declara fracaso en el 33: exactamente 34 iteraciones, sin
  ningún tope externo.

### D-26 · IDDFS se reporta con las métricas acumuladas de todas las iteraciones

- **Decisión:** `expandidos`, `generados` y `repetidos` de IDDFS son la suma
  de todas sus iteraciones, y `frontera_maxima` es el máximo.
- **Por qué:** re-expandir los niveles superiores es el costo real de IDDFS.
  Reportar solo la última iteración lo haría parecer más barato que BFS.
- **Hallazgo:** en la instancia individual IDDFS expande 5 439 estados,
  **21,8 veces** los 249 de BFS. El argumento clásico, un sobrecosto del
  orden de *b/(b−1)*, supone una ramificación holgada. Un laberinto perfecto
  es casi un pasillo: el número de estados a profundidad ≤ L crece más o
  menos linealmente con L, y la suma de las iteraciones crece como L². Hay
  que llevarlo al análisis teórico de la sección 11: la ventaja de memoria de
  IDDFS tampoco se aprecia aquí, porque la frontera de BFS no pasa de 12.

---

## Etapa 6 — Búsqueda bidireccional (2026-09-23)

### D-27 · BFS bidireccional por capas completas, equilibrada por tamaño de frontera

- **Decisión:** dos BFS, desde el inicio y desde la meta. En cada paso se
  expande la **capa completa** del lado con la frontera más pequeña; en caso
  de empate, el de adelante. Cada lado tiene su propio diccionario
  `alcanzados` (estado → nodo), y cada hijo nuevo se busca en el del otro
  lado.
- **Alternativas:** alternar un nodo de cada lado; alternar capas sin mirar
  el tamaño; dos UCS.
- **Por qué:** alternar nodos sueltos mezcla profundidades distintas dentro
  de una misma frontera y complica el argumento de optimalidad (D-28). Elegir
  el lado más pequeño es la forma de «expandir de forma equilibrada» que pide
  el enunciado: gasta el trabajo donde crece menos. En la instancia resultan
  49 capas desde el inicio y 10 desde la meta, porque la frontera de la meta
  es más ancha.
- **Unión:** la mitad de atrás se invierte, y cada acción suya se reemplaza
  por su opuesta (`ACCION_INVERSA`). El costo total es `g_ad + g_at`, que
  solo es correcto porque los costos son de arista y simétricos (D-23).
  `verificar_resultado` recalcula el costo hacia adelante, así que una
  asimetría o una acción mal invertida haría fallar la celda.
- **Hallazgo:** en la instancia individual la búsqueda bidireccional expande
  218 estados, el 88 % de los 249 de BFS. La ventaja O(b^(d/2)) supone una
  ramificación que el laberinto perfecto no tiene.
- **Expectativa corregida por la medición:** el primer docstring afirmaba
  que, sin solución, «basta agotar el lado más pequeño». Es cierto que para
  cuando se vacía una frontera, pero no que el trabajo se limite a ese lado.
  Con el corredor cortado, la búsqueda bidireccional expande 95 estados
  frente a 89 de BFS: 89 desde el inicio, que agota su componente, y 6 desde
  la meta, en vano. El docstring se corrigió y la celda comprueba ese
  desglose.

### D-28 · El objetivo es el encuentro, detectado al generar; se reúnen todos los encuentros de la capa

- **Decisión:** la búsqueda termina cuando un hijo recién generado ya está
  alcanzado por el otro lado. Se completa la capa en curso, se reúnen todos
  los puntos de encuentro y se elige el de menor longitud total (en empate,
  el primero descubierto).
- **Desvío respecto de la convención:** los demás algoritmos prueban la meta
  al **extraer**. Aquí el objetivo no es un estado sino que dos regiones se
  toquen, y esperar a extraer ese estado de alguna frontera solo añadiría
  una capa de trabajo sin cambiar el resultado. Se documenta como excepción
  deliberada.
- **Lema de la capa:** con capas completas y detección al generar, todos los
  encuentros de una capa miden exactamente *k + j + 1*, que es la distancia
  óptima (demostración en el apartado 6.4 del cuaderno). Por tanto el primer
  encuentro ya es óptimo, y reunir los demás cuesta una sola capa.
- **Verificación empírica:** en 300 subgrafos aleatorios de rejillas
  pequeñas con ciclos (semilla fija), la búsqueda bidireccional concuerda con
  BFS en existencia de solución y en longitud. En los 71 casos con varios
  encuentros en la capa final, todos medían lo mismo.
- **Dos puntos de encuentro (caso límite de la sección 8):** en la rejilla
  abierta 2×2, de `(0,0)` a `(1,1)`, los encuentros `(0,1)` y `(1,0)` se
  detectan en la misma capa, ambos de longitud 2. Se elige `(0,1)` porque se
  descubre primero en el orden N-E-S-O, y la unión da las acciones `E S`.
- **Límite:** con costos no unitarios este algoritmo minimiza pasos, no
  costo. En el grafo ponderado de 2×4 devuelve costo 17 donde UCS encuentra
  12. Una versión óptima en costo requiere dos UCS y el criterio de parada
  `tope_ad + tope_at ≥ μ`; no se implementa porque el enunciado solo exige
  la optimalidad en costo a UCS.

---

## Etapa 7 — Algoritmo de Lee y frente de onda (2026-09-23)

### D-29 · Lee se implementa solo con etiquetas, sin nodos ni padres

- **Decisión:** `lee` traduce el pseudocódigo literalmente. Usa un
  diccionario `etiqueta[celda]` y dos listas, `frente_actual` y
  `frente_siguiente`. El camino se reconstruye desde la meta bajando por
  etiquetas decrecientes; en cada paso se toma el primer vecino, en orden
  N-E-S-O, con etiqueta `k − 1`, y la acción hacia adelante es la inversa.
- **Alternativas:** reutilizar `bfs` y mostrar sus niveles; guardar la
  procedencia de cada celda, como permite el pseudocódigo («registrar
  procedencia o dirección»).
- **Por qué:** reutilizar BFS convertiría la afirmación «Lee es BFS» en una
  tautología. Implementado aparte, que sus 253 etiquetas coincidan con la
  profundidad que BFS obtiene hasta cada celda es una comprobación real entre
  dos programas distintos. Reconstruir por etiquetas es la idea original de
  Lee (1961): las etiquetas bastan y no hacen falta padres. Además su
  corrección se demuestra con el mismo argumento inductivo del apartado 7.1.
- **Parada entre frentes:** como dice el pseudocódigo, se termina el frente
  en el que la meta recibe su etiqueta, pero no se procesa el frente de la
  meta. Por eso Lee expande 244 estados y BFS 249: BFS saca de su cola las
  celdas del nivel de la meta que entraron antes que ella. La celda comprueba
  que `expandidos` es la suma de todos los frentes salvo el último.
- **Métricas:** celda procesada = expandida; vecino examinado = generado;
  vecino ya etiquetado = repetido. `frontera_maxima` es el frente más
  grande, 11 en la instancia, alrededor del instante 49.
- **Contra-experimento:** «Lee con costos», con la etiqueta
  `etiqueta[u] + c(u, v)` asignada al primer contacto, deja 3 de 8 etiquetas
  erróneas en el grafo ponderado de 2×4. `(1,1)` recibe 8 y su costo mínimo
  es 6. Hace falta poder rebajar etiquetas y procesar en orden de costo, que
  ya es UCS.

### D-30 · La figura del frente de onda: una escala común y una sola tonalidad

- **Decisión:** ocho paneles (2×4) en los instantes `round(i·d/7)`, con
  i = 0..7, es decir 0, 8, 17, 25, 34, 42, 51 y 59. Cada celda alcanzada se
  colorea por su instante de llegada con una rampa secuencial de un solo tono
  (azul claro → oscuro); las no alcanzadas, en gris neutro fuera de la escala.
  La escala va de 0 a *d* y es **la misma en los ocho paneles**, con una
  única barra de color. El camino reconstruido aparece en naranja solo en el
  último panel.
- **Alternativas:** una rampa multicolor (tipo arcoíris), o una escala
  propia por panel.
- **Por qué:** el tiempo de llegada es una magnitud ordenada. Una rampa de un
  solo tono se lee como «más oscuro = más tarde», mientras que un arcoíris
  introduce saltos de tono que parecen fronteras y no lo son. Con una escala
  por panel, el mismo color significaría instantes distintos en cada uno y la
  comparación entre paneles se perdería.
- **La figura no es la evidencia:** el enunciado no acepta imágenes como
  prueba. La evidencia es el diccionario `ETIQUETA_LEE`, los frentes
  `FRENTES_LEE` y el mapa de etiquetas impreso como texto con
  `dibujar_laberinto`, la función cuya firma con `marcas` se diseñó en la
  etapa 1 precisamente para esto. La imagen se guarda en
  `resultados/lee_frente_de_onda.png`, que no se versiona porque se regenera.

---

## Etapa 8 — Versión SimpleAI (2026-09-23)

### D-31 · El adaptador delega en `ProblemaLaberinto`

- **Decisión:** `LaberintoSimpleAI(SearchProblem)` no reimplementa nada.
  `actions`, `result`, `is_goal` y `cost` llaman a los métodos de
  `ProblemaLaberinto`. El estado inicial es la tupla `(fila, columna)` y se
  usa siempre `graph_search=True`.
- **Alternativas:** escribir de nuevo las acciones sobre el grafo dentro del
  adaptador.
- **Por qué:** el enunciado exige que las tres versiones trabajen sobre el
  mismo grafo, las mismas acciones y los mismos costos. Con una sola
  formulación eso se cumple por construcción. Cualquier diferencia de
  métricas que aparezca es entonces de la biblioteca, no del modelado, y ese
  es el diagnóstico que pide la sección 10.

### D-32 · Métricas con un visor propio y tiempo en una ejecución aparte

- **Decisión:** `ContadorSimpleAI` implementa `event(nombre, *params)` y
  traduce los eventos de `_search` al contrato. `repetidos` no tiene evento:
  se deduce como *generados − insertados*, y los insertados salen de la
  variación del tamaño de la frontera entre dos iteraciones. El tiempo se
  mide en una segunda ejecución sin visor.
- **Alternativas:** heredar de `BaseViewer`; llamar a `_search` con una
  frontera propia instrumentada; parchear la biblioteca.
- **Por qué:** parchear está prohibido. `_search` es privada, y depender de
  su firma ataría el cuaderno a un detalle interno. `BaseViewer` convierte la
  frontera a texto en cada iteración, un costo inútil aquí. El visor es el
  mecanismo público que la biblioteca ofrece para esto. Sobre el tiempo: con
  un visor, SimpleAI llama a `fringe.sorted()` en cada iteración aunque el
  visor no use el resultado, y en UCS eso es O(n log n) por iteración. Medir
  el tiempo con visor atribuiría a la biblioteca un costo que no tiene.
- **Límite conocido:** en UCS, un reemplazo en la frontera deja el tamaño
  igual y se cuenta como repetido. Queda documentado, no oculto.
- **Validación:** el BFS de SimpleAI coincide con el de la Versión 1 en las
  cuatro métricas (249, 506, 248, 12), y su DFS coincide exactamente con
  nuestra DFS con la pila sin invertir (228 expandidos). Si la deducción de
  insertados estuviera mal, estas igualdades no se cumplirían.

### D-33 · Dos defectos de SimpleAI en búsqueda limitada, documentados y no corregidos

- **Hallazgo 1:** con `graph_search=True`, `limited_depth_first` guarda en
  `memory` todo estado extraído, de forma global. Es el defecto que la
  etapa 5 descartó para la Versión 1 (D-24). El caso de la etapa 5 no lo
  dispara, porque SimpleAI explora en orden O-S-E-N. Una búsqueda exhaustiva
  sobre rejillas abiertas de 2×3 a 4×4 no halló ningún fallo con límite
  exacto, pero sí con límites mayores. En la 2×4 abierta, de `(0,0)` a
  `(0,3)` (distancia 3), SimpleAI encuentra la meta con límite 3 y **la
  pierde con límite 4**.
- **Hallazgo 2:** `iterative_limited_depth_first` repite `while not
  solution` y no distingue corte de fracaso. Con la meta inalcanzable no
  termina. Se demostró deteniéndolo desde el visor tras |V| + 2 = 502
  ejecuciones; la Versión 1 declara el fracaso en 34.
- **Decisión:** no se corrige la biblioteca (está prohibido modificarla) ni
  se esconde el defecto. Se documenta, se mide y se evita en los
  experimentos: IDDFS de SimpleAI solo se ejecuta sobre instancias con
  solución, y DLS con límite igual a la profundidad de BFS.

---

## Etapa 9 — Versión AIMA-Python (2026-09-23)

### D-34 · Vendorización efectiva de AIMA-Python

- **Decisión:** se copian `aima/__init__.py`, `aima/search.py` y
  `aima/utils.py` desde `aimacode/aima-python`, rama `master`, commit
  `bbf6bc2` (2026-06-29), junto con su licencia MIT en `aima/LICENSE`. No se
  modifica ninguna línea. Se importan como el paquete `aima` desde la raíz
  del proyecto, que es el directorio de trabajo del kernel.
- **Por qué:** cumple D-05. El commit fijado hace reproducible la versión,
  igual que la versión fijada de SimpleAI en `requirements.txt`.

### D-35 · Instrumentación de AIMA en la subclase de `Problem`

- **Decisión:** `LaberintoAIMA(Problem)` delega en `ProblemaLaberinto` y lleva
  los contadores. `actions` cuenta expansiones, `result` cuenta nodos
  generados, y los estados distintos vistos dan los insertados; de ahí salen
  los repetidos y, en búsqueda en grafo, el tamaño de la frontera
  (*1 + insertados − expandidos*). En la DLS recursiva, la altura de la pila
  se reconstruye a partir de la secuencia de `goal_test` y `actions`.
- **Alternativas:** sustituir temporalmente `aima.search.Node` por una
  subclase contadora; envolver las funciones de búsqueda.
- **Por qué:** AIMA no expone visor ni ganchos, y sus fronteras son variables
  locales. El problema es la única interfaz pública que todas sus búsquedas
  usan. Sustituir `Node` también sería legítimo («sin alterar
  permanentemente»), pero `bidirectional_search` crea nodos centinela
  (`Node(-1)`) en cada llamada a `find_key` e inflaría la cuenta.
- **Validación:** las predicciones se cumplen. La DFS de AIMA coincide en
  las cuatro métricas con SimpleAI y con nuestra DFS sin invertir, y la UCS
  de AIMA coincide en las cuatro con la de la Versión 1. Si los contadores
  estuvieran mal, estas igualdades exactas no se darían.

### D-36 · Diferencias de AIMA documentadas

- **BFS prueba el objetivo al generar** (figura 3.11 del libro). Expande 241
  estados frente a 249. Se comprueba que 241 es la posición del padre de la
  meta en el orden de expansión de nuestra BFS. La diferencia es de
  **convención**, no de algoritmo, y por eso la Versión 1 mantiene la prueba
  al extraer que fija el enunciado.
- **DLS e IDDFS no controlan ciclos.** `recursive_dls` es búsqueda en árbol
  pura: en un grafo no dirigido recorre caminatas. Con límite 16 genera
  284 650 nodos frente a 82 de la Versión 1. Hasta la profundidad 59 el árbol
  de caminatas tiene unos 4,05 × 10¹⁹ nodos, calculados con programación
  dinámica y no ejecutando. En la instancia no se ejecutan; se comparan en el
  3×3 y, en los experimentos, solo en instancias pequeñas. A favor de AIMA:
  **sí** distingue `'cutoff'` de `None`, a diferencia de SimpleAI.
- **`bidirectional_search` es MM y devuelve solo el costo.** No hay camino ni
  acciones, así que no puede llenar el contrato; se compara el costo óptimo.
  Con `h = 0` es óptima en costo: da 12 en el grafo ponderado, donde nuestra
  bidireccional por capas, óptima en pasos, da 17. Tras las etapas 6 y 9, la
  comparación de las dos bidireccionales muestra que «bidireccional» nombra
  una familia, no un algoritmo.

---

## Etapa 10 — Pruebas de aceptación (2026-09-23)

### D-37 · Una batería sobre tres familias de instancias, con contra-pruebas

- **Decisión:** las pruebas se escriben como funciones que devuelven
  `(aprobada, detalle)` y se registran con un decorador. Un informe final las
  ejecuta todas y hace `assert` sobre el conjunto. Se aplican a 46
  instancias con semilla fija: 14 árboles, 16 con ciclos y 16 ponderados.
  `ejecutar_todas` corre los algoritmos de las tres versiones sobre cada una.
- **Alternativas:** `unittest` o `pytest`; probar solo la instancia
  individual.
- **Por qué:** el entregable es un cuaderno que debe ejecutarse de arriba
  abajo. Un informe en la propia celda es la evidencia verificable que pide
  el enunciado, sin depender de un ejecutor externo. Probar solo la instancia
  individual es insuficiente: es un árbol, y en un árbol la mitad de las
  concordancias (BFS ≤ DFS, UCS ≤ BFS) se cumplen como igualdad y **no
  pueden fallar**.
- **Contra-pruebas (D-11):**
  - cinco mutaciones de un resultado válido, cada una pensada para romper
    una sola condición, que la validación debe detectar por esa condición
    (185 detectadas);
  - la unicidad del camino, que debe dejar de cumplirse con ciclos (en 10
    instancias no se cumple);
  - las desigualdades de concordancia, que deben ser estrictas al menos una
    vez (en 11 casos DFS da un camino más largo que BFS, y en 75
    comparaciones UCS es más barata).
- **Validez separada por condición:** `condiciones_de_validez` devuelve la
  lista de condiciones incumplidas, en lugar de un único `assert`, para que un
  fallo indique **cuál** se rompió. Es la herramienta de la pregunta 11 de la
  defensa: diagnosticar una discrepancia.
- **Resultado:** 15 de 15 pruebas aprobadas y 768 resultados válidos. La
  bidireccional MM de AIMA concuerda en costo óptimo con las tres UCS en las
  46 instancias, incluidas las inalcanzables (infinito). La IDDFS de SimpleAI
  terminó en todas las instancias con solución: el defecto D-33 no se
  manifestó en estas familias, pero la cota del visor sigue puesta.

---

## Etapa 11 — Ciclos y costos (2026-09-23)

### D-38 · Las transformaciones construyen grafos nuevos y se auditan con la sección 1

- **Decisión:** `abrir_ciclos` enumera las paredes internas (pares
  contiguos sin corredor, en orden canónico), toma una muestra con
  `random.Random(semilla)` sobre la lista **ordenada** y devuelve una
  `Instancia` nueva con el grafo congelado. `paredes_internas` solo produce
  pares ortogonales dentro de la rejilla. Fuera del rango 5 %–12 % lanza
  `ValueError`.
- **Por qué:** así las cuatro propiedades exigidas se cumplen por
  construcción, y además se **comprueban** con las funciones de la
  auditoría: ortogonalidad, simetría, dominio, conectividad y ausencia de
  lazos. La comprobación de aciclicidad, que en el árbol aprobaba, debe ahora
  fallar: ese es el «ciclo comprobable». Muestrear sobre una lista ordenada,
  y no sobre un conjunto, mantiene la reproducibilidad entre procesos (D-08).
- **Medido:** 456 paredes internas; se abren 23 (5 %) y 46 (10 %), y |E| pasa
  de 499 a 522 y a 545.

### D-39 · ERROR CORREGIDO — el caso «menos pasos ≠ menor costo» se aceptaba con un criterio débil

- **Decisión de fondo:** el costo se mantiene en la arista no dirigida (D-23)
  pero se deriva de un terreno: los corredores que tocan una zona de barro,
  un rombo alrededor del punto medio del camino más corto, cuestan 9, y los
  demás cuestan 1. `construir_caso_pasos_vs_costo` busca el menor radio que
  produce el caso.
- **Qué se hizo primero:** el criterio de búsqueda era «el camino de UCS es
  distinto del de BFS y más barato».
- **Qué falló:** el `assert` posterior, que exigía que el camino barato
  tuviera más pasos, detuvo la celda. Con radio 0 (barro en una sola celda),
  UCS encontraba **otro camino de 47 pasos**, igual de corto, que esquivaba
  esa celda. El criterio aceptaba un caso que no demuestra nada: dos caminos
  distintos de igual longitud no separan «pasos» de «costo».
- **Corrección:** el criterio exige que el camino de menor costo tenga
  **estrictamente más pasos**. Con esa condición el caso encontrado es BFS
  con 47 pasos y costo 143, frente a UCS con 51 pasos y costo 51.
- **Lección:** la misma que en D-11, aplicada a la construcción de un
  ejemplo. Un criterio que acepta el caso trivial no garantiza la propiedad
  que se quiere mostrar. El `assert` redundante que lo detectó no era
  redundante.

### D-40 · Con ciclos, IDDFS explota: recorre caminos simples

- **Hallazgo:** en la instancia con 10 % de ciclos, IDDFS expande 552 374
  estados y tarda unos 5 s, frente a 425 estados de BFS. DLS con límite
  exacto expande 14 417.
- **Causa:** DLS controla repetidos solo sobre el camino actual (D-24). En
  un árbol cada estado tiene un único camino simple desde el inicio; con
  ciclos, el número de caminos simples crece de forma exponencial, y DLS
  recorre cada uno. Es el precio de la memoria O(d): no recuerda lo ya
  explorado por otra rama.
- **Consecuencia para los experimentos:** IDDFS se medirá en todos los
  árboles, pero con ciclos solo en el tamaño menor (15×15). Se informa como
  resultado, no como limitación oculta: es la respuesta cuantitativa a «¿por
  qué IDDFS repite trabajo y aun así puede ser conveniente?». Conviene cuando
  la memoria es el recurso escaso y el espacio se parece a un árbol; aquí no
  se da ninguna de las dos condiciones.

---
