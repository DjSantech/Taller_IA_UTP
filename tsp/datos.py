# -*- coding: utf-8 -*-
"""Carga de instancias TSPLIB y subinstancias inducidas (seccion 3 del taller).

Decision de representacion: las ciudades se manejan por POSICION 0..n-1; la
correspondencia con los identificadores reales del archivo vive en `node_ids`.
Nunca se supone que el identificador i este en la posicion i-1.
"""
import os

import tsplib95

# Optimos oficiales del CICLO (TSP-BEST.html de TSPLIB95).
OPTIMA = {"att48": 10628, "berlin52": 7542, "brazil58": 25395, "gr48": 5046,
          "gr17": 2085, "burma14": 3323, "eil51": 426}


class TSPInstance:
    """Instancia simetrica con matriz de pesos inmutable.

    Atributos:
        name        nombre (las subinstancias llevan sufijo [k=..])
        node_ids    identificadores reales, ordenados; posicion i <-> node_ids[i]
        D           tuple de tuples de int: D[i][j] = peso oficial entre posiciones
        coords      tuple de (x, y) por posicion, o None si el archivo no trae
                    datos de dibujo (solo para VISUALIZAR, nunca para pesos)
        weight_type valor de EDGE_WEIGHT_TYPE (EUC_2D, ATT, GEO, EXPLICIT)
        optimum     optimo oficial del ciclo, o None (subinstancias: None)
        parent      nombre de la instancia completa si es subinstancia
    """

    def __init__(self, name, node_ids, D, coords, weight_type, optimum, parent=None):
        self.name = name
        self.node_ids = tuple(node_ids)
        self.D = tuple(tuple(fila) for fila in D)
        self.coords = None if coords is None else tuple(coords)
        self.weight_type = weight_type
        self.optimum = optimum
        self.parent = parent
        self.n = len(self.node_ids)

    def __repr__(self):
        return "TSPInstance({0}, n={1}, {2})".format(self.name, self.n, self.weight_type)

    def subinstance(self, k):
        """Primeros k identificadores ORDENADOS, con los pesos originales (induce
        el subproblema; no se recalculan distancias). El optimo oficial no aplica."""
        if not 2 <= k <= self.n:
            raise ValueError("k fuera de rango")
        pos = list(range(k))
        D = [[self.D[i][j] for j in pos] for i in pos]
        coords = None if self.coords is None else [self.coords[i] for i in pos]
        return TSPInstance("{0}[k={1}]".format(self.name, k), self.node_ids[:k], D,
                           coords, self.weight_type, None, parent=self.name)


def load_instance(path):
    """Lee un .tsp con tsplib95 y reconstruye la matriz D (verificada)."""
    problem = tsplib95.load(path)
    weight_keys = sorted(problem.get_nodes())     # claves que acepta get_weight
    n = len(weight_keys)
    if problem.dimension != n:
        raise ValueError("DIMENSION no coincide con los nodos leidos")
    # Para EXPLICIT sin coordenadas tsplib95 numera los nodos 0..n-1, pero los
    # archivos (.opt.tour) y la convencion TSPLIB los numeran 1..n. El
    # identificador REAL es posicion+1; la clave de get_weight es solo interna.
    node_ids = [k + 1 for k in weight_keys] if weight_keys[0] == 0 else list(weight_keys)
    D = [[0 if a == b else problem.get_weight(a, b) for b in weight_keys]
         for a in weight_keys]
    _audit_matrix(D)
    coords = _drawing_coords(problem, weight_keys)
    name = problem.name
    return TSPInstance(name, node_ids, D, coords, problem.edge_weight_type,
                       OPTIMA.get(name))


def load_by_name(name, folder="datos"):
    return load_instance(os.path.join(folder, name + ".tsp"))


def _audit_matrix(D):
    n = len(D)
    for i in range(n):
        if len(D[i]) != n:
            raise ValueError("matriz no cuadrada")
        if D[i][i] != 0:
            raise ValueError("diagonal no nula en {0}".format(i))
        for j in range(n):
            if D[i][j] != D[j][i]:
                raise ValueError("matriz asimetrica en ({0},{1})".format(i, j))
            if D[i][j] < 0:
                raise ValueError("peso negativo en ({0},{1})".format(i, j))


def _drawing_coords(problem, node_ids):
    """Coordenadas SOLO para dibujar. Si no existen, devuelve None."""
    for fuente in (getattr(problem, "node_coords", None),
                   getattr(problem, "display_data", None)):
        if fuente and all(i in fuente for i in node_ids):
            return [tuple(fuente[i][:2]) for i in node_ids]
    return None


def read_opt_tour(path, instance):
    """Lee un .opt.tour oficial y lo devuelve como ruta de POSICIONES, empezando
    en la posicion 0. Sirve para verificar costos, nunca como ruta inicial."""
    t = tsplib95.load(path)
    ids = list(t.tours[0])
    pos = {nid: i for i, nid in enumerate(instance.node_ids)}
    route = [pos[i] for i in ids]
    k = route.index(0)
    return route[k:] + route[:k]
