# ===== Escala B: instancias completas =====
from IPython.display import Markdown, display

assert_frozen()
RESULTS_B = run_scale_b([INSTANCES[n] for n in MANDATORY], seeds=FROZEN["seeds"], config=FROZEN)
save_rows_csv(RESULTS_B, "resultados/escala_b.csv")
save_results_json(RESULTS_B, "resultados/escala_b.json")
SUMMARY_B = summarize(RESULTS_B)
print("Registros guardados:", len(RESULTS_B), "ejecuciones en resultados/escala_b.csv")

for _nombre in MANDATORY:
    _opt = INSTANCES[_nombre].optimum
    display(Markdown("#### {0} (óptimo oficial {1})\n\n{2}".format(_nombre, _opt, table_methods(SUMMARY_B, _nombre))))

# Auditoría final: ningún gap negativo y ninguna ruta inválida en ninguna ejecución.
for _r in RESULTS_B + RESULTS_A:
    _r.validate(INSTANCES[_r.instance.split("[")[0]] if "[" not in _r.instance else
                INSTANCES[_r.instance.split("[")[0]].subinstance(int(_r.instance.split("k=")[1].rstrip("]"))),
                origin=_r.parameters.get("origin", 0))
    assert _r.gap_percent is None or _r.gap_percent >= -1e-9, (_r.instance, _r.algorithm, _r.gap_percent)
print("✔ Todas las rutas son permutaciones válidas con costo coherente y ningún gap es negativo.")
