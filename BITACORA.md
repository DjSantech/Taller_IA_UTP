# Bitácora de decisiones — Taller 2 (TSP)

Registro breve de las decisiones de diseño, los errores cometidos y su corrección.
Cada entrada: **Decisión · Alternativas · Por qué · Consecuencia**. Los errores
corregidos llevan la marca **ERROR CORREGIDO**; son material directo para la sustentación.

---

## Etapa 0 — Estructura, entorno y datos

### D-01 · El entregable es el propio cuaderno del profesor, construido desde módulos probados
- **Decisión:** el código vive en el paquete `tsp/` (un módulo por responsabilidad, con
  pruebas en `tests/`) y `tools/construir_cuaderno.py` inserta ese mismo código en las
  celdas del cuaderno del enunciado, conservando sus secciones y su pseudocódigo.
- **Alternativas:** escribir todo directamente en celdas; entregar un cuaderno delgado que importe el paquete.
- **Por qué:** los módulos se prueban con `pytest` y se pueden desarrollar en paralelo;
  pero la entrega exige un cuaderno que se ejecute de arriba abajo con datos locales y sin
  dependencias implícitas, así que el código que se ejecuta en el cuaderno debe estar *en* el cuaderno.
- **Consecuencia:** los módulos solo pueden importar de módulos anteriores en el orden
  `datos → modelo → mst → astar → rbfs → vecindad → hc → sa → ga → experimentos`.

### D-02 · Primer commit con el enunciado intacto
- El commit `e10a4f7` contiene el cuaderno exactamente como lo entregó el profesor.
  Hace verificable en el historial qué es del docente y qué es propio.

### D-03 · Entorno virtual fuera de OneDrive
- `C:\Users\santi\venvs\ia-taller2`, con versiones fijadas en `requirements.txt`
  (misma razón que D-03 del Taller 1: OneDrive sincronizaría miles de archivos y puede corromper el entorno).

### D-04 · Misma repo de GitHub, rama independiente `taller-2`
- **Decisión:** rama huérfana `taller-2` del repositorio `DjSantech/Taller_IA_UTP`
  (el Primer Taller vive en `main`). No se hace `push` sin orden explícita.
- **Por qué:** el repo ya existe y se pidió usarlo, pero mezclar en `main` los archivos
  de los dos talleres ensuciaría ambos historiales.

### D-05 · Identificadores en inglés, explicaciones en español
- El enunciado lo pide expresamente («nombres sugeridos … en inglés; explicaciones y conclusiones en español»).
  El Taller 1 usó identificadores en español; aquí se sigue la regla nueva.

### D-06 · Ciudades por posición, identificadores aparte
- **Decisión:** todos los algoritmos trabajan con posiciones `0..n-1`; `TSPInstance.node_ids`
  guarda la correspondencia con los identificadores reales del archivo.
- **Por qué:** el enunciado (§3.1) prohíbe suponer que el nodo `i` está en la posición `i-1`.
- **Origen fijo:** posición 0 (el identificador menor). Un parámetro `origin` permite cambiarlo
  para la prueba de invarianza del costo óptimo.

### D-07 · Semillas enteras y generadores independientes
- **Decisión:** `make_rngs(seed)` devuelve dos `random.Random` sembrados con enteros
  (`1000003*seed+1` para la ruta inicial y `+2` para las decisiones del algoritmo).
- **Alternativas:** sembrar con cadenas o con `hash(...)`; un único generador compartido.
- **Por qué:** (a) el enunciado exige generadores independientes para que cambiar un algoritmo
  no altere las rutas iniciales; (b) la lección de D-08 del Taller 1: lo que depende de `hash`
  puede variar entre procesos (`PYTHONHASHSEED`), un entero no.

### D-08 · Memoria incremental con `tracemalloc`
- **Decisión:** `MemoryMeter` mide la memoria *incremental* atribuible al solver con
  `tracemalloc`, descontando la base previa.
- **Límite declarado:** solo cuenta asignaciones de Python; no es la memoria del proceso
  completo (§14.1 exige distinguirlas y declarar la herramienta).

### D-09 · ERROR CORREGIDO — `gr48` numerado 0..47 por la biblioteca, 1..48 por los archivos
- **Qué se hizo primero:** `node_ids = sorted(problem.get_nodes())` para todas las instancias.
- **Qué falló:** la prueba que lee `gr48.opt.tour` lanzó `KeyError: 48`. Para instancias
  `EXPLICIT` sin coordenadas, `tsplib95` numera los nodos de 0 a n-1 (`gr48`, `brazil58`,
  `gr17`), mientras que el archivo `.opt.tour` y la convención TSPLIB usan 1 a n.
- **Por qué importa:** si la prueba no hubiera existido, las rutas de salida habrían quedado
  desplazadas en uno, y cualquier comparación con una ruta oficial habría sido absurda.
  Es exactamente la advertencia del enunciado sobre no presuponer la numeración.
- **Corrección:** se separan las *claves de `get_weight`* (internas) de los *identificadores reales*
  (`posición+1` en las explícitas). Tras el cambio, el tour óptimo oficial de `gr48` cuesta
  **5046**, el valor publicado: eso confirma que la matriz está bien leída.
- **Lección:** verificar los datos contra una ruta oficial *conocida* detecta errores de
  lectura que ninguna auditoría de simetría o diagonal puede ver.

### D-10 · Auditoría de datos
- Para las 7 instancias: dimensión, simetría, diagonal cero y pesos no negativos
  (`_audit_matrix`); fórmulas EUC_2D y ATT recalculadas por separado y comparadas contra la
  biblioteca en **todos** los pares de `berlin52` y `att48`; costo de los `.opt.tour`
  oficiales (att48, berlin52, gr48) verificado contra los óptimos publicados.
