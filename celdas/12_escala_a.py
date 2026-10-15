# ===== Escala A: subinstancias (k = 6, 8, 10, 12) de las cuatro instancias obligatorias =====
import os
from IPython.display import Markdown, display

assert_frozen()                                # SA y GA deben estar calibrados antes de evaluar
os.makedirs("resultados", exist_ok=True)

RESULTS_A = run_scale_a([INSTANCES[n] for n in MANDATORY], ks=FROZEN["ks"],
                        seeds=FROZEN["seeds"], config=FROZEN,
                        timing_repeats=3, check_origin=True)
save_rows_csv(RESULTS_A, "resultados/escala_a.csv")
save_results_json(RESULTS_A, "resultados/escala_a.json")   # registros completos (trazas y series)
print("Registros guardados:", len(RESULTS_A), "ejecuciones en resultados/escala_a.csv")

display(Markdown("**Tabla de subinstancias** (óptimo certificado por A\\*, RBFS o programación dinámica; "
                 "memoria = pico incremental de `tracemalloc`)\n\n" + table_subinstances(RESULTS_A)))
