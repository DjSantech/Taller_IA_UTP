# -*- coding: utf-8 -*-
"""Construye el cuaderno entregable a partir del enunciado ORIGINAL (primer commit).

* Conserva todas las celdas del profesor, en su orden.
* Celda 9 (plantilla con `raise NotImplementedError`): se COMPLETA con el codigo de
  `caballo/solver.py`, que es la fuente probada con pytest.
* Celda 11: se quitan los comentarios de `probar_saltos()` y `probar_resolver()`,
  como pide el enunciado al terminar cada reto.
* Despues de algunas celdas se insertan textos (`apuntes/*.md`) y celdas propias
  (`celdas/*.py`). Un archivo que falte solo produce un aviso.

Uso:  python tools/construir_cuaderno.py
"""
import os
import subprocess
import sys

import nbformat

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE = "Backtracking_Recorrido_del_Caballo.ipynb"
SEPARADOR = "<!-- celda -->"

PLAN = {
    0: [("md", "apuntes/00_portada.md")],
    6: [("md", "apuntes/02_laboratorio.md"), ("py", "celdas/02_laboratorio.py")],
    9: [("md", "apuntes/03_decisiones.md"), ("py", "celdas/03_invariante.py")],
    10: [("md", "apuntes/04_cierre.md")],
    11: [("py", "celdas/05_pruebas_propias.py"), ("md", "apuntes/05_pruebas.md"),
         ("py", "celdas/06_tabla.py"), ("md", "apuntes/06_tabla.md")],
    12: [("py", "celdas/07_animacion.py"), ("md", "apuntes/07_animacion.md"),
         ("py", "celdas/08_prediccion.py"), ("md", "apuntes/08_prediccion.md"),
         ("md", "apuntes/09_traza_manual.md"), ("md", "apuntes/10_entrega.md")],
}


def leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def existe(ruta):
    return os.path.exists(os.path.join(RAIZ, ruta))


def enunciado_original():
    primero = subprocess.check_output(["git", "rev-list", "--max-parents=0", "HEAD"],
                                      cwd=RAIZ, text=True).split()[-1]
    texto = subprocess.check_output(["git", "show", f"{primero}:{NOMBRE}"], cwd=RAIZ).decode("utf-8")
    return nbformat.reads(texto, as_version=4)


def celdas_md(ruta):
    for trozo in leer(ruta).split(SEPARADOR):
        if trozo.strip():
            yield nbformat.v4.new_markdown_cell(trozo.strip("\n"))


def main():
    nb = enunciado_original()
    if len(nb.cells) != 13 or "NotImplementedError" not in "".join(nb.cells[9].source):
        sys.exit("El enunciado no tiene la forma esperada (13 celdas, plantilla en la celda 9).")

    solver = leer("caballo/solver.py")
    nb.cells[9].source = ("# ===== Retos 1, 2 y 3: codigo propio (fuente probada: caballo/solver.py) =====\n"
                          + solver.strip() + "\n")
    pruebas = nb.cells[11].source
    for llamada in ("probar_saltos()", "probar_resolver()"):
        if f"# {llamada}" not in pruebas:
            sys.exit(f"No encuentro '# {llamada}' en la celda 11.")
        pruebas = pruebas.replace(f"# {llamada}", llamada)
    nb.cells[11].source = pruebas + '\nprint("probar_saltos() y probar_resolver(): todas las aserciones pasan.")\n'

    nuevas, faltan = [], []
    for i, celda in enumerate(nb.cells):
        nuevas.append(celda)
        for tipo, ruta in PLAN.get(i, []):
            if not existe(ruta):
                faltan.append(ruta)
            elif tipo == "md":
                nuevas.extend(celdas_md(ruta))
            else:
                nuevas.append(nbformat.v4.new_code_cell(leer(ruta).strip("\n") + "\n"))

    nb.cells = nuevas
    nb.metadata["kernelspec"] = {"display_name": "Python (ia-taller4)", "language": "python",
                                 "name": "ia-taller4"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.metadata["authors"] = [{"name": "Santiago Guevara"}]
    nb.nbformat_minor = 5
    for k, c in enumerate(nb.cells):
        c["id"] = f"c{k:03d}"
        if c.cell_type == "code":
            c.outputs = []
            c.execution_count = None
    nbformat.validate(nb)
    with open(os.path.join(RAIZ, NOMBRE), "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    for ruta in faltan:
        print("AVISO: falta", ruta)
    print(f"Cuaderno escrito: {NOMBRE} ({len(nuevas)} celdas)")


if __name__ == "__main__":
    main()
