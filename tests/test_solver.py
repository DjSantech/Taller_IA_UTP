import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from caballo.solver import (DESPLAZAMIENTOS, contar_eventos, resolver, rotar,  # noqa: E402
                            saltos_legales, ordenar_destinos)


# ---- funciones del profesor (celda 11), copiadas tal cual ---------------------------
def es_salto(a, b):
    return sorted((abs(a[0] - b[0]), abs(a[1] - b[1]))) == [1, 2]


def recorrido_valido(n, inicio, camino, *, cerrado=False):
    if not camino or len(camino) != n * n or camino[0] != inicio:
        return False
    return (
        len(set(camino)) == len(camino)
        and all(0 <= f < n and 0 <= c < n for f, c in camino)
        and all(es_salto(a, b) for a, b in zip(camino, camino[1:]))
        and (not cerrado or es_salto(camino[-1], inicio))
    )


def test_probar_saltos_del_profesor():
    assert saltos_legales(5, (0, 0), {(0, 0)}, DESPLAZAMIENTOS) == [(1, 2), (2, 1)]
    assert saltos_legales(5, (0, 0), {(0, 0), (1, 2)}, DESPLAZAMIENTOS) == [(2, 1)]
    assert len(saltos_legales(5, (2, 2), {(2, 2)}, DESPLAZAMIENTOS)) == 8
    assert saltos_legales(2, (0, 0), {(0, 0)}, DESPLAZAMIENTOS) == []


def test_probar_resolver_del_profesor():
    estado, camino, _, expansiones = resolver(1, (0, 0), presupuesto=1)
    assert (estado, camino, expansiones) == ("éxito", [(0, 0)], 1)

    estado, camino, traza, expansiones = resolver(5, (0, 0), presupuesto=1)
    assert (estado, camino, expansiones) == ("límite", None, 1)
    assert traza == [("inicio", 0, 0), ("límite", 0, 0)]

    estado, camino, traza, expansiones = resolver(5, (0, 0), presupuesto=2)
    assert (estado, camino, expansiones) == ("límite", None, 2)
    assert [tipo for tipo, _, _ in traza] == ["inicio", "avance", "retroceso", "límite"]

    estado, camino, _, _ = resolver(3, (0, 0))
    assert (estado, camino) == ("fracaso", None)

    estado, camino, _, _ = resolver(1, (0, 0), cerrado=True)
    assert (estado, camino) == ("fracaso", None)

    for estrategia in ("fijo", "warnsdorff"):
        estado, camino, traza, _ = resolver(5, (0, 0), estrategia=estrategia)
        assert estado == "éxito" and recorrido_valido(5, (0, 0), camino)
        assert traza[-1] == ("éxito", *camino[-1])


# ---- pruebas propias ------------------------------------------------------------------
def reproducir(traza):
    """Reconstruye camino y visitadas aplicando la traza; verifica el invariante en cada paso."""
    assert traza[0][0] == "inicio"
    camino = [traza[0][1:]]
    visitadas = {traza[0][1:]}
    for tipo, f, c in traza[1:-1]:
        if tipo == "avance":
            assert (f, c) not in visitadas, "avance a casilla ya visitada"
            assert es_salto(camino[-1], (f, c)), "avance que no es salto de caballo"
            camino.append((f, c)); visitadas.add((f, c))
        elif tipo == "retroceso":
            assert camino[-1] == (f, c), "el retroceso no retira la ultima casilla"
            camino.pop(); visitadas.remove((f, c))
        else:
            raise AssertionError(f"evento intermedio inesperado: {tipo}")
        assert visitadas == set(camino), "se rompio el invariante visitadas == set(camino)"
    return camino


@pytest.mark.parametrize("n,inicio,estrategia,presupuesto", [
    (5, (0, 0), "fijo", 50_000), (5, (0, 0), "warnsdorff", 50_000),
    (5, (0, 0), "fijo", 137), (6, (2, 3), "fijo", 3_000), (3, (0, 0), "fijo", 50_000),
    (4, (1, 1), "warnsdorff", 50_000),
])
def test_la_traza_reconstruye_el_camino_y_respeta_el_invariante(n, inicio, estrategia, presupuesto):
    """PRUEBA ADICIONAL: habria detectado olvidar desmarcar `visitadas` al retroceder,
    registrar el retroceso con la casilla equivocada, o devolver un camino distinto al de la traza."""
    estado, camino, traza, expansiones = resolver(n, inicio, estrategia=estrategia,
                                                   presupuesto=presupuesto)
    final = reproducir(traza)
    assert traza[-1] == (estado, *final[-1])
    if estado == "éxito":
        assert final == camino
    else:
        assert final == [inicio] and camino is None
    assert expansiones <= presupuesto
    # cada avance se cuenta como una expansion del hijo; la raiz suma una mas
    assert expansiones == contar_eventos(traza, "avance") + 1


def test_tres_salidas_de_busqueda():
    assert resolver(5, (0, 0))[0] == "éxito"
    assert resolver(3, (0, 0))[0] == "fracaso"
    assert resolver(5, (0, 0), presupuesto=10)[0] == "límite"


def test_limite_propaga_hasta_la_raiz_desenrollando_con_retrocesos():
    estado, camino, traza, expansiones = resolver(5, (0, 0), presupuesto=10)
    assert estado == "límite" and camino is None and expansiones == 10
    assert traza[-1] == ("límite", 0, 0)
    assert contar_eventos(traza, "avance") == contar_eventos(traza, "retroceso")


def test_impar_por_impar_no_tiene_recorrido_cerrado():
    # Paridad: cada salto cambia de color y un circuito de n^2 saltos (impar) no puede volver
    # al color inicial. Se comprueba agotando el arbol completo (5x5: ~1.7 millones de expansiones).
    assert resolver(3, (0, 0), cerrado=True)[0] == "fracaso"
    estado, _, _, expansiones = resolver(5, (0, 0), cerrado=True, presupuesto=10_000_000)
    assert estado == "fracaso" and expansiones < 10_000_000


def test_recorrido_cerrado_en_6x6():
    estado, camino, _, _ = resolver(6, (1, 1), estrategia="warnsdorff", cerrado=True)
    assert estado == "éxito" and recorrido_valido(6, (1, 1), camino, cerrado=True)


def test_warnsdorff_ordena_por_grado_y_desempata_por_orden_recibido():
    visitadas = {(0, 0)}
    destinos = ordenar_destinos(5, (0, 0), visitadas, DESPLAZAMIENTOS, "warnsdorff")
    assert sorted(destinos) == [(1, 2), (2, 1)]
    grados = [len(saltos_legales(5, d, visitadas | {d}, DESPLAZAMIENTOS)) for d in destinos]
    assert grados == sorted(grados)
    # empate de grados en (1,2) y (2,1) -> se conserva el orden recibido
    assert destinos == [(1, 2), (2, 1)]
    assert ordenar_destinos(5, (0, 0), visitadas, rotar(DESPLAZAMIENTOS, 2), "warnsdorff") == [(2, 1), (1, 2)]


def test_saltos_conservan_el_orden_y_respetan_bordes():
    centro = saltos_legales(5, (2, 2), {(2, 2)}, DESPLAZAMIENTOS)
    assert centro == [(2 + df, 2 + dc) for df, dc in DESPLAZAMIENTOS]
    esquina = saltos_legales(5, (4, 4), {(4, 4)}, rotar(DESPLAZAMIENTOS, 3))
    assert sorted(esquina) == [(2, 3), (3, 2)]


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        resolver(0, (0, 0))
    with pytest.raises(ValueError):
        resolver(5, (5, 0))
    with pytest.raises(ValueError):
        resolver(5, (0, 0), estrategia="otra")
    with pytest.raises(ValueError):
        resolver(5, (0, 0), presupuesto=0)
    with pytest.raises(ValueError):
        resolver(5, (0, 0), orden=DESPLAZAMIENTOS[:7])


def test_misma_entrada_misma_salida():
    assert resolver(6, (0, 0), presupuesto=5_000) == resolver(6, (0, 0), presupuesto=5_000)


def test_nuestra_traza_coincide_con_la_traza_demo_del_profesor():
    """La TRAZA_DEMO del enunciado (celda 3) se grabo en 5x5 desde (0,0) con el orden base:
    nuestro solucionador debe reproducirla evento por evento (validacion externa del contrato)."""
    import json
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nb = json.load(open(os.path.join(raiz, "Backtracking_Recorrido_del_Caballo.ipynb"), encoding="utf-8"))
    ns = {}
    celda = next("".join(c["source"]) for c in nb["cells"]
                 if "".join(c["source"]).startswith("TRAZA_DEMO = "))
    exec(celda, ns)
    _, _, traza, _ = resolver(5, (0, 0))
    assert traza == ns["TRAZA_DEMO"]
