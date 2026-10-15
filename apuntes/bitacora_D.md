## Experimentos y gráficas (agente D)

### E-01 · Configuración congelada en un diccionario, con marcador de calibración
- **Decisión:** `FROZEN` guarda semillas, $k$, presupuestos y límites; SA y GA llevan `"calibrated": False` hasta que el coordinador fija los valores.
- **Alternativas:** constantes sueltas en las celdas; valores por omisión silenciosos.
- **Por qué:** el enunciado pide fijar la configuración antes de la evaluación principal. `assert_frozen` se niega a continuar si siguen provisionales.
- **Consecuencia:** una corrida final con parámetros sin calibrar es imposible por accidente.

### E-02 · Solvers por importación perezosa e inyectables
- **Decisión:** `_solver(clave, solvers)` busca primero un solver inyectado, luego el nombre ya definido en el espacio global (cuaderno) y por último el módulo `tsp.*`.
- **Alternativas:** `import` al principio del módulo.
- **Por qué:** los solvers se escribieron en paralelo; así el protocolo se probó con solvers falsos antes de que existieran los reales, y el módulo sigue funcionando al concatenarse en el cuaderno.
- **Consecuencia:** el protocolo tiene pruebas que no dependen de los algoritmos, y pruebas de integración que se omiten si falta un módulo.

### E-03 · El cronómetro envuelve todo el método; la calibración de SA se cuenta
- **Decisión:** `elapsed_seconds` es el `perf_counter` total de `run_one`. En SA, las evaluaciones y el tiempo de `calibrate_t0` se restan del presupuesto, se suman a `candidate_evaluations` y desplazan la traza.
- **Alternativas:** usar el tiempo interno del solver; dejar la calibración gratis.
- **Por qué:** §14.1 exige registrar la calibración y no excluir sin documentar la ruta inicial; sin esto SA tendría ventaja oculta sobre HC.
- **Consecuencia:** las curvas de HC y SA son comparables en el eje de evaluaciones y de tiempo.

### E-04 · Certificado del subproblema independiente de A*/RBFS
- **Decisión:** para $k\le 10$ el óptimo también se calcula con Held-Karp; si dos certificados chocan, `AuditError`.
- **Alternativas:** confiar solo en A*/RBFS.
- **Por qué:** un error compartido en la heurística MST haría que A* y RBFS coincidieran en un valor equivocado; un método independiente lo delata.
- **Consecuencia:** el "óptimo certificado" de la tabla de subinstancias indica su fuente.

### E-05 · Resultados guardados en CSV (planos) y JSON (completos)
- **Decisión:** `save_rows_csv` guarda una fila por ejecución; `save_results_json` guarda además `trace` y `extras`.
- **Por qué:** el CSV no contiene las curvas, pero las gráficas de convergencia, SA y GA las necesitan; ambas salidas son registros, no números a mano.
- **Consecuencia:** `summarize` acepta tanto objetos como filas del CSV y da el mismo resultado (hay una prueba).

### E-06 · Paralelismo opcional, apagado por omisión
- **Decisión:** `ProcessPoolExecutor` con `pool.map` (orden determinista), pero `workers=1` por omisión.
- **Por qué:** con varios procesos el tiempo medido se infla. Los solvers inyectados no se pueden serializar, por eso con `workers>1` se rechazan.
- **Consecuencia:** la corrida final de tiempos debe ir en serie.

### E-07 · Curvas de convergencia como función escalonada, con tramo conservado diferenciado
- **Decisión:** cada traza se evalúa con `searchsorted` en una rejilla común (valor vigente, sin interpolar); el trazo es discontinuo cuando menos de la mitad de las semillas sigue ejecutando.
- **Alternativas:** interpolación lineal; extender sin marcar.
- **Por qué:** §11.1 solo permite extender una curva constante si se identifica como conservación.

### E-08 · Memoria de los métodos locales no medida
- **Decisión:** si el solver no reporta memoria (`peak_memory == 0`), las tablas muestran "no medida" y no `0 B`.
- **Por qué:** `tracemalloc` ralentiza mucho y distorsionaría el tiempo de HC/SA/GA; el interés de la memoria está en A* vs RBFS. Escribir `0 B` sería presentar como medición algo que no se midió.

### ERROR CORREGIDO · La prueba de invarianza del origen no detectaba nada
- **Qué pasó:** escribí un solver falso que cambiaba el costo al usar otro origen para comprobar que `run_scale_a` lanza `AuditError`; la prueba falló con "DID NOT RAISE".
- **Diagnóstico:** el falso solo intercambiaba dos ciudades vecinas y en `gr17[k=6]` hay 8 rutas óptimas empatadas: la ruta "dañada" seguía costando lo mismo, así que la prueba comprobaba algo que no ocurría.
- **Corrección:** el falso intercambia pares de ciudades hasta que el costo realmente cambia.
- **Lección:** una prueba que debe fallar tiene que verificar primero que la entrada es de verdad mala; con empates, "cambiar la ruta" no es "cambiar el costo".

### ERROR CORREGIDO · Comparar trazas con sus tiempos
- **Qué pasó:** la prueba de reproducibilidad de SA falló aunque costo y ruta coincidían.
- **Diagnóstico:** la traza incluye segundos reales (y el desplazamiento por el tiempo de calibración), que nunca son idénticos entre corridas.
- **Corrección:** la prueba compara (evaluaciones, costo) y no los segundos.
- **Lección:** la reproducibilidad se exige en lo determinista (semilla, rutas, costos, evaluaciones); el tiempo es una medición y varía.
