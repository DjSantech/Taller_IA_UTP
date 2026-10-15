# ===== Visualizaciones obligatorias (15.2) a partir de los registros =====
import matplotlib.pyplot as plt

# 1) Rutas inicial y final: una ejecución de SA por instancia obligatoria (semilla 0).
for _nombre in MANDATORY:
    _inst = INSTANCES[_nombre]
    _r = run_one("SA", _inst, seed=0, config=FROZEN, scale="B", keep_history=True)
    plot_routes(_inst, _r.extras["initial_route"], _r.tour, "SA")
    plt.show()

# 2) Mejor costo acumulado vs. evaluaciones (y vs. tiempo) para HC, SA y GA.
for _nombre in MANDATORY:
    plot_convergence_both(RESULTS_B, _nombre, ("HC", "HC-restarts", "SA", "GA"))
    plt.show()

# 3) Gap por algoritmo e instancia.
plot_gap_boxes(RESULTS_B, MANDATORY, ("HC", "HC-restarts", "SA", "GA"))
plt.show()

# 4) Tiempo y memoria de A* y RBFS contra el tamaño de la subinstancia (interrumpidas marcadas).
for _nombre in MANDATORY:
    plot_exact_scaling(RESULTS_A, _nombre)
    plt.show()

# 5) Temperatura, costo actual y tasa de aceptación de empeoramientos de SA.
_sa = [r for r in RESULTS_B if r.algorithm == "SA" and r.instance == "berlin52" and r.seed == 0][0]
plot_sa(_sa, window=FROZEN["sa"]["window"])
plt.show()

# 6) GA: mejor y mediana de la población + diversidad por generación.
_ga = [r for r in RESULTS_B if r.algorithm == "GA" and r.instance == "berlin52" and r.seed == 0][0]
plot_ga(_ga)
plt.show()

# Animación didáctica de mejoras de berlin52 (Hill Climbing, mejor mejora).
_b52 = INSTANCES["berlin52"]
_hc = run_one("HC", _b52, seed=0, config=FROZEN, scale="B", keep_history=True)
_imagenes = animate_improvements(_b52, _hc.extras["route_history"], "HC", path_gif="resultados/berlin52_hc.gif")
print("Cuadros generados:", len(_imagenes), "→ resultados/berlin52_hc.gif")
show_frames(_imagenes)
