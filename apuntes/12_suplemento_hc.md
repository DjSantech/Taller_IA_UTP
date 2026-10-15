### 14.E Suplemento: por qué HC no mejora con reinicios en la escala B

Al ver que HC y HC con reinicios daban resultados idénticos, no lo dejé pasar como una curiosidad: lo medí. La tabla (a) responde cuánto cuesta realmente un ascenso completo y la (b) muestra en qué condiciones los reinicios sí aportan.

**(a)** Con 10 semillas y sin tope práctico, HC (mejor mejora) necesita **≈ 45 000 a 48 000 evaluaciones en att48 y gr48, ≈ 62 000 en berlin52 y ≈ 92 000 en brazil58** para su primer óptimo local, y en **ninguna** de las 40 ejecuciones lo alcanza antes de las 30 000. El hallazgo importante es doble:

- el gap de HC en la escala B (20 % a 76 %) es el de una **ruta a medio ascender** cuando se acaba el presupuesto; no es lo que da el método cuando termina;
- los óptimos locales de 2-opt son **buenos**: el gap mediano de los óptimos locales completos es de 3,2 % a 5,4 %, no lejos del 1 % al 6 % de SA. La ventaja de SA no está en que explore un vecindario mejor, sino en que **gasta su presupuesto en lo que importa** (un calendario de enfriamiento que cabe) mientras HC gasta casi todo en barridos completos de 1000 evaluaciones para dar un solo paso.

**(b)** Donde un ascenso completo sí cabe, los reinicios aportan: en burma14, HC de una ruta iguala el óptimo en 5 de 10 semillas y HC con reinicios (≈ 39 reinicios) en **10 de 10**; en gr17, de 1 de 10 a 8 de 10 (≈ 19 reinicios).

**Consecuencia para la pregunta 7:** los reinicios aportan mucho cuando el presupuesto alcanza para varios ascensos y **nada** cuando no alcanza para uno. «Con reinicios» no es una mejora de HC en sí misma, es una forma de usar presupuesto sobrante.

**Primera mejora (subinstancia, por separado).** En berlin52 con 30 ciudades, primera mejora llega al óptimo local con menos evaluaciones (mediana ≈ 7600 contra ≈ 10 500) pero con un costo ligeramente peor (6334 contra 6275). No mezclo esta variante con los resultados principales, como pide el enunciado.
