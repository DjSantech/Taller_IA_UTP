# -*- coding: utf-8 -*-
"""Ejecuta un cuaderno completo, de arriba abajo, en un kernel NUEVO.

POR QUE EXISTE ESTA HERRAMIENTA
El enunciado exige que el cuaderno se ejecute desde un kernel reiniciado, con los
datos locales y en orden. En una sesion interactiva las variables de ejecuciones
anteriores pueden ocultar dependencias implicitas; aqui se arranca un kernel
limpio, se ejecutan las celdas en orden y se FALLA en la primera celda con error
(no se sigue adelante: allow_errors=False).

NO MODIFICA EL CUADERNO: ejecuta una copia en memoria y guarda la copia ejecutada
en una carpeta temporal (el archivo versionado no lleva salidas).

KERNEL: debe ser el del entorno virtual ia-taller2. Se usa el kernel `python3` del
Python que lanza este script, asi que hay que invocarlo con el del venv:
    C:/Users/santi/venvs/ia-taller2/Scripts/python.exe tools/ejecutar_cuaderno.py

Uso:
    python tools/ejecutar_cuaderno.py                      # autodeteccion (un solo .ipynb en la raiz)
    python tools/ejecutar_cuaderno.py ruta/al/cuaderno.ipynb
    python tools/ejecutar_cuaderno.py cuaderno.ipynb --texto --timeout 3600
"""

import argparse
import asyncio
import glob
import os
import sys
import tempfile

# En Windows el bucle por omision (Proactor) no implementa `add_reader`, que pyzmq
# necesita; la politica Selector es la que recomienda el propio aviso.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

NOMBRE_ENTREGABLE = "Taller_IA_TSP_AStar_MST_HC_SA_GA_RBFS.ipynb"
VENV = "ia-taller2"


def localizar_cuaderno(raiz):
    """Sin argumento: el entregable si existe; si no, el unico .ipynb de la raiz."""
    entregable = os.path.join(raiz, NOMBRE_ENTREGABLE)
    if os.path.exists(entregable):
        return entregable
    candidatos = sorted(glob.glob(os.path.join(raiz, "*.ipynb")))
    if not candidatos:
        sys.exit("No se encontro ningun .ipynb en {0}".format(raiz))
    if len(candidatos) > 1:
        sys.exit("Hay varios .ipynb; indique cual como argumento:\n  "
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
    analizador = argparse.ArgumentParser(description=__doc__,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("cuaderno", nargs="?", default=None,
                            help="ruta del .ipynb (por omision: autodeteccion)")
    analizador.add_argument("--texto", action="store_true",
                            help="imprimir la salida de cada celda de codigo")
    analizador.add_argument("--timeout", type=int, default=3600,
                            help="segundos maximos por celda (por omision 3600)")
    analizador.add_argument("--guardar", default=None, metavar="RUTA",
                            help="ademas de la copia temporal, guardar aqui el cuaderno ejecutado "
                                 "(con salidas); se usa solo para el commit de entrega (decision D-04)")
    analizador.add_argument("--permitir-otro-entorno", action="store_true",
                            help="no exigir que el Python sea el del venv ia-taller2")
    argumentos = analizador.parse_args()

    # El kernel `python3` hereda el Python que lanza este script: si no es el del
    # venv, el cuaderno se ejecutaria con otras versiones de las dependencias.
    if VENV not in sys.executable and not argumentos.permitir_otro_entorno:
        sys.exit("Use el Python del entorno {0} (actual: {1}).".format(VENV, sys.executable))

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta = os.path.abspath(argumentos.cuaderno) if argumentos.cuaderno else localizar_cuaderno(raiz)
    if not os.path.exists(ruta):
        sys.exit("No existe el cuaderno: {0}".format(ruta))
    print("Cuaderno: {0}".format(ruta))
    print("Python:   {0}".format(sys.executable))

    cuaderno = nbformat.read(ruta, as_version=4)
    celdas_codigo = sum(1 for c in cuaderno.cells if c.cell_type == "code")
    print("Celdas:   {0} en total, {1} de codigo".format(len(cuaderno.cells), celdas_codigo))
    print("-" * 70)

    # El directorio de trabajo del kernel es la RAIZ del proyecto (donde esta datos/),
    # sin importar donde este el .ipynb temporal.
    cliente = NotebookClient(cuaderno, timeout=argumentos.timeout, kernel_name="python3",
                             resources={"metadata": {"path": raiz}},
                             allow_errors=False)
    try:
        cliente.execute()
    except CellExecutionError as error:
        print("FALLO la ejecucion del cuaderno (primera celda con error).\n")
        for indice, celda in enumerate(cuaderno.cells):
            if celda.cell_type == "code" and any(
                    s.get("output_type") == "error" for s in celda.get("outputs", [])):
                print("Celda {0}, primeras lineas del codigo:".format(indice))
                for linea in "".join(celda.source).splitlines()[:6]:
                    print("    " + linea)
                print("\n" + texto_de_las_salidas(celda))
                break
        print(str(error)[:400])
        return 1

    # Copia ejecutada en carpeta temporal; el original no se toca.
    copia = os.path.join(tempfile.mkdtemp(), os.path.basename(ruta))
    nbformat.write(cuaderno, copia)
    if argumentos.guardar:
        nbformat.write(cuaderno, argumentos.guardar)
        print("Cuaderno ejecutado guardado en: {0}".format(argumentos.guardar))

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
