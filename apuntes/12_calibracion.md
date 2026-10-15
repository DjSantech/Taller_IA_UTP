### 14.B Cómo se calibraron SA y GA (y por qué no hay trampa)

**Regla.** Los parámetros se eligen en **instancias distintas** de las de evaluación (gr17, burma14 y eil51, las tres de ampliación) y con **semillas distintas** (100–104 frente a 0–9), y se **congelan** antes de ejecutar la evaluación principal (`assert_frozen()` falla si no están marcados como calibrados). Así no ajusto los parámetros sobre los mismos datos con los que luego juzgo.

**Criterio.** Para cada configuración calculo el gap mediano por instancia (sobre las 5 semillas) y promedio las tres medianas; elijo el menor promedio. Uso el gap (no el costo) para que las instancias sean comparables entre sí. Cada ejecución usa el mismo presupuesto que la evaluación (30000 evaluaciones), con la calibración de T0 de SA contada dentro.

**Hallazgo que condicionó el diseño de SA.** En la prueba de cordura vi que con un número fijo de propuestas por temperatura (`steps = 100`) y α cercano a 1, SA **agotaba el presupuesto sin llegar a enfriarse** y rendía mal (957 en eil51, cuyo óptimo es 426). El motivo: el número de niveles de temperatura hasta Tmin es ⌈ln(Tmin/T0) / ln α⌉ (227 para α = 0,97 y 1379 para α = 0,995), y `steps × niveles` debe caber en el presupuesto. Por eso `steps` se deriva de él: `steps = presupuesto // niveles`. Con esa regla las seis combinaciones de α y p0 terminan por enfriamiento y la comparación entre ellas es justa: ninguna sale perjudicada por un horario de enfriamiento que no cabe.

**Resultado de SA.** α = 0,97 con p0 = 0,8 queda empatado con las dos configuraciones de α = 0,995 (promedio 1,17 %); desempato por la regla declarada de elegir el menor α, que es la más barata de ajustar a presupuestos pequeños. Con α = 0,90 el enfriamiento es tan rápido que queda peor en eil51 (4,46 % con p0 = 0,5 y 4,23 % con p0 = 0,8, frente a 3,52 %), y α = 0,97 con p0 = 0,5, que acepta menos empeoramientos al inicio, llega a 4,69 %. En gr17 y burma14 casi todas las configuraciones alcanzan el óptimo, así que quien decide es eil51, la instancia más grande de las tres.

**Resultado de GA.** Población 40, 2 élites y pm = 0,3. La diferencia con (40, 1, 0,3) es pequeña (2,09 % frente a 2,11 %), y la mutación alta es lo que más pesa: con pm = 0,1 el promedio sube a entre 3,18 % y 5,57 %. Con presupuesto fijo, una población de 40 produce el doble de generaciones que una de 80, que es lo que se nota en eil51.

**Reproducibilidad.** La celda de calibración se puede volver a ejecutar: con semillas fijas reproduce exactamente la misma elección, y compara esa elección con los valores congelados en `FROZEN`; si difirieran, falla.

**Límite de esta calibración.** Son cinco semillas por celda: sirve para elegir una configuración razonable, no para afirmar que es *la* mejor. Una calibración distinta (otros valores de pc, torneo o Tmin) podría mejorar a SA o a GA; los resultados de la evaluación principal son los de **estos** parámetros, no los de todos los posibles.
