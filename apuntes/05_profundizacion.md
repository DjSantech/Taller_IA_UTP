### Implementación C: dónde está y qué muestra la celda siguiente

La ordenación y la profundización iterativa ya están en el código de la implementación B (`AlphaBetaImprovedAgent` y `_search_order_moves`, en `chess_ai/search.py`), porque comparten el núcleo de alfa-beta. El diseño está explicado arriba, en «Alfa-beta mejorado». Aquí lo ejecutamos con plazo y mostramos cada iteración:

- **Respaldo:** antes de iterar se guarda una jugada legal (la primera según la ordenación). Si el plazo vence antes de que termine la profundidad 1, el agente devuelve esa jugada con `score=None` y `completed_depth=0`. Nunca devuelve `None` en una posición no terminal.
- **Última iteración completa:** el plazo se consulta al entrar a cada nodo. Si vence, `SearchTimeout` sube por la recursión y los `finally` deshacen cada `push`; la iteración parcial se **descarta** (fila «NO» de la tabla) y se devuelve la jugada y el valor de la última iteración terminada. `completed_depth` es esa profundidad, no la que se alcanzó a empezar.
- **Contadores:** los nodos del `SearchStats` suman todas las iteraciones, incluida la abortada, porque es el trabajo realmente gastado.

Los tiempos y la profundidad alcanzada dependen de la máquina y de su carga en el momento de ejecutar. Por eso la celda solo **afirma** invariantes: la jugada es legal, el tablero queda intacto, `completed_depth` coincide con las iteraciones terminadas y, sin plazo, el valor es el de alfa-beta a esa profundidad.
