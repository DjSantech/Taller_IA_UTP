### Cambio de parámetros con predicción previa

El enunciado pide documentar un cambio en otro parámetro y **predecir su efecto antes de ejecutar**. Escribimos cada predicción con su razón; la celda anterior las verifica todas con `assert`.

1. **Rotar el orden 2 posiciones.** El orden empieza en `(2, 1), (2, -1), …`. Desde (0, 0), el primer desplazamiento que cae dentro del tablero es `(2, 1)`, así que el primer avance es **(2, 1)** y no (1, 2).
2. **`presupuesto=30` en 5×5.** El orden base necesita 41 expansiones, así que con 30 no alcanza. El resultado es **límite**, y tras desenrollar el camino vuelve al inicio: último evento `("límite", 0, 0)`.
3. **6×6 cerrado desde (1, 1).** 36 es par, así que la paridad no lo prohíbe, y en 6×6 se conocen circuitos cerrados: esperamos **éxito**.
4. **5×5 cerrado.** 25 es impar, así que por paridad **no existe circuito**. Con presupuesto suficiente, el árbol se agota y el resultado es **fracaso**, no límite.
