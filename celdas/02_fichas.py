# ===== Fichas de las siete instancias (lectura + auditoría automática de la matriz) =====
import math
from IPython.display import Markdown, display

INSTANCE_NAMES = ["att48", "berlin52", "brazil58", "gr48", "gr17", "burma14", "eil51"]
MANDATORY = ["att48", "berlin52", "brazil58", "gr48"]
CALIBRATION = ["gr17", "burma14", "eil51"]
INSTANCES = {nombre: load_by_name(nombre) for nombre in INSTANCE_NAMES}   # falla si la auditoría falla

filas = ["| Instancia | n | Tipo de pesos | Coordenadas | Óptimo oficial | Peso mín / máx | D(1,2), D(1,3), D(2,3) |",
         "|---|---:|---|---|---:|---|---|"]
for nombre in INSTANCE_NAMES:
    inst = INSTANCES[nombre]
    pesos = sorted({inst.D[a][b] for a in range(inst.n) for b in range(a + 1, inst.n)})
    filas.append("| {0} | {1} | {2} | {3} | {4} | {5} / {6} | {7}, {8}, {9} |".format(
        nombre, inst.n, inst.weight_type, "sí" if inst.coords else "no", inst.optimum,
        pesos[0], pesos[-1], inst.D[0][1], inst.D[0][2], inst.D[1][2]))
display(Markdown("\n".join(filas)))
