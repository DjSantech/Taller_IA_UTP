### Decisiones de implementación (Retos 1–3)

| Decisión | Qué hice | Por qué |
|---|---|---|
| Estado | `camino` (lista ordenada) y `visitadas` (conjunto) | La lista conserva el orden de los saltos y permite deshacer el último. El conjunto responde «¿ya la visité?» en O(1). |
| Saltos legales | Se recorre `orden` y se filtran los destinos fuera del tablero y los visitados, **sin reordenar** | Así el orden de exploración lo controla quien llama: la rotación del docente o Warnsdorff. |
| Dónde se cuenta la expansión | Al **entrar** a `buscar()`, antes del caso base | El contrato cuenta la raíz y los casos base. Por eso `expansiones == avances + 1`. |
| Caso base | `len(camino) == n*n`. En modo abierto es éxito; en modo cerrado, éxito solo si hay salto del último al inicio | La condición de cierre mira la **geometría** del salto, aunque el inicio ya esté visitado. |
| Dónde se mira el presupuesto | Dentro del ciclo, **antes de cada avance**: `if expansiones >= presupuesto: return "límite"` | «Si queda un destino por explorar y no hay presupuesto para procesarlo, devuelva límite antes de registrar ese avance». Un caso base ya contado puede dar éxito con la última expansión. |
| Deshacer | Tras un fracaso **o** un límite del hijo: `camino.pop()`, `visitadas.remove()` y se registra `retroceso` | Restaura el invariante `visitadas == set(camino)`. Ante un límite también se desenrolla, por eso la traza muestra los retrocesos hasta la raíz. |
| Propagar límite | Si el hijo devuelve límite, el padre deshace y devuelve límite **sin probar más destinos** | El presupuesto es global: probar otro destino gastaría expansiones que no hay. |
| Último evento | `(estado, *camino[-1])` después de desenrollar | En éxito es la última casilla del recorrido; en fracaso o límite, el inicio. |
| Warnsdorff | `sorted(destinos, key=grado)`, donde `grado` cuenta los saltos libres desde el destino con ese destino marcado como visitado | `sorted` es **estable**, así que los empates conservan el orden recibido. Se mantiene el retroceso por si la heurística falla. |

La celda siguiente comprueba el invariante en una rama fallida de **mi** ejecución.
