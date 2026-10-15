### 3.A Lectura de datos, fichas y auditoría

**Qué hice.** `load_instance` lee el archivo con `tsplib95`, reconstruye la matriz simétrica `D` y la audita. Trabajo siempre con **posiciones** `0..n−1` y guardo aparte la correspondencia `node_ids` con los identificadores reales del archivo, tal como pide la sección 3.1.

**Auditoría automática (pasa en las 7 instancias):** la dimensión declarada coincide con los nodos leídos, la matriz es cuadrada, simétrica, con diagonal cero y sin pesos negativos.

**Fichas de instancia** (valores producidos por mi lector; el óptimo es el oficial de TSP-BEST):

| Instancia | n | Tipo de pesos | ¿Coordenadas? | Óptimo oficial | Peso mínimo / máximo | D(1,2), D(1,3), D(2,3) |
|---|---:|---|---|---:|---|---|
| att48 | 48 | ATT | sí | 10628 | 42 / 2662 | 1495, 381, 1135 |
| berlin52 | 52 | EUC_2D | sí | 7542 | 15 / 1716 | 666, 281, 649 |
| brazil58 | 58 | EXPLICIT | no | 25395 | 72 / 8700 | 2635, 2713, 314 |
| gr48 | 48 | EXPLICIT | no | 5046 | 21 / 1083 | 593, 409, 258 |
| gr17 | 17 | EXPLICIT | no | 2085 | 27 / 745 | 633, 257, 390 |
| burma14 | 14 | GEO | sí | 3323 | 19 / 1261 | 153, 510, 422 |
| eil51 | 51 | EUC_2D | sí | 426 | 2 / 86 | 12, 19, 15 |

Para `brazil58` y `gr48` no hay coordenadas: los pesos salen de la matriz del archivo y **no** los reemplazo por distancias euclidianas. Para dibujarlas usaré un mapa de calor y una disposición circular rotulada como esquemática.

<!-- celda -->

### 3.B Las dos reglas de distancia, calculadas a mano (ejercicio de la sección 3.2)

**berlin52 (EUC_2D), ciudades 1 y 2.** Ciudad 1 = (565, 575), ciudad 2 = (25, 185). Δx = 540, Δy = 390.
r = √(540² + 390²) = √443700 = 666.108…  →  d = ⌊666.108 + 0.5⌋ = **666**. El lector da 666. ✔

**att48 (ATT), ciudades 1 y 2.** Ciudad 1 = (6734, 1453), ciudad 2 = (2233, 10). Δx = 4501, Δy = 1443.
r = √((4501² + 1443²)/10) = √(22341250/10) = √2234125 = 1494.699…
t = ⌊1494.699 + 0.5⌋ = 1495. Como t < r es falso (1495 > 1494.699), d = t = **1495**. El lector da 1495. ✔

La regla ATT es *pseudoeuclidiana*: divide por 10 antes de la raíz, y por eso **no es lo mismo** que EUC_2D: en att48 los **1128 de 1128 pares** de ciudades tienen un peso ATT distinto del que daría EUC_2D. Además implementé las dos fórmulas por separado en las pruebas y las comparé contra el lector en **todos los pares** de att48 y berlin52: coinciden en todos.

<!-- celda -->

### 3.C Por qué una ruta «mejor que el óptimo oficial» obliga a auditar primero

El óptimo oficial C\* es el mínimo demostrado del problema. Si obtengo un costo menor, lo más probable es un error mío, no un récord mundial. Comprobé tres errores típicos usando las **rutas óptimas oficiales** (`.opt.tour`), cuyo costo correcto sí conozco:

| Ruta óptima oficial de | Costo cerrado (correcto) | Si **olvido el regreso al origen** | Diferencia con C\* |
|---|---:|---:|---|
| att48 | 10628 | 10481 | **−1,4 %** (parece mejor que el óptimo) |
| berlin52 | 7542 | 7496 | **−0,6 %** |
| gr48 | 5046 | 4966 | **−1,6 %** |

Es exactamente el error que haría un A\* que devuelva el primer nodo con pendientes vacíos sin cobrar el retorno (pregunta 4 de la discusión). Los otros dos candidatos son: una **distancia mal calculada** (con la euclidiana sin redondear la misma ruta de att48 cuesta 33 523,71, no 10628, lo que delataría el error) y una **ruta inválida** (con una ciudad duplicada y otra omitida, el costo deja de significar algo). Por eso mi contrato de salida exige tres comprobaciones antes de aceptar un costo: la ruta es una permutación válida, el costo incluye el cierre y el gap no es negativo; un gap negativo detiene la ejecución (`AuditError`).

**Comprobación con rutas oficiales.** Verifiqué que los `.opt.tour` oficiales de att48, berlin52 y gr48 son rutas válidas y que su costo con mi lector es **exactamente** 10628, 7542 y 5046. Los uso solo para verificar costos, nunca como ruta inicial.

<!-- celda -->

### 3.D Un error real que encontré y corregí

Al leer `gr48.opt.tour` la prueba falló con `KeyError: 48`. Causa: para instancias `EXPLICIT` sin coordenadas, `tsplib95` numera los nodos de **0 a n−1**, pero el archivo de la ruta y la convención TSPLIB los numeran de **1 a n**. Si no hubiera existido esa prueba, mis rutas de `gr48`, `brazil58` y `gr17` habrían salido desplazadas en uno. Corrección: separé la clave que acepta `get_weight` (interna) del identificador real (posición + 1). Tras el cambio, la ruta oficial de gr48 cuesta 5046, el valor publicado. Esto confirma que la matriz está bien leída, algo que la auditoría de simetría o diagonal **no** habría detectado. (Registrado como D-09 en la bitácora.)
