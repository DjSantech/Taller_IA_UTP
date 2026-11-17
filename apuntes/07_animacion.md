### Comentario de nuestra animación (Reto 4)

Animamos **nuestra propia ejecución**, distinta de la del enunciado: 5×5 desde (0, 0), con el orden de desplazamientos **rotado 5 posiciones**. Con ese orden la búsqueda necesita 288 expansiones, frente a las 41 del orden base. El GIF muestra un **prefijo** de la traza que empieza en el evento `inicio` y llega hasta poco después del primer retroceso.

- **Rama fallida:** hasta el evento 19, el caballo avanza sin problemas. En el evento 20 se **libera (3, 0)**: desde ahí no queda ningún salto libre, así que esa llamada devuelve fracaso.
- **Dónde queda el caballo:** en **(4, 2)**, la casilla anterior del camino. El número más alto del tablero desaparece, como predijimos en el laboratorio.
- **Siguiente alternativa:** la lista de destinos del marco de (4, 2), en el orden rotado, era solo `[(3, 0)]`. Como no le queda otra alternativa, **ese marco también retrocede**. La animación muestra el retroceso en cadena hasta un marco que todavía tiene destinos sin probar, y desde ahí el caballo avanza por otra rama.

El fotograma fijo de abajo es el del primer retroceso: el aspa marca la casilla liberada y el color naranja, la casilla donde quedó el caballo.
