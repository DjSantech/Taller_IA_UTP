# ===== Pruebas propias: las tres salidas de busqueda y la PRUEBA ADICIONAL =====
def reproducir_traza(traza):
    """Reconstruye camino y visitadas aplicando la traza y verifica el invariante en cada paso."""
    camino, visitadas = [traza[0][1:]], {traza[0][1:]}
    for tipo, f, c in traza[1:-1]:
        if tipo == "avance":
            assert (f, c) not in visitadas and es_salto(camino[-1], (f, c))
            camino.append((f, c))
            visitadas.add((f, c))
        else:
            assert tipo == "retroceso" and camino[-1] == (f, c)
            camino.pop()
            visitadas.remove((f, c))
        assert visitadas == set(camino)
    return camino


casos = [("éxito", dict(n=5, inicio=(0, 0))),
         ("fracaso", dict(n=3, inicio=(0, 0))),
         ("límite", dict(n=5, inicio=(0, 0), presupuesto=10)),
         ("fracaso", dict(n=1, inicio=(0, 0), cerrado=True)),
         ("éxito", dict(n=6, inicio=(1, 1), estrategia="warnsdorff", cerrado=True))]
for esperado, kw in casos:
    estado, camino, traza, expansiones = resolver(**kw)
    final = reproducir_traza(traza)
    assert estado == esperado and traza[-1] == (estado, *final[-1])
    assert (final == camino) if estado == "éxito" else (camino is None and final == [kw["inicio"]])
    assert expansiones == contar_eventos(traza, "avance") + 1
    print(f"{str(kw):70s} -> {estado:8s} expansiones={expansiones:>5}  ultimo evento={traza[-1]}")

assert resolver(5, (0, 0))[2] == TRAZA_DEMO
print("\nMi traza 5x5 desde (0, 0) coincide evento por evento con TRAZA_DEMO del enunciado.")
print("Prueba adicional reproducir_traza: todas las aserciones pasan.")
