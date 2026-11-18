# ===== Reto 4: animacion de MI ejecucion (5x5, inicio (0, 0), orden rotado 5 posiciones) =====
orden_gif = rotar(DESPLAZAMIENTOS, 5)
estado, camino, traza_propia, expansiones = resolver(5, (0, 0), orden=orden_gif)
print(f"Ejecucion propia: {estado}, {expansiones} expansiones, {len(traza_propia)} eventos.")

estados_p = caminos_por_evento(traza_propia)
i_r = next(i for i, e in enumerate(traza_propia) if e[0] == "retroceso")
liberada, vuelve = traza_propia[i_r][1:], estados_p[i_r][-1]
# Destinos que el marco de `vuelve` tenia en su lista, en orden, y cual sigue despues de `liberada`.
lista = ordenar_destinos(5, vuelve, set(estados_p[i_r]), orden_gif, "fijo")
pos = lista.index(liberada)
siguiente = lista[pos + 1] if pos + 1 < len(lista) else None
print(f"Primer retroceso (evento {i_r}): se libera {liberada}; el caballo queda en {vuelve}.")
print(f"Lista de destinos del marco de {vuelve}: {lista}")
print(f"Siguiente alternativa: {siguiente if siguiente else 'ninguna, asi que ese marco tambien retrocede'}.")

prefijo = traza_propia[: i_r + 6]          # empieza en "inicio" y muestra la rama fallida y lo que sigue
display(NotebookImage(data=gif_traza(5, prefijo), format="gif"))
display(NotebookImage(data=ver_fotograma(5, traza_propia, i_r), format="png"))
