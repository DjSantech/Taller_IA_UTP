### C.1. Microcaso manual (sección 6.2): lo que calculé antes de programar

Antes de escribir A* y RBFS resolví a mano el microcaso de cinco ciudades. Lo hice por una razón de método: con 24 rutas todo se puede verificar con lápiz, y esos números pasan a ser el oráculo de mis implementaciones. Si el programa no reproduce exactamente mis $g$, $h$ y $f$, hay un error en el programa o en mi papel, y es mejor descubrirlo aquí que con 48 ciudades.

<!-- celda -->

**Heurística de la raíz.** Con origen $A$ y pendientes $\{B,C,D,E\}$: $\operatorname{MST}=7$ (aristas $B$-$C$=2, $D$-$E$=2, $C$-$D$=3), la conexión mínima desde $A$ cuesta 3 (a $E$) y la mínima hacia $A$ también 3 (desde $E$). Entonces $h=13$ y $f=13$. Aquí las dos conexiones eligen la misma ciudad, como advierte el enunciado: la cota sigue siendo válida, solo menos ajustada (el óptimo es 14).

**Hijos de la raíz** (cada $h$ usa los pendientes sin la ciudad nueva):

| hijo | $g$ | $U$ | MST($U$) | mín $d(v,u)$ | mín $d(u,A)$ | $h$ | $f$ |
|---|---|---|---|---|---|---|---|
| B | 4 | {C,D,E} | 5 | 2 | 3 | 10 | 14 |
| C | 6 | {B,D,E} | 7 | 2 | 3 | 12 | 18 |
| D | 7 | {B,C,E} | 6 | 2 | 3 | 11 | 18 |
| E | 3 | {B,C,D} | 5 | 2 | 4 | 11 | 14 |

El prefijo $A\to B$ da $h=10$ y $f=14$, igual que el enunciado. La prueba `test_microcaso_hijos_de_la_raiz` compara estos números con los que calcula el código.

<!-- celda -->

**Primer empate y regla determinista.** $B$ y $E$ empatan con $f=14$. Ordeno la frontera por la tupla $(f,\;h,\;\text{orden de inserción})$: primero menor $f$; a igual $f$, menor $h$ (equivale a mayor $g$, es decir, el nodo más avanzado, y los nodos cerrados con $h=0$ salen antes); y si aún hay empate, el generado primero. Los sucesores se generan por posición de ciudad ascendente, de modo que la regla es reproducible. Aplicada: $B$ ($h=10$) antes que $E$ ($h=11$). El desempate cambia cuánto se explora, no el costo final.

**Cota con uno y con cero pendientes.** Con un pendiente $u$ la fórmula da $d(v,u)+d(u,A)$, exactamente lo que falta (en $A\!-\!B\!-\!C\!-\!D$: $h=2+3=5$, $f=9+5=14$). Con ninguno y sin cerrar da $d(v,A)$ (en $A\!-\!B\!-\!C\!-\!D\!-\!E$: $h=3$). Ese nodo **no** es meta: la meta es el nodo cerrado, con $g=11+3=14$ y $h=0$. Si devolviera el nodo sin cobrar el regreso, respondería 11 en lugar de 14.

<!-- celda -->

**Traza de A\*** (salida real del programa con registro de expansiones):

| # | nodo expandido | $g$ | $h$ | $f$ |
|---|---|---|---|---|
| 1 | A | 0 | 13 | 13 |
| 2 | A-B | 4 | 10 | 14 |
| 3 | A-B-C | 6 | 8 | 14 |
| 4 | A-B-C-D | 9 | 5 | 14 |
| 5 | A-B-C-D-E | 11 | 3 | 14 |

Después sale el cierre con $g=14$. Fueron 5 expansiones, 11 nodos generados, 10 cálculos de MST y una frontera máxima de 7. La enumeración exhaustiva da 14 con exactamente 2 rutas óptimas ($A\!-\!B\!-\!C\!-\!D\!-\!E$ y su reversa). Con $h=0$ el mismo caso cuesta 33 expansiones.

**Primeros límites de RBFS.** Los hijos de $A$ valen $B=14,\,E=14,\,D=18,\,C=18$; el mejor es $B$ y su alternativa es $E$ (14), así que $\text{RBFS}(B)$ recibe límite $\min(\infty,14)=14$. Dentro de $B$, el mejor es $C$ (14) con alternativa $D$ (18): límite $\min(14,18)=14$. Y así hasta el cierre. La secuencia de límites es $\infty\to14\to14\to14\to14$: bajada directa por la rama óptima, 6 llamadas y 0 regeneraciones. Para ver un retroceso real uso el caso de 4 ciudades de las trazas de RBFS (apunte 07).

<!-- celda -->

**Swap contra 2-opt sobre una misma ruta.** Tomo $R=[A,C,B,E,D]$, de costo $6+2+6+2+7=23$.

- *Swap* de las posiciones 1 y 3 (intercambia $C$ y $E$): $[A,E,B,C,D]$, costo 21. Rompe cuatro aristas.
- *2-opt* con $i=1,\,j=3$: $a=C,\,b=B,\,c=E,\,d=D$. Invierte el segmento de la posición 2 a la 3: $[A,C,E,B,D]$. $\Delta=d(C,E)+d(B,D)-d(C,B)-d(E,D)=4+5-2-2=+5$, y el costo recalculado es 28 $=23+5$. Rompe solo dos aristas.
- *2-opt* con $i=2,\,j=4$ (aquí $d=A$, por el cierre): $\Delta=5+3-6-7=-5$, ruta $[A,C,B,D,E]$ de costo 18.

La diferencia: el swap intercambia dos ciudades y deshace hasta cuatro aristas; el 2-opt reemplaza dos aristas invirtiendo el tramo entre ellas, y conserva intactos los tramos. La mutación por inversión del GA es esta misma operación con posiciones aleatorias y sin comprobar si mejora.

**Qué prueba lo respalda:** `test_microcaso_hijos_de_la_raiz`, `test_microcaso_optimo_por_enumeracion_y_por_los_solvers`, `test_microcaso_desempate_determinista_elige_B_antes_que_E`, `test_heuristica_casos_de_la_formula` y `test_heuristica_raiz_con_la_misma_ciudad_en_ambas_conexiones` (todas en `tests/test_exactos.py`). Guía de estudio en `estudio/Etapa3_teoria.txt`.
