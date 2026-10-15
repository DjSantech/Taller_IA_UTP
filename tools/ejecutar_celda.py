# -*- coding: utf-8 -*-
"""Ejecuta una o varias celdas de `celdas/` FUERA del cuaderno, con los modulos
de `tsp/` ya cargados en un unico espacio de nombres (igual que en el cuaderno,
donde el codigo de los modulos se concatena). Sirve para probar una celda
sin construir ni ejecutar el cuaderno completo.

Uso:  python tools/ejecutar_celda.py celdas/02_fichas.py celdas/02_auditoria.py
"""
import importlib
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDEN = ["datos", "modelo", "mst", "astar", "rbfs", "vecindad", "hc", "sa", "ga",
         "memetico", "validacion", "experimentos", "graficas"]


def main():
    sys.path.insert(0, RAIZ)
    os.chdir(RAIZ)
    espacio = {"__name__": "__main__"}
    for nombre in ORDEN:
        if os.path.exists(os.path.join(RAIZ, "tsp", nombre + ".py")):
            modulo = importlib.import_module("tsp." + nombre)
            espacio.update({k: v for k, v in vars(modulo).items() if not k.startswith("__")})
    # Fuera de Jupyter `display(Markdown(...))` solo imprimiria el repr del objeto:
    # se sustituye por una impresion del texto para poder leer el resultado.
    import IPython.display as _d
    _d.display = lambda *objs, **kw: [print(getattr(o, "data", o)) for o in objs]
    for ruta in sys.argv[1:]:
        with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
            exec(compile(f.read(), ruta, "exec"), espacio)


if __name__ == "__main__":
    main()
