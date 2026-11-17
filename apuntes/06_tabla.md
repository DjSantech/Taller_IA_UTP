### Lectura de la comparación (Reto 3.4)

Todas las filas usan el **mismo presupuesto (50 000)** y el **mismo orden de desempate**. Los números se reproducen exactamente: la búsqueda no tiene azar.

- **5×5 desde (0, 0):**
  - el orden fijo encuentra el recorrido en 41 expansiones, con 16 retrocesos;
  - Warnsdorff lo encuentra en 25 expansiones, **sin retroceder ni una vez**: va directo.
- **6×6 desde (0, 0), orden base:** el orden fijo **agota el presupuesto (límite)**; Warnsdorff termina en 36 expansiones, también sin retrocesos.
- **El orden importa muchísimo:** en 5×5 desde (0, 0) con estrategia fija, según la rotación del orden, se necesitan entre 41 y 14 385 expansiones.

**Por qué funciona Warnsdorff:** las casillas con pocas salidas son las que se quedan aisladas si se dejan para el final. Visitarlas primero evita los callejones sin salida que obligan a retroceder.

**Lo que Warnsdorff no garantiza:**
- **Que no haya que retroceder:** es una regla de orden, no un algoritmo nuevo. Por eso se mantiene el retroceso: en el modo cerrado desde (0, 0) en 6×6, Warnsdorff también se queda sin presupuesto, porque la regla no tiene en cuenta el salto de regreso.
- **Correspondencia exacta entre expansiones y casillas:** el caso de éxito sin retrocesos usa exactamente `n²` expansiones, una por casilla; en cuanto hay retrocesos, se necesitan más.

> **Caso asignado:** cuando el docente asigne tablero, inicio y rotación, se cambian `ASIGNADO_N`, `ASIGNADO_INICIO` y `ASIGNADO_ROTACION` en la celda anterior y se vuelve a ejecutar. La tabla se actualiza sola.
