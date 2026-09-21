# -*- coding: utf-8 -*-
"""Ejecuta el cuaderno completo en un entorno limpio y reporta el resultado.

POR QUE EXISTE ESTA HERRAMIENTA
El enunciado exige que "todo el cuaderno debe ejecutarse desde el inicio en un
entorno limpio" y considera defectos reproducibles las celdas fuera de orden y
las dependencias implicitas. Comprobar eso a mano en el editor no sirve: una
sesion interactiva conserva variables de ejecuciones anteriores, asi que una
celda puede funcionar por accidente gracias a algo que ya no existe en el
cuaderno. Esta herramienta arranca un kernel nuevo, ejecuta las celdas en
orden y falla si alguna lanza una excepcion.

NO MODIFICA EL CUADERNO. Ejecuta sobre una copia temporal, de modo que el
archivo versionado sigue sin salidas guardadas (decision D-04 de la bitacora).

Uso:
    python tools/ejecutar_cuaderno.py
    python tools/ejecutar_cuaderno.py --texto        # imprime tambien la salida
"""

import argparse
import asyncio
import glob
import os
import sys
import tempfile

# En Windows, el bucle de eventos por omision (Proactor) no implementa
# `add_reader`, que pyzmq necesita, y cada ejecucion emite un RuntimeWarning.
# La politica Selector es la que recomienda el propio aviso.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


def localizar_cuaderno(raiz):
    """Busca el .ipynb del taller sin depender de su nombre exacto."""
    candidatos = sorted(glob.glob(os.path.join(raiz, "*.ipynb")))
    if not candidatos:
        sys.exit("No se encontro ningun .ipynb en {0}".format(raiz))
    if len(candidatos) > 1:
        sys.exit("Hay varios .ipynb; deje solo el del taller:\n  "
                 + "\n  ".join(candidatos))
    return candidatos[0]


def texto_de_las_salidas(celda):
    """Concatena el texto que una celda imprimio (stdout, resultados, errores)."""
    partes = []
    for salida in celda.get("outputs", []):
        if "text" in salida:
            partes.append("".join(salida["text"]))
        elif "data" in salida and "text/plain" in salida["data"]:
            partes.append("".join(salida["data"]["text/plain"]))
        elif salida.get("output_type") == "error":
            partes.append("\n".join(salida.get("traceback", [])))
    return "".join(partes)


def main():
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--texto", action="store_true",
                            help="imprimir la salida de cada celda de codigo")
    argumentos = analizador.parse_args()

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta = localizar_cuaderno(raiz)
    print("Cuaderno: {0}".format(os.path.basename(ruta)))
    print("Python:   {0}".format(sys.executable))

    cuaderno = nbformat.read(ruta, as_version=4)
    celdas_codigo = sum(1 for c in cuaderno.cells if c.cell_type == "code")
    print("Celdas:   {0} en total, {1} de codigo".format(
        len(cuaderno.cells), celdas_codigo))
    print("-" * 70)

    # `resources.metadata.path` fija el directorio de trabajo del kernel. Debe
    # ser la carpeta del cuaderno: la comprobacion 10 de la auditoria lee el
    # propio .ipynb desde el directorio actual (ver D-10 en la bitacora).
    cliente = NotebookClient(cuaderno, timeout=900, kernel_name="python3",
                             resources={"metadata": {"path": raiz}},
                             allow_errors=False)
    try:
        cliente.execute()
    except CellExecutionError as error:
        print("FALLO la ejecucion del cuaderno.\n")
        for indice, celda in enumerate(cuaderno.cells):
            if celda.cell_type == "code" and any(
                    s.get("output_type") == "error"
                    for s in celda.get("outputs", [])):
                print("Celda {0}, primeras lineas del codigo:".format(indice))
                for linea in "".join(celda.source).splitlines()[:6]:
                    print("    " + linea)
                print("\n" + texto_de_las_salidas(celda))
                break
        print(str(error)[:400])
        return 1

    # Se guarda la copia ejecutada en una carpeta temporal, nunca encima del
    # original: el cuaderno versionado no debe llevar salidas.
    copia = os.path.join(tempfile.mkdtemp(), os.path.basename(ruta))
    nbformat.write(cuaderno, copia)

    if argumentos.texto:
        for indice, celda in enumerate(cuaderno.cells):
            if celda.cell_type != "code":
                continue
            salida = texto_de_las_salidas(celda).rstrip()
            if salida:
                print("\n===== salida de la celda {0} =====".format(indice))
                print(salida)

    print("-" * 70)
    print("OK: el cuaderno se ejecuto de principio a fin sin excepciones.")
    print("Copia ejecutada (no versionada): {0}".format(copia))
    return 0


if __name__ == "__main__":
    sys.exit(main())
