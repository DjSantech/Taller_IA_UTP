# ===== Laboratorio de observacion: respuestas calculadas sobre TRAZA_DEMO =====
def caminos_por_evento(traza):
    """Camino actual DESPUES de aplicar cada evento (reconstruido desde la traza)."""
    camino, estados = [], []
    for tipo, f, c in traza:
        if tipo in ("inicio", "avance"):
            camino.append((f, c))
        elif tipo == "retroceso":
            assert camino[-1] == (f, c)
            camino.pop()
        estados.append(list(camino))
    return estados


estados_demo = caminos_por_evento(TRAZA_DEMO)
i_ret = next(i for i, e in enumerate(TRAZA_DEMO) if e[0] == "retroceso")
antes, despues = estados_demo[i_ret - 1], estados_demo[i_ret]
print(f"1) Primer retroceso: evento {i_ret}. Casilla liberada {TRAZA_DEMO[i_ret][1:]}; "
      f"el caballo vuelve a {despues[-1]}.")
print(f"   Visitadas antes: {len(antes)}; despues: {len(despues)}. "
      f"El ultimo numero del tablero ({len(antes)}) desaparece.")
print("2) Pila (ultimos tres marcos; cada marco = una llamada BUSCAR con su ultima casilla):")
print("   antes  :", " -> ".join(map(str, antes[-3:])), "(el marco de", antes[-1], "no tiene destinos libres)")
print("   despues:", " -> ".join(map(str, despues[-3:])),
      "(el marco de", despues[-1], "elige su siguiente destino)")
for i, (tipo, f, c) in enumerate(TRAZA_DEMO):
    if tipo != "retroceso":
        continue
    j = next((k for k in range(i + 1, len(TRAZA_DEMO))
              if TRAZA_DEMO[k][0] == "avance" and TRAZA_DEMO[k][1:] == (f, c)), None)
    if j is not None:
        print(f"3) La casilla {(f, c)} se libera en el evento {i} y vuelve como destino en el evento {j}: "
              f"ahora se llega desde {estados_demo[j - 1][-1]} y no desde {estados_demo[i - 1][-2]}.")
        break
