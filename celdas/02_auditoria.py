# ===== Auditoría independiente de distancias y de las rutas óptimas oficiales (sección 3) =====
# Se ejecuta aquí, justo después del modelo común de la sección 4, porque usa `tour_cost` y `is_valid_tour`.
import itertools

def _euc2d(a, b):                          # fórmula EUC_2D escrita aparte del lector
    return int(math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) + 0.5)

def _att(a, b):                            # fórmula ATT escrita aparte del lector
    r = math.sqrt(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) / 10.0)
    t = int(r + 0.5)
    return t + 1 if t < r else t

for nombre, formula in (("berlin52", _euc2d), ("att48", _att)):
    inst = INSTANCES[nombre]
    malos = [(i, j) for i, j in itertools.combinations(range(inst.n), 2)
             if inst.D[i][j] != formula(inst.coords[i], inst.coords[j])]
    assert not malos, (nombre, malos[:3])
    print("✔ {0}: los {1} pares coinciden con la fórmula {2} escrita a mano".format(
        nombre, inst.n * (inst.n - 1) // 2, inst.weight_type))

a48 = INSTANCES["att48"]
distintos = sum(1 for i, j in itertools.combinations(range(a48.n), 2)
                if a48.D[i][j] != _euc2d(a48.coords[i], a48.coords[j]))
print("• att48: {0} de 1128 pares tienen un peso ATT distinto del que daría EUC_2D".format(distintos))

print("\nRutas óptimas oficiales (.opt.tour): validez, costo y el error de olvidar el regreso")
for nombre in ("att48", "berlin52", "gr48"):
    inst = INSTANCES[nombre]
    ruta = read_opt_tour("datos/{0}.opt.tour".format(nombre), inst)
    assert is_valid_tour(ruta, inst.n, 0)
    costo = tour_cost(inst.D, ruta)
    assert costo == inst.optimum, (nombre, costo)
    sin_cierre = costo - inst.D[ruta[-1]][ruta[0]]
    print("✔ {0}: costo {1} == óptimo oficial {2}.  Sin la arista de cierre saldría {3} "
          "({4:+.1f} % respecto al óptimo: parecería «mejor que el óptimo»)".format(
              nombre, costo, inst.optimum, sin_cierre, 100 * (sin_cierre - inst.optimum) / inst.optimum))

print("\nRutas inválidas rechazadas por el verificador")
for descripcion, ruta in (("ciudad duplicada", [0, 1, 1, 3, 4]), ("ciudad omitida", [0, 1, 2, 3]),
                          ("ciudad fuera de rango", [0, 1, 2, 3, 9]), ("no empieza en el origen", [1, 0, 2, 3, 4])):
    problemas = tour_problems(ruta, 5, origin=0)
    assert problemas
    print("✔ {0}: {1}".format(descripcion, problemas[0]))
