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
