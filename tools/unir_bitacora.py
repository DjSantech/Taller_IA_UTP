# -*- coding: utf-8 -*-
"""Genera BITACORA.md uniendo las bitacoras de cada etapa (apuntes/bitacora_*.md).

Cada modulo se desarrollo con su propia bitacora (asi varios integrantes/sesiones
podian escribir en paralelo sin conflictos). Este script las une en el orden de
las etapas, baja un nivel los titulos y quita el parrafo de formato repetido.

Uso:  python tools/unir_bitacora.py
"""
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDEN = [
    ("D", "Etapa 0 — Estructura, entorno, contrato y evaluación (prefijo D-)"),
    ("G", "Etapa 1 — Interfaz y controlador (prefijo G-)"),
    ("E_T", "Etapa 2 — Agentes aleatorio y voraz; mejora: ajuste de pesos (prefijos E- y T-)"),
    ("S", "Etapa 3 — Minimax, alfa-beta y alfa-beta mejorado (prefijo S-)"),
    ("I", "Etapa 4 — Integración: torre, búsqueda informada, AND-OR, expectiminimax (prefijo I-)"),
    ("M", "Etapa 5 — MCTS-UCT (prefijo M-)"),
    ("X", "Etapa 6 — Torneo y experimentos (prefijo X-)"),
    ("N", "Etapa 7 — Cuaderno, README y entrega (prefijo N-)"),
]


def leer(ruta):
    with open(os.path.join(RAIZ, ruta), encoding="utf-8") as f:
        return f.read()


def cuerpo(texto):
    """Quita el titulo H1 y el parrafo inicial de formato; baja los titulos un nivel."""
    lineas = texto.splitlines()
    if lineas and lineas[0].startswith("# "):
        lineas = lineas[1:]
    texto = "\n".join(lineas).lstrip("\n")
    texto = re.sub(r"\AFormato:.*?\n\n", "", texto, flags=re.S)
    return re.sub(r"^(#{2,5}) ", lambda m: "#" + m.group(1) + " ", texto, flags=re.M).strip()


def main():
    partes = [leer("apuntes/_bitacora_cabecera.md").rstrip(), ""]
    for clave, titulo in ORDEN:
        ruta = "apuntes/bitacora_{0}.md".format(clave)
        if not os.path.exists(os.path.join(RAIZ, ruta)):
            print("AVISO: falta", ruta)
            continue
        partes += ["---", "", "## " + titulo, "", cuerpo(leer(ruta)), ""]
    salida = os.path.join(RAIZ, "BITACORA.md")
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(partes).rstrip() + "\n")
    print("BITACORA.md escrita")


if __name__ == "__main__":
    main()
