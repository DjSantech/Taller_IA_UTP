# ===== Reto 2: invariante antes y despues de una rama fallida de MI ejecucion =====
estado, camino, traza, expansiones = resolver(5, (0, 0))
print(f"5x5 desde (0, 0), orden base, fijo: {estado} en {expansiones} expansiones, "
      f"{contar_eventos(traza, 'retroceso')} retrocesos, {len(traza)} eventos.")

estados = caminos_por_evento(traza)
# Rama fallida = un avance seguido, mas adelante, del retroceso de esa misma casilla a la misma profundidad.
for i, (tipo, f, c) in enumerate(traza):
    if tipo != "avance":
        continue
    prof = len(estados[i])
    j = next((k for k in range(i + 1, len(traza))
              if traza[k][0] == "retroceso" and traza[k][1:] == (f, c)
              and len(estados[k]) == prof - 1), None)
    if j is not None:
        break
antes, despues = estados[i - 1], estados[j]
print(f"Rama fallida: avance a {(f, c)} en el evento {i}; retroceso de esa casilla en el evento {j}.")
print("  camino antes   (ultimas 4):", antes[-4:], "| largo", len(antes))
print("  camino despues (ultimas 4):", despues[-4:], "| largo", len(despues))
print("  mismo camino y mismo orden:", antes == despues)
print("  visitadas == set(camino) en ambos momentos:", set(antes) == set(despues) == set(estados[i - 1]))
assert antes == despues
