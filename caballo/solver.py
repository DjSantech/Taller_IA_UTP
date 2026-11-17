"""Recorrido del caballo con backtracking (Retos 1, 2 y 3).

Estado de la busqueda (un nodo del arbol = un CAMINO PARCIAL):
    camino     lista ordenada de casillas (fila, columna); camino[0] es el inicio.
    visitadas  conjunto con las mismas casillas, para preguntar pertenencia en O(1).
Invariante: visitadas == set(camino) antes y despues de explorar cada rama.

Contrato de `resolver` (celda 8 del enunciado):
* Una EXPANSION se cuenta al entrar a procesar un camino parcial (raiz y casos base incluidos).
* Antes de cada AVANCE se pregunta por el presupuesto: si ya se gastaron todas las
  expansiones y aun queda un destino por explorar, se devuelve "límite" SIN registrar
  ese avance. Una llamada ya contada si puede reconocer un caso base exitoso.
* La traza empieza en ("inicio", f, c); cada avance registra la casilla agregada y cada
  retroceso la casilla retirada (tambien al desenrollar tras "límite"); el ultimo
  evento es (estado, f, c) con la casilla donde quedo el camino tras desenrollar.
* "límite" y "fracaso" se propagan hasta la raiz, que conserva la casilla inicial.
"""

DESPLAZAMIENTOS = (
    (-1, 2), (1, 2), (2, 1), (2, -1),
    (1, -2), (-1, -2), (-2, -1), (-2, 1),
)
ESTRATEGIAS = ("fijo", "warnsdorff")


def saltos_legales(n, posicion, visitadas, orden):
    """Devuelve las casillas libres alcanzables, en el orden recibido."""
    fila, columna = posicion
    destinos = []
    for df, dc in orden:
        f, c = fila + df, columna + dc
        if 0 <= f < n and 0 <= c < n and (f, c) not in visitadas:
            destinos.append((f, c))
    return destinos


def _caballo_salta(a, b):
    """Geometria del salto (para el cierre): no mira si la casilla esta visitada."""
    return sorted((abs(a[0] - b[0]), abs(a[1] - b[1]))) == [1, 2]


def ordenar_destinos(n, posicion, visitadas, orden, estrategia):
    """Destinos en el orden en que se probaran.

    fijo:       el orden de `orden`.
    warnsdorff: primero el destino con MENOS saltos libres desde el, tratando ese destino
                como visitado; `sorted` es estable, asi los empates conservan `orden`.
    """
    destinos = saltos_legales(n, posicion, visitadas, orden)
    if estrategia == "fijo":
        return destinos
    if estrategia == "warnsdorff":
        def grado(d):
            return len(saltos_legales(n, d, visitadas | {d}, orden))
        return sorted(destinos, key=grado)
    raise ValueError(f"estrategia desconocida: {estrategia!r}; use 'fijo' o 'warnsdorff'")


def _validar_entrada(n, inicio, orden, estrategia, presupuesto):
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n debe ser un entero positivo")
    if not (isinstance(inicio, tuple) and len(inicio) == 2
            and all(isinstance(x, int) and 0 <= x < n for x in inicio)):
        raise ValueError(f"inicio fuera del tablero {n}x{n}: {inicio!r}")
    if sorted(orden) != sorted(DESPLAZAMIENTOS) or len(set(orden)) != 8:
        raise ValueError("orden debe ser una permutacion de DESPLAZAMIENTOS")
    if estrategia not in ESTRATEGIAS:
        raise ValueError(f"estrategia desconocida: {estrategia!r}; use 'fijo' o 'warnsdorff'")
    if not isinstance(presupuesto, int) or isinstance(presupuesto, bool) or presupuesto < 1:
        raise ValueError("presupuesto debe ser un entero positivo")


def resolver(n, inicio, *, orden=DESPLAZAMIENTOS, estrategia="fijo",
             cerrado=False, presupuesto=50_000):
    """Devuelve estado, camino, traza y número de expansiones."""
    _validar_entrada(n, inicio, orden, estrategia, presupuesto)
    total = n * n
    camino = [inicio]
    visitadas = {inicio}
    traza = [("inicio", *inicio)]
    expansiones = 0

    def buscar():
        nonlocal expansiones
        expansiones += 1                                   # se procesa este camino parcial
        if len(camino) == total:                           # caso base: tablero cubierto
            if not cerrado or _caballo_salta(camino[-1], inicio):
                return "éxito"
            return "fracaso"                               # cerrado sin salto de regreso
        for destino in ordenar_destinos(n, camino[-1], visitadas, orden, estrategia):
            if expansiones >= presupuesto:                 # queda destino, no queda presupuesto
                return "límite"
            camino.append(destino)                         # ELEGIR
            visitadas.add(destino)
            traza.append(("avance", *destino))
            resultado = buscar()                           # EXPLORAR
            if resultado == "éxito":
                return resultado                           # se conserva el camino completo
            camino.pop()                                   # DESHACER (fracaso o límite)
            visitadas.remove(destino)
            traza.append(("retroceso", *destino))
            if resultado == "límite":
                return resultado                           # se propaga sin probar mas
        return "fracaso"                                   # sin destinos o todos agotados

    estado = buscar()
    traza.append((estado, *camino[-1]))
    return estado, (list(camino) if estado == "éxito" else None), traza, expansiones


def contar_eventos(traza, tipo):
    return sum(1 for evento in traza if evento[0] == tipo)


def rotar(orden, k):
    """Rotacion de la lista de desplazamientos (como la que asigna el docente)."""
    k %= len(orden)
    return tuple(orden[k:]) + tuple(orden[:k])


def comparar_estrategias(casos, *, presupuesto=50_000):
    """Filas de la tabla del Reto 3 con el MISMO presupuesto y orden para ambas estrategias.

    `casos`: iterable de (etiqueta, n, inicio, orden, cerrado).
    """
    filas = []
    for etiqueta, n, inicio, orden, cerrado in casos:
        for estrategia in ESTRATEGIAS:
            estado, _, traza, expansiones = resolver(
                n, inicio, orden=orden, estrategia=estrategia,
                cerrado=cerrado, presupuesto=presupuesto)
            filas.append({
                "caso": etiqueta, "tablero": f"{n}×{n}", "inicio": inicio,
                "modo": "Cerrado" if cerrado else "Abierto",
                "estrategia": "Warnsdorff" if estrategia == "warnsdorff" else "Fijo",
                "estado": estado, "expansiones": expansiones,
                "retrocesos": contar_eventos(traza, "retroceso"),
            })
    return filas


def tabla_markdown(filas):
    cab = "| Tablero | Inicio | Modo | Estrategia | Estado | Expansiones | Retrocesos |\n|---|---|---|---|---|---:|---:|\n"
    def num(x):
        return f"{x:,}".replace(",", ".")
    return cab + "".join(
        f"| {f['tablero']} | {f['inicio']} | {f['modo']} | {f['estrategia']} | {f['estado']} "
        f"| {num(f['expansiones'])} | {num(f['retrocesos'])} |\n" for f in filas)
