## E. Vecindad 2-opt y Hill Climbing

Para HC, SA (y el GA) trabajo con rutas **completas**: siempre tengo una respuesta válida y la voy mejorando. Lo primero que definí fue la **vecindad** común: el movimiento 2-opt de la sección 9, con el origen fijo en la posición 0.

**Qué hice.** Un movimiento es un par de posiciones `(i, j)` con `0 ≤ i < j ≤ n-1`, `j ≥ i+2` y `(i, j) ≠ (0, n-1)`. Quito las aristas `(route[i], route[i+1])` y `(route[j], route[j+1 mod n])` y las reconecto invirtiendo las posiciones `i+1..j`. Como `i+1 ≥ 1`, el origen nunca se mueve. El costo del movimiento lo calculo con el delta
`Δ = d(a,c) + d(b,d) − d(a,b) − d(c,d)`, que es O(1) y solo vale porque mis matrices son simétricas (las auditué).

**Por qué se excluye (0, n-1).** Esas dos aristas comparten el origen por el cierre del ciclo; invertir `1..n-1` solo recorre la misma ruta al revés. Con las demás reglas quedan exactamente `n(n-3)/2` pares: 119 para gr17, 1224 para eil51, 1274 para berlin52.

<!-- celda -->

**Pruebas que lo respaldan** (`tests/test_locales.py`):
- el número de pares válidos es `n(n-3)/2` para n = 4, 5, 6, 7, 8, 10, 14, 17 y 52, y coincide con la definición directa del enunciado;
- el delta es igual a la diferencia de costos completos en 3000 movimientos aleatorios de berlin52 (contra `tour_cost` y contra el oráculo independiente) y en **todos** los pares de burma14 y gr17, incluidos los que usan la arista de cierre;
- cada movimiento conserva la permutación y el origen, y la versión que copia no toca la ruta original;
- el sorteo de pares es uniforme (prueba estadística con n = 7);
- **2-opt ≠ swap**: con la ruta 0 1 2 3 4 5 6, el 2-opt (1,5) da `0 1 5 4 3 2 6` y el swap de las posiciones 2 y 5 da `0 1 5 3 4 2 6`; el 2-opt cambia 2 aristas y el swap 4. Solo coinciden cuando el tramo es de 2 o 3 ciudades.

Aclaro la diferencia con la mutación por inversión del GA: es la misma operación de lista, pero en HC/SA el movimiento es un candidato que se costea y se acepta con una regla, y en el GA es una perturbación aleatoria sin exigir mejora.

<!-- celda -->

### Hill Climbing (sección 10)

**Qué hice.** La variante principal recorre todo el vecindario y aplica la **mejor mejora estricta** (`Δ < 0`). Elegí que sea estricta para que termine: si aceptara empates podría oscilar entre rutas de igual costo. Cuando una pasada completa no encuentra ningún `Δ < 0`, paro con `LOCAL_OPTIMUM`.

Si el presupuesto se agota a mitad de una pasada devuelvo la ruta actual (válida, nunca peor que la inicial) con el motivo del `Budget` y **no afirmo** óptimo local. Consulto el presupuesto *antes* de cada evaluación, así que nunca me paso ni de una unidad; cada delta evaluado cuenta como una evaluación y el costo de la ruta inicial no cuenta (igual para HC y SA, declarado).

Además implementé la primera mejora (`strategy="first"`, para comparar aparte) y los **reinicios aleatorios** con un solo presupuesto global, conservando la mejor ruta global y registrando cuántos reinicios hubo y el costo de cada óptimo local. Con `keep_history=True` guardo cada mejora aplicada para la animación.

<!-- celda -->

**Pruebas de HC.**
- Si HC termina en `LOCAL_OPTIMUM`, enumero **todo** el vecindario, calculo cada costo completo con el oráculo y verifico que ninguno es menor (burma14, gr17 y eil51, ambas estrategias, 3 semillas).
- HC nunca empeora: el historial de costos es estrictamente decreciente.
- Presupuesto exacto: con `max_evals` ∈ {0, 1, 7, 100, 119, 120, 1234} las evaluaciones nunca lo superan, la ruta es válida, y si se interrumpe el motivo es `EVAL_LIMIT`.
- Una pasada completa sobre un óptimo local cuesta exactamente `n(n-3)/2` evaluaciones.
- En una subinstancia de 8 ciudades, HC con reinicios alcanza el óptimo de la fuerza bruta y ninguna ejecución baja de él.
- `trace` es monótono (evaluaciones no decrecen, mejor costo no sube) y `route_history` es coherente.

<!-- celda -->

**Resultados reales de la prueba de cordura** (30000 evaluaciones, semillas 0, 1, 2; óptimo oficial entre paréntesis):

| Instancia | HC una ruta | HC primera mejora | HC reinicios |
|---|---|---|---|
| gr17 (2085) | 2095, 2142, 2095 | 2088, 2095, 2095 | 2085, 2085, 2085 |
| burma14 (3323) | 3323, 3336, 3323 | 3336, 3336, 3323 | 3323, 3323, 3323 |
| eil51 (426) | 557, 615, 589 | 445, 544, 445 | 557, 615, 589 |

HC de una ruta terminó en `LOCAL_OPTIMUM` en gr17 (1400–1800 evaluaciones) y en burma14 (540–690). En gr17 y burma14 los reinicios hicieron 19–21 y 40–42 ascensos y bajaron al óptimo.

**Hallazgo importante.** En eil51 HC *no llega* a un óptimo local con 30000 evaluaciones: una pasada cuesta 1224 evaluaciones y desde una ruta aleatoria hacen falta muchos pasos. Por eso "HC con reinicios" hizo un solo ascenso y dio **exactamente lo mismo** que HC de una ruta. Los reinicios solo ayudan si un ascenso cabe varias veces en el presupuesto; en eil51 la primera mejora, que gasta menos por paso, llegó mucho más lejos (445 con la semilla 0).

**Respuesta a la pregunta del enunciado.** Una ruta sin cruces visibles no es necesariamente óptima. Con distancias euclidianas un cruce siempre se puede quitar con un 2-opt, así que una ruta óptima no tiene cruces; pero lo contrario es falso. Ejemplo calculado con mi código: con las primeras 8 ciudades de eil51, la ruta `0 4 3 5 6 7 2 1` no tiene cruces (lo comprobé con un test de intersección de segmentos), es un óptimo local de 2-opt de costo 141, y el óptimo por fuerza bruta es 138. En una matriz explícita (gr17, gr48, brazil58) no hay geometría que mirar y los pesos no tienen por qué cumplir la desigualdad triangular.
