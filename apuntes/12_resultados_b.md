### 14.D Lectura de la Escala B (instancias completas)

**1. Los exactos no terminan, como se esperaba, y la causa es distinta para cada uno.** En las cuatro instancias, A\* y RBFS se detienen por el límite de **tiempo** (30 s) sin ruta ni certificado; ninguno llega a los límites de expansiones ni de memoria. Lo que cambia es *qué* quedó acumulado:

| Instancia | Nodos en la frontera de A\* al parar | Memoria de A\* | Memoria de RBFS | Regeneraciones de RBFS |
|---|---:|---|---|---:|
| att48 | ≈ 70 mil | ≈ 28 MiB | ≈ 0,1 MiB | ≈ 1400 |
| berlin52 | ≈ 59 mil | ≈ 24 MiB | ≈ 0,1 MiB | ≈ 1050 |
| brazil58 | ≈ 56 mil | ≈ 23 MiB | ≈ 0,1 MiB | ≈ 890 |
| gr48 | ≈ 71 mil | ≈ 29 MiB | ≈ 0,1 MiB | ≈ 1370 |

(Cifras de una ejecución; dependen de la velocidad del equipo, por eso las redondeo.) A\* mantiene decenas de miles de nodos en su frontera y su memoria crece sin parar: aun suponiendo un crecimiento solo lineal (y la frontera crece más rápido), el límite de 256 MiB se habría alcanzado en unos 5 minutos. RBFS usa unos 100 KiB, pero tras 30 s tampoco ha terminado y ha regenerado ya del orden de mil subárboles (el registro de auditoría de regeneraciones es lo único que ocupa memoria adicional y está incluido en esa cifra). **Esta es la respuesta empírica a la pregunta central en su extremo exacto:** A\* convierte tiempo en memoria; RBFS convierte memoria en recomputación; ninguno termina en 48 ciudades. No se penaliza si se documenta (sección 17 del enunciado).

**2. Calidad de los aproximados (10 semillas, 30000 evaluaciones, gap sobre el óptimo oficial).**

| Instancia | HC una ruta | HC con reinicios | SA | GA básico |
|---|---|---|---|---|
| att48 (10628) | 22,35 % | 22,35 % | **2,13 %** | 4,70 % |
| berlin52 (7542) | 43,37 % | 43,37 % | **6,23 %** | 10,88 % |
| brazil58 (25395) | 75,60 % | 75,60 % | **1,08 %** | 4,87 % |
| gr48 (5046) | 20,06 % | 20,06 % | **2,63 %** | 7,03 % |

(Medianas del gap. Las tablas completas por instancia, con mejor costo, repeticiones válidas, tiempo y motivo de parada, están arriba; las 10 ejecuciones de cada método son válidas.)

**Dispersión.** SA tiene el menor gap mediano pero una dispersión no pequeña: por ejemplo en att48 va de 0,19 % a 7,35 % y en brazil58 de 0 % a 7,28 %. Una sola ejecución de SA puede salir mejor o bastante peor que una de GA, por eso el análisis usa la distribución completa (figura 3) y no la mejor ejecución. En brazil58 una de las diez semillas de SA llegó **exactamente** al óptimo oficial 25395; es una coincidencia con la referencia, no un certificado de optimalidad.

**3. HC y HC con reinicios son idénticos aquí, y no es un error.** Los dos dan exactamente los mismos números en las cuatro instancias. La razón (suplemento de abajo): con mejor mejora, un barrido de 2-opt cuesta ≈ 1000 evaluaciones y HC necesita entre 45 000 y 92 000 evaluaciones para llegar a su **primer** óptimo local, más que el presupuesto de 30 000. Nunca llega a reiniciar, así que «con reinicios» se reduce a «una ruta».

**4. Tiempo.** Por ejecución, HC y SA tardan del orden de centésimas de segundo; GA, del orden de un segundo (cada individuo se evalúa con el costo completo, O(n), mientras HC y SA usan el delta de 4 aristas, O(1)). Con el mismo número de evaluaciones, **el esfuerzo por evaluación no es igual**, y por eso el ranking de costo por tiempo puede diferir del de costo por evaluaciones (pregunta 9 de la discusión).
