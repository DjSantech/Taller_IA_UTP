### 1.A Lectura crítica de TSP Solve (actividad de la sección 1)

Leí las cuatro páginas del sitio (inicio, A\*, Hill Climbing y RBFS, consultadas el 15 de octubre de 2026) con una pregunta en mente: **¿qué hace exactamente el código, y qué dice el texto que hace?** Estas son las diferencias que encontré; las separo en las dos que pide el enunciado y otras que aparecieron.

**1. ¿Qué código realiza swap, y qué cambiaría para implementar 2-opt?**

El texto de la página de Hill Climbing dice que un vecino se obtiene «cambiando las posiciones de dos nodos (o borrando dos aristas y añadiendo dos)» y lo llama «vecinos 2-opt». Esas son **dos operaciones distintas** que la página trata como una sola. El código MATLAB hace la primera:

```matlab
tempNode = newTour(p1);
newTour(p1) = curState.node(p2);
newTour(p2) = tempNode;
```

Eso es un **swap**: intercambia dos ciudades y deja el resto en su sitio. Un swap de las posiciones `p1` y `p2` toca hasta **4 aristas** (las dos vecinas de cada ciudad) y, si las posiciones son adyacentes, solo 3. El 2-opt elimina exactamente **2 aristas** y reconecta invirtiendo el tramo intermedio. Para pasar de uno a otro habría que sustituir esas tres líneas por la inversión de un segmento, `newTour(p1+1:p2) = flip(newTour(p1+1:p2))`, y además cambiar el rango de los índices: el código recorre `p1 = 1:n-1` y `p2 = p1+1:n`, es decir **n(n−1)/2 = 1128** candidatos para n = 48, mientras que los pares válidos de 2-opt son **n(n−3)/2 = 1080** (se excluyen las aristas adyacentes). Una consecuencia práctica: con 2-opt el cambio de costo se calcula con solo 4 pesos (`Δ = d(a,c)+d(b,d)−d(a,b)−d(c,d)`), mientras que el código de la página vuelve a calcular el costo completo de cada candidato.

**2. ¿Qué información necesita la clave de un estado de A\*?**

En la versión de grafo la página comprueba los repetidos comparando solo el **nombre de la ciudad**: `ismember(nodelist(i).name, {closed.name})`. Es decir, su clave de estado es *únicamente la última ciudad*. Eso es incorrecto en el TSP porque dos rutas parciales pueden terminar en la misma ciudad habiendo visitado **conjuntos distintos**: sus futuros son diferentes, y al descartar una de ellas podría perderse la ruta óptima. La clave correcta es `(última ciudad, conjunto de pendientes, ciclo cerrado)`, con el mismo origen fijo. En mi implementación (etapa 6) esa afirmación no queda como opinión: construyo un contraejemplo concreto y lo verifico con una prueba.

**Otras diferencias entre lo que la página dice y lo que hace**

| Hallazgo | Qué dice la página | Qué hace el código | Por qué importa |
|---|---|---|---|
| Ruta inicial de HC | «comienza con una solución aleatoria» | usa el orden de los nodos del grafo (`table2cell(G.Nodes)`) | el resultado reportado es de una sola ruta inicial fija, no de una aleatoria; no se puede hablar de variabilidad |
| Hill Climbing acepta mejoras | «mejor vecino» | actualiza `curState` en cuanto encuentra una mejora dentro del barrido (primera mejora, no mejor mejora) | es otra variante; compararla con «mejor mejora» exige decirlo |
| Complejidad de HC | tiempo `O(∞)`, espacio `O(b)` | cada candidato recalcula el costo completo en O(n); un barrido cuesta O(n³) | `O(∞)` no es una cota; la memoria real es O(n), no O(b) |
| Término `- depth` | no aparece en el pseudocódigo | `node.cost = h + g - depth` en el árbol y en RBFS | el valor de `f` deja de ser el largo de la ruta; el costo reportado es menor que el real en aproximadamente n−1 |
| «Pathmax» en RBFS | `suc.cost ← max(suc.g+suc.h, currentNode.cost)` | se ejecuta sobre una copia (`suc = nodelist(i)`) que nunca se guarda | el `max` no tiene efecto; justo ese `max` es lo que mantiene los valores respaldados de `f` monótonos |
| A\* de grafo | «óptimo o casi óptimo» | solo 8 de las 48 ciudades de inicio dan 10628; las otras dan entre 10648 y 10795 | un A\* correctamente formulado devuelve el mismo costo desde cualquier origen |

**Qué NO afirmo.** Los resultados no óptimos de esa página **no demuestran** que A\* pierda la optimalidad: demuestran que *esa implementación* (clave de estado incompleta, `- depth`) no es un A\* correctamente formulado. Y no uso sus tiempos (166 s, 161 s, horas…) como objetivos de rendimiento: dependen del lenguaje, del hardware y de la implementación.

**Cómo lo uso.** Estas observaciones definen cuatro pruebas de mi propio trabajo: (i) el contraejemplo de la clave de estado (etapa 6); (ii) la invarianza del costo óptimo al cambiar el origen (etapa 6); (iii) 2-opt frente a swap con un ejemplo concreto (etapa 8); (iv) la traza de RBFS que muestra por qué se necesita el `max` (etapa 7).
