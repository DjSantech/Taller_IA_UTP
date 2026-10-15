# -*- coding: utf-8 -*-
"""Construye el cuaderno entregable a partir del enunciado ORIGINAL del profesor.

POR QUE EXISTE
El codigo se desarrolla y se prueba en el paquete `tsp/` (pytest), pero el
enunciado exige un cuaderno autocontenido que se ejecute de arriba abajo con
datos locales. Esta herramienta:
  1. recupera el enunciado intacto del primer commit (nunca parte del cuaderno
     ya modificado, asi la construccion es idempotente);
  2. conserva todas sus celdas (enunciados y pseudocodigo visibles);
  3. inserta, debajo de cada seccion, el codigo de los modulos (sin los
     imports internos `from tsp... import`, que en el cuaderno ya estan en
     celdas anteriores), las celdas de `celdas/` y los apuntes de `apuntes/`;
  4. falla si dos modulos definen el mismo nombre de nivel superior (al
     concatenarlos uno taparia al otro en silencio).

Uso:  python tools/construir_cuaderno.py [--salida RUTA]
"""
import argparse
import ast
import os
import re
import subprocess
import sys

import nbformat

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE = "Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb"
SEPARADOR = "<!-- celda -->"

# indice de celda del enunciado -> lista de inserciones DESPUES de esa celda.
# ("md", ruta) apuntes en Markdown (varias celdas si hay separador)
# ("mod", nombre) codigo de tsp/<nombre>.py      ("py", ruta) celda de codigo suelta
# ("opt-mod", nombre) igual que "mod" pero se omite si el modulo no existe
PLAN = {
    0: [("md", "apuntes/00_mapa.md")],
    1: [("md", "apuntes/01_lectura_critica.md")],
    6: [("mod", "datos"), ("py", "celdas/02_fichas.py"), ("md", "apuntes/02_datos.md")],
    7: [("mod", "modelo"), ("py", "celdas/02_auditoria.py"), ("md", "apuntes/04_modelo.md")],
    10: [("mod", "mst"), ("md", "apuntes/05_mst.md")],
    11: [("md", "apuntes/03_microcaso.md")],
    12: [("mod", "astar"), ("md", "apuntes/06_astar.md")],
    14: [("mod", "rbfs"), ("md", "apuntes/07_rbfs.md")],
    15: [("mod", "vecindad")],
    16: [("mod", "hc"), ("md", "apuntes/08_2opt_hc.md")],
    17: [("mod", "sa")],
    18: [("md", "apuntes/09_sa.md")],
    19: [("mod", "ga")],
    20: [("opt-mod", "memetico"), ("md", "apuntes/10_ga.md")],
    21: [("mod", "validacion"), ("py", "celdas/11_validacion.py"), ("md", "apuntes/11_validacion.md")],
    23: [("mod", "experimentos"), ("md", "apuntes/12_protocolo.md"),
         ("py", "celdas/12_calibracion.py"), ("md", "apuntes/12_calibracion.md"),
         ("py", "celdas/12_escala_a.py"), ("py", "celdas/12_overhead.py"), ("md", "apuntes/12_resultados_a.md"),
         ("py", "celdas/12_escala_b.py"), ("md", "apuntes/12_resultados_b.md"),
         ("py", "celdas/12_suplemento_hc.py"), ("md", "apuntes/12_suplemento_hc.md"),
         ("py", "celdas/14_tiempo_igual.py"), ("md", "apuntes/14_tiempo_igual.md"),
         ("py", "celdas/09_hc_vs_sa.py"), ("md", "apuntes/09_hc_vs_sa.md")],
    26: [("mod", "graficas"), ("md", "apuntes/13_graficas.md"), ("py", "celdas/13_figuras.py"),
         ("md", "apuntes/13_lectura_figuras.md")],
    27: [("md", "apuntes/14_discusion.md")],
    29: [("md", "apuntes/18_espacios.md"), ("py", "celdas/00_entorno.py"), ("md", "apuntes/18_mapa.md")],
    30: [("md", "apuntes/19_entrega.md")],
}

MARCADORES = ("{{RESULTADOS_ESCALA_A}}", "{{RESULTADOS_ESCALA_B}}")


def leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def existe(ruta):
    return os.path.exists(os.path.join(RAIZ, ruta))


def enunciado_original():
    primero = subprocess.check_output(
        ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=RAIZ, text=True).split()[-1]
    texto = subprocess.check_output(["git", "show", "{0}:{1}".format(primero, NOMBRE)],
                                    cwd=RAIZ).decode("utf-8")
    return nbformat.reads(texto, as_version=4)


def codigo_sin_imports_internos(ruta):
    """Quita `from tsp.x import ...` / `import tsp...` (multilinea incluido)."""
    fuente = leer(ruta)
    arbol = ast.parse(fuente)
    lineas = fuente.splitlines()
    for nodo in arbol.body:
        interno = ((isinstance(nodo, ast.ImportFrom) and nodo.module
                    and nodo.module.split(".")[0] == "tsp") or
                   (isinstance(nodo, ast.Import) and any(a.name.split(".")[0] == "tsp"
                                                         for a in nodo.names)))
        if interno:
            for k in range(nodo.lineno - 1, nodo.end_lineno):
                lineas[k] = ""
    return "\n".join(lineas).strip() + "\n"


def nombres_de_nivel_superior(ruta):
    nombres = set()
    for nodo in ast.parse(leer(ruta)).body:
        if isinstance(nodo, (ast.FunctionDef, ast.ClassDef)):
            nombres.add(nodo.name)
        elif isinstance(nodo, ast.Assign):
            for t in nodo.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        nombres.add(n.id)
    return nombres


def celdas_de_markdown(ruta):
    texto = leer(ruta)
    for m in MARCADORES:
        texto = texto.replace(m, "")
    for trozo in texto.split(SEPARADOR):
        trozo = trozo.strip("\n")
        if trozo.strip():
            yield nbformat.v4.new_markdown_cell(trozo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=os.path.join(RAIZ, NOMBRE))
    args = ap.parse_args()

    original = enunciado_original()
    modulos_usados = []
    nuevas = []
    for i, celda in enumerate(original.cells):
        nuevas.append(celda)
        for tipo, destino in PLAN.get(i, []):
            if tipo == "md":
                if existe(destino):
                    nuevas.extend(celdas_de_markdown(destino))
                else:
                    print("AVISO: falta {0}".format(destino))
            elif tipo in ("mod", "opt-mod"):
                ruta = "tsp/{0}.py".format(destino)
                if not existe(ruta):
                    if tipo == "mod":
                        print("AVISO: falta modulo {0}".format(ruta))
                    continue
                modulos_usados.append(ruta)
                cabecera = "# ===== tsp/{0}.py =====\n".format(destino)
                nuevas.append(nbformat.v4.new_code_cell(cabecera + codigo_sin_imports_internos(ruta)))
            elif tipo == "py":
                if existe(destino):
                    nuevas.append(nbformat.v4.new_code_cell(leer(destino).strip("\n") + "\n"))
                else:
                    print("AVISO: falta celda {0}".format(destino))

    # Choques de nombres entre modulos concatenados.
    vistos = {}
    for ruta in modulos_usados:
        for nombre in nombres_de_nivel_superior(ruta):
            if nombre in vistos and not nombre.startswith("__"):
                sys.exit("CHOQUE DE NOMBRES: '{0}' esta en {1} y en {2}".format(nombre, vistos[nombre], ruta))
            vistos[nombre] = ruta

    original.cells = nuevas
    original.metadata["kernelspec"] = {"display_name": "Python (ia-taller2)",
                                       "language": "python", "name": "ia-taller2"}
    original.metadata["language_info"] = {"name": "python"}
    original.nbformat_minor = 5
    for k, c in enumerate(original.cells):          # nbformat 4.5 exige ids unicos
        c["id"] = "c{0:03d}".format(k)
        if c.cell_type == "code":
            c.outputs = []
            c.execution_count = None
    nbformat.validate(original)
    with open(args.salida, "w", encoding="utf-8") as f:
        nbformat.write(original, f)
    print("Cuaderno escrito: {0} ({1} celdas, {2} modulos)".format(args.salida, len(nuevas), len(modulos_usados)))


if __name__ == "__main__":
    main()
