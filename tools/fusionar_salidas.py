# -*- coding: utf-8 -*-
"""Fusiona el cuaderno recien construido (textos al dia) con las SALIDAS de una
ejecucion completa ya hecha, sin repetirla.

Cuando se usa: la ejecucion completa tarda ~25 minutos. Si despues de ejecutarla solo
se corrigen textos (celdas Markdown), no hace falta volver a ejecutar: esta herramienta
toma las celdas Markdown del cuaderno nuevo y las celdas de CODIGO con sus salidas del
cuaderno ejecutado. Por seguridad EXIGE que el codigo de cada celda sea idéntico en
ambos; si alguna celda de codigo cambio, hay que volver a ejecutar.

Uso:  python tools/fusionar_salidas.py NUEVO.ipynb EJECUTADO.ipynb SALIDA.ipynb
"""
import sys

import nbformat


def normal(celda):
    return "".join(celda.source).strip()


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    nuevo = nbformat.read(sys.argv[1], as_version=4)
    ejecutado = nbformat.read(sys.argv[2], as_version=4)
    if len(nuevo.cells) != len(ejecutado.cells):
        sys.exit("Distinto numero de celdas ({0} frente a {1}): hay que volver a ejecutar".format(
            len(nuevo.cells), len(ejecutado.cells)))
    for i, (n, e) in enumerate(zip(nuevo.cells, ejecutado.cells)):
        if n.cell_type != e.cell_type:
            sys.exit("La celda {0} cambio de tipo: hay que volver a ejecutar".format(i))
        if n.cell_type == "code":
            if normal(n) != normal(e):
                sys.exit("El codigo de la celda {0} cambio: hay que volver a ejecutar".format(i))
            n["outputs"] = e["outputs"]
            n["execution_count"] = e["execution_count"]
    nbformat.validate(nuevo)
    nbformat.write(nuevo, sys.argv[3])
    print("Fusion correcta: {0} celdas; salidas de {1} celdas de codigo conservadas.".format(
        len(nuevo.cells), sum(1 for c in nuevo.cells if c.cell_type == "code")))


if __name__ == "__main__":
    main()
