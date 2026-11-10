### Nuestra evaluación común E(s) (sección 5)

Usamos la forma propuesta, $E(s)=w_mM(s)+w_pP(s)+w_kK(s)+w_aA(s)$, en centipeones y **siempre desde blancas**: cada característica es «valor de blancas − valor de negras», así que un número positivo es bueno para blancas en cualquier nodo y en cualquier partida (bitácora D-06 y D-11). El código está en la celda siguiente (`chess_ai/evaluation.py`); su docstring tiene la tabla completa.

| Característica | Definición | Escala típica | Costo | Qué decisión pretende inducir |
|---|---|---|---|---|
| $M$ material | P = 1, C = 3,2, A = 3,3, T = 5, D = 9 (en peones) | −39 … +39 | O(1) con bitboards | no regalar piezas; cambiar cuando se va ganando |
| $P$ peones | pasados (1 + avance/6) − doblados − aislados | ≈ −6 … 6 | O(peones), máscaras precalculadas | crear y empujar pasados; evitar peones débiles |
| $K$ rey | (escudo de peones − casillas de la zona del rey atacadas) × fase | ≈ −9 … 3 | 9 consultas de ataque | enrocar y no abrir el rey en el medio juego; en finales la fase → 0 y el término se apaga |
| $A$ actividad | casillas atacadas por C, A, T, D que no ocupan piezas propias | ≈ −40 … 40 | O(piezas) | desarrollar piezas y abrir líneas |

**Pesos iniciales** $E_0 = (100, 15, 10, 4)$ centipeones por unidad. Ningún término posicional pesa más que un peón por unidad, porque «no regalar material» debe dominar. Los pesos ajustados $E^*$ salen de la búsqueda local de la sección 7C.

**Terminales antes que E.** Ninguna búsqueda consulta $E$ en un estado terminal: primero se resuelve el resultado exacto (`search_outcome`). Una victoria a `ply` jugadas de la raíz vale $\pm(100\,000 - \text{ply})$, las tablas valen 0 y $E$ se recorta a ±10 000, así que **cualquier mate domina a cualquier estimación**. Restar el ply hace preferir el mate más corto. No usamos tabla de transposición; si se usara, ese valor de mate tendría que guardarse como «distancia desde el nodo» y convertirse de vuelta al leerlo (D-07).

**Perspectiva de negras.** Como $E$ está desde blancas, cuando deciden negras los agentes **minimizan** $E$ (equivale a maximizar $-E$). La celda que sigue al código lo comprueba en cuatro posiciones: al reflejar el tablero y cambiar los colores, $E$ cambia de signo exactamente.
