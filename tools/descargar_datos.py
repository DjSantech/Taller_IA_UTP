# -*- coding: utf-8 -*-
"""Descarga y descomprime las instancias TSPLIB que usa el taller.

Uso:  python tools/descargar_datos.py [carpeta_destino]     (por omision: datos/)

Fuente: https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/
Los archivos son datos, no codigo: solo se leen como texto. Se comprueba que
cada .tsp descargado declare la misma NAME y que el .opt.tour (si existe)
tenga la dimension esperada.
"""
import gzip
import os
import sys
import urllib.request

BASE = "https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/"
INSTANCIAS = ["att48", "berlin52", "brazil58", "gr48",      # obligatorias
              "gr17", "burma14", "eil51"]                    # ampliacion
TOURS_OPTIMOS = ["att48", "berlin52", "gr48"]               # los que publica el indice


def bajar(nombre_remoto, destino):
    with urllib.request.urlopen(BASE + nombre_remoto, timeout=60) as r:
        crudo = r.read()
    datos = gzip.decompress(crudo) if nombre_remoto.endswith(".gz") else crudo
    with open(destino, "wb") as f:
        f.write(datos)
    return datos.decode("latin-1")


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "datos"
    os.makedirs(carpeta, exist_ok=True)
    for nombre in INSTANCIAS:
        try:
            texto = bajar(nombre + ".tsp.gz", os.path.join(carpeta, nombre + ".tsp"))
            ok = ("NAME" in texto.splitlines()[0]) and (nombre in texto.splitlines()[0])
            print("[{0}] {1}.tsp ({2} bytes)".format("OK" if ok else "??", nombre, len(texto)))
        except Exception as e:
            print("[ERROR] {0}.tsp: {1}".format(nombre, e))
    for nombre in TOURS_OPTIMOS:
        try:
            texto = bajar(nombre + ".opt.tour.gz", os.path.join(carpeta, nombre + ".opt.tour"))
            print("[OK] {0}.opt.tour ({1} bytes)".format(nombre, len(texto)))
        except Exception as e:
            print("[AVISO] {0}.opt.tour no disponible: {1}".format(nombre, e))
    try:
        texto = bajar("TSP-BEST.html", os.path.join(carpeta, "TSP-BEST.html"))
        print("[OK] TSP-BEST.html (referencia de optimos)")
    except Exception as e:
        print("[AVISO] TSP-BEST.html: {0}".format(e))


if __name__ == "__main__":
    main()
