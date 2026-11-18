### Las tres salidas de búsqueda y mi prueba adicional

La celda anterior muestra las tres salidas:

| Salida | Caso | Por qué termina así |
|---|---|---|
| **éxito** | 5×5 desde (0, 0) | Hay recorrido abierto: 41 expansiones. |
| **fracaso** | 3×3 desde (0, 0) | El centro (1, 1) es inalcanzable para el caballo; el árbol se agota en 15 expansiones. |
| **límite** | 5×5 con `presupuesto=10` | Se gastan las 10 expansiones con destinos pendientes; se desenrolla hasta la raíz y el último evento es `("límite", 0, 0)`. |

Además se prueban el 1×1 cerrado (fracaso por falta de salto de regreso) y un circuito cerrado real en 6×6.

**Prueba adicional: `reproducir_traza`.** Reconstruye el camino aplicando la traza evento por evento. En cada paso comprueba cuatro cosas:
- que cada avance sea un salto de caballo a una casilla libre;
- que cada retroceso retire **la última** casilla del camino;
- que `visitadas == set(camino)` se cumpla después de cada evento;
- que el camino reconstruido coincida con el devuelto (en éxito) o sea `[inicio]` (en fracaso o límite).

También verifica `expansiones == avances + 1`.

**Qué error habría detectado:** si al retroceder se olvida `visitadas.remove(destino)`, el camino se acorta, pero la casilla sigue marcada. En ese caso:
- la comprobación `visitadas == set(camino)` falla en el primer retroceso;
- además, la búsqueda nunca vuelve a esa casilla y en 5×5 terminaría en fracaso o con otro camino.

Las pruebas del profesor solo miran el resultado final. Esta revisa **cada paso** de la restauración del estado.

**Validación externa:** mi traza del 5×5 desde (0, 0) con el orden base es **idéntica, evento por evento**, a `TRAZA_DEMO` del enunciado (58 eventos).
