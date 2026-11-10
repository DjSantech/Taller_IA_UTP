# -*- coding: utf-8 -*-
"""Construye el cuaderno entregable a partir del enunciado ORIGINAL del profesor.

POR QUE EXISTE
El codigo se desarrolla y se prueba en el paquete `chess_ai/` (pytest), pero la
entrega principal es el cuaderno del enunciado, completado y ejecutable de arriba
abajo sin importar el paquete. Esta herramienta (misma idea que en el Taller 2):
  1. recupera el enunciado intacto del PRIMER commit (nunca parte del cuaderno ya
     modificado: la construccion es idempotente);
  2. conserva TODAS sus celdas (enunciados, tablas y pseudocodigo visibles);
  3. inserta, debajo de cada celda, el codigo de los modulos (sin los imports
     internos `from chess_ai... import`, que en el cuaderno ya estan definidos en
     celdas anteriores, y sin bloques `if __name__ == "__main__":`), las celdas
     propias de `celdas/*.py` y los textos de `apuntes/*.md`;
  4. FALLA si dos modulos definen el mismo nombre de nivel superior, o si una celda
     propia redefine un nombre de un modulo (al concatenarlos, uno taparia al otro
     en silencio);
  5. asigna ids de celda unicos, fija el kernel `ia-taller3` y valida con nbformat.

`chess_ai/contract.py` NO se inserta: el enunciado ya define SearchStats,
Decision y Agent en su celda 8 (el modulo existe solo para pytest).

Si falta un archivo del plan (por ejemplo, resultados de un experimento que aun
no se ha corrido), solo se AVISA y se sigue: una reconstruccion posterior lo incluye.

Uso:  python tools/construir_cuaderno.py [--salida RUTA]
"""
import argparse
import ast
import os
import subprocess
import sys

import nbformat

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE = "Taller_Ajedrez_Grafico_Agentes_IA.ipynb"
PAQUETE = "chess_ai"
SEPARADOR = "<!-- celda -->"          # parte un apunte en varias celdas Markdown
CELDAS_ENUNCIADO = 28

# indice de celda del enunciado -> inserciones DESPUES de esa celda.
#   ("md", ruta)   apunte Markdown (varias celdas si contiene SEPARADOR)
#   ("mod", nombre) codigo de chess_ai/<nombre>.py      ("py", ruta) celda de codigo propia
PLAN = {
    # 0 titulo del enunciado
    0: [("md", "apuntes/00_portada.md")],
    # 2 celda de dependencias del enunciado (importa chess, ipywidgets, ...)
    2: [("py", "celdas/00_entorno.py")],
    # 3 seccion 2: analisis PEAS
    3: [("md", "apuntes/02_peas.md")],
    # 6 ampliaciones graficas obligatorias
    6: [("md", "apuntes/03_interfaz.md")],
    # 8 contrato suministrado (SearchStats, Decision, Agent)
    8: [("md", "apuntes/04_arquitectura.md"), ("mod", "environment")],
    # 9 seccion 5: agentes y evaluacion comun
    9: [("md", "apuntes/05_evaluacion.md"), ("mod", "evaluation"),
        ("py", "celdas/05_evaluacion.py")],
    # 11 IMPLEMENTACION A: aleatorio, voraz
    11: [("mod", "agents_basic"), ("md", "apuntes/05a_basicos.md"),
         ("py", "celdas/05a_basicos.py")],
    # 12 IMPLEMENTACION B: minimax y alfa-beta
    12: [("mod", "search"), ("md", "apuntes/05b_busqueda.md"), ("py", "celdas/05b_busqueda.py")],
    # 13 IMPLEMENTACION C: ordenacion y profundizacion iterativa (codigo en search)
    13: [("md", "apuntes/05_profundizacion.md"), ("py", "celdas/05_profundizacion.py")],
    # 14 IMPLEMENTACION D: MCTS-UCT y mejora adicional
    14: [("mod", "mcts"), ("md", "apuntes/05c_mcts.md"), ("py", "celdas/05c_mcts.py"),
         ("md", "apuntes/05e_mejora.md"), ("mod", "tuning"), ("mod", "registry")],
    # 16 IMPLEMENTACION E: controlador y vista
    16: [("mod", "controller"), ("md", "apuntes/06_controlador.md"), ("mod", "gui"),
         ("md", "apuntes/06_app.md"), ("py", "celdas/06_app.py")],
    # 18 INTEGRACION: torre, busqueda informada, ajuste local e incertidumbre
    18: [("mod", "rook_problem"), ("py", "celdas/07a_torre.py"), ("md", "apuntes/07a_torre.md"),
         ("md", "apuntes/07b_informada.md"),
         ("py", "celdas/07c_ajuste.py"), ("md", "apuntes/07c_ajuste.md"),
         ("mod", "uncertainty"), ("py", "celdas/07d_incertidumbre.py"),
         ("md", "apuntes/07d_incertidumbre.md")],
    # 21 PRUEBAS DE SUS AGENTES
    21: [("py", "celdas/08_pruebas.py"), ("md", "apuntes/08_pruebas.md")],
    # 22 seccion 9: protocolo experimental
    22: [("md", "apuntes/09_protocolo.md")],
    # 23 esquema CSV + TODO del torneo
    23: [("mod", "tournament"), ("mod", "experiments"),
         ("py", "celdas/09_exp1.py"), ("md", "apuntes/09_exp1.md"),
         ("py", "celdas/09_torneo.py"), ("md", "apuntes/09_exp2.md"),
         ("py", "celdas/09_ablacion.py"), ("md", "apuntes/09_exp3.md"),
         ("py", "celdas/09_mcts.py"), ("md", "apuntes/09_exp4.md")],
    # 26 rubrica
    26: [("md", "apuntes/11_rubrica.md")],
    # 27 sustentacion, conclusiones y lista de entrega
    27: [("md", "apuntes/12_sustentacion.md"), ("md", "apuntes/13_entrega.md")],
}

# Marcadores que se reemplazan por el contenido de otro apunte si existe (si no, se quitan).
INCLUSIONES = {"{{Q10}}": "apuntes/12_q10.md"}


def leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def existe(ruta):
    return os.path.exists(os.path.join(RAIZ, ruta))


def enunciado_original():
    """El cuaderno tal como esta en el primer commit (enunciado sin modificar)."""
    primero = subprocess.check_output(
        ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=RAIZ, text=True).split()[-1]
    texto = subprocess.check_output(["git", "show", "{0}:{1}".format(primero, NOMBRE)],
                                    cwd=RAIZ).decode("utf-8")
    nb = nbformat.reads(texto, as_version=4)
    if len(nb.cells) != CELDAS_ENUNCIADO:
        sys.exit("El enunciado del primer commit tiene {0} celdas; se esperaban {1}".format(
            len(nb.cells), CELDAS_ENUNCIADO))
    return nb


def _es_interno(nodo):
    if isinstance(nodo, ast.ImportFrom):
        return bool(nodo.module) and nodo.module.split(".")[0] == PAQUETE
    if isinstance(nodo, ast.Import):
        return any(a.name.split(".")[0] == PAQUETE for a in nodo.names)
    return False


def _es_bloque_main(nodo):
    return (isinstance(nodo, ast.If) and isinstance(nodo.test, ast.Compare)
            and isinstance(nodo.test.left, ast.Name) and nodo.test.left.id == "__name__")


def codigo_de_modulo(ruta):
    """Fuente del modulo sin imports internos (multilinea incluido) ni bloque __main__."""
    fuente = leer(ruta)
    arbol = ast.parse(fuente)
    lineas = fuente.splitlines()
    for nodo in arbol.body:
        if _es_interno(nodo) or _es_bloque_main(nodo):
            for k in range(nodo.lineno - 1, nodo.end_lineno):
                lineas[k] = ""
    # sin lineas en blanco repetidas donde estaban los imports
    salida, vacias = [], 0
    for linea in lineas:
        vacias = vacias + 1 if not linea.strip() else 0
        if vacias <= 2:
            salida.append(linea)
    return "\n".join(salida).strip() + "\n"


def nombres_de_nivel_superior(fuente):
    nombres = set()
    for nodo in ast.parse(fuente).body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombres.add(nodo.name)
        elif isinstance(nodo, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for t in objetivos:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        nombres.add(n.id)
    return nombres


_VALORES = {}


def numero_de_pruebas():
    """Cuenta las pruebas de la suite pytest (se recolectan, no se ejecutan)."""
    if "n" not in _VALORES:
        try:
            salida = subprocess.run([sys.executable, "-m", "pytest", "tests", "--collect-only", "-q",
                                     "-p", "no:cacheprovider"], cwd=RAIZ, capture_output=True,
                                    text=True, timeout=300).stdout
            linea = [l for l in salida.splitlines() if " collected" in l or "tests collected" in l]
            _VALORES["n"] = linea[-1].split()[0] if linea else "(ver tests/)"
        except (OSError, subprocess.SubprocessError):
            _VALORES["n"] = "(ver tests/)"
    return _VALORES["n"]


def celdas_de_markdown(ruta):
    texto = leer(ruta)
    if "{{N_PRUEBAS}}" in texto:
        texto = texto.replace("{{N_PRUEBAS}}", numero_de_pruebas())
    for marcador, origen in INCLUSIONES.items():
        if marcador in texto:
            texto = texto.replace(marcador, leer(origen).strip() if existe(origen) else "")
    for trozo in texto.split(SEPARADOR):
        trozo = trozo.strip("\n")
        if trozo.strip():
            yield nbformat.v4.new_markdown_cell(trozo)


def main():
    ap = argparse.ArgumentParser(description="Construye el cuaderno entregable.")
    ap.add_argument("--salida", default=os.path.join(RAIZ, NOMBRE))
    args = ap.parse_args()

    original = enunciado_original()
    modulos, propias, faltan, nuevas = [], [], [], []
    for i, celda in enumerate(original.cells):
        nuevas.append(celda)
        for tipo, destino in PLAN.get(i, []):
            if tipo == "md":
                if existe(destino):
                    nuevas.extend(celdas_de_markdown(destino))
                else:
                    faltan.append(destino)
            elif tipo == "mod":
                ruta = "{0}/{1}.py".format(PAQUETE, destino)
                if not existe(ruta):
                    faltan.append(ruta)
                    continue
                modulos.append(ruta)
                cabecera = "# ===== {0}/{1}.py =====\n".format(PAQUETE, destino)
                nuevas.append(nbformat.v4.new_code_cell(cabecera + codigo_de_modulo(ruta)))
            elif tipo == "py":
                if existe(destino):
                    propias.append(destino)
                    nuevas.append(nbformat.v4.new_code_cell(leer(destino).strip("\n") + "\n"))
                else:
                    faltan.append(destino)
            else:
                sys.exit("tipo desconocido en PLAN: {0}".format(tipo))

    # Choques de nombres: modulo contra modulo (error) y celda propia contra modulo (error).
    vistos = {}
    for ruta in modulos:
        for nombre in nombres_de_nivel_superior(codigo_de_modulo(ruta)):
            if nombre.startswith("__"):
                continue
            if nombre in vistos:
                sys.exit("CHOQUE DE NOMBRES: '{0}' esta en {1} y en {2}".format(
                    nombre, vistos[nombre], ruta))
            vistos[nombre] = ruta
    for ruta in propias:
        for nombre in nombres_de_nivel_superior(leer(ruta)):
            if nombre in vistos:
                sys.exit("CHOQUE DE NOMBRES: la celda {0} redefine '{1}' de {2}".format(
                    ruta, nombre, vistos[nombre]))

    original.cells = nuevas
    original.metadata["kernelspec"] = {"display_name": "Python (ia-taller3)",
                                       "language": "python", "name": "ia-taller3"}
    original.metadata["language_info"] = {"name": "python"}
    original.metadata.pop("colab", None)
    autores = [a for a in original.metadata.get("authors", []) if a.get("name")]
    original.metadata["authors"] = autores + [{"name": "Santiago Guevara"}, {"name": "Januar Mena"}]
    original.nbformat_minor = 5
    for k, c in enumerate(original.cells):          # nbformat 4.5 exige ids unicos
        c["id"] = "c{0:03d}".format(k)
        if c.cell_type == "code":
            c.outputs = []
            c.execution_count = None
    nbformat.validate(original)
    with open(args.salida, "w", encoding="utf-8", newline="\n") as f:
        nbformat.write(original, f)
    for ruta in faltan:
        print("AVISO: falta {0} (se incluira al reconstruir cuando exista)".format(ruta))
    print("Cuaderno escrito: {0} ({1} celdas: {2} del enunciado, {3} modulos, {4} celdas propias, "
          "{5} faltantes)".format(args.salida, len(nuevas), CELDAS_ENUNCIADO, len(modulos),
                                  len(propias), len(faltan)))


if __name__ == "__main__":
    main()
