# ===== Experimento 3: ablacion (E0 frente a E*, y ordenacion si/no) desde los resultados guardados =====
import os

import matplotlib.pyplot as plt
from IPython.display import Markdown, display

if os.path.exists(os.path.join("resultados", "exp3_ablacion_partidas.csv")):
    ablacion = ablation_load("resultados")
    _lineas = ["| Comparación | Partidas | Terminadas | Truncadas | V | T | D | Puntuación media | IC 95 % | Material medio al truncar (no oficial) |",
               "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    def _num(valor, formato):
        return "-" if valor in ("", None) else format(float(valor), formato)

    for _s in ablacion["summary"]:
        _ic = ("-" if _s["ic95_bajo"] in ("", None)
               else f"[{_num(_s['ic95_bajo'], '.3f')}, {_num(_s['ic95_alto'], '.3f')}]")
        _lineas.append(f"| {_s['comparacion']} | {_s['partidas']} | {_s['terminadas']} | {_s['truncadas']} | "
                       f"{_s['victorias']} | {_s['tablas']} | {_s['derrotas']} | "
                       f"{_num(_s['puntuacion_media'], '.3f')} | {_ic} | "
                       f"{_num(_s['material_medio_truncadas_no_oficial'], '+.2f')} |")
    display(Markdown("**Ablación en partidas: el mismo alfa-beta mejorado con $E_0$ y con $E^*$** "
                     "(mismo plazo, mismas aperturas, colores intercambiados)\n\n" + "\n".join(_lineas)))
    print("Profundidad media completada por etiqueta (E0 y E* cuestan lo mismo de evaluar):",
          ablation_depths(ablacion["decisions"]))
    _cfg_ab = ablacion["config"]
    if _cfg_ab:
        print(f"Configuracion: {_cfg_ab.get('description', '')}; partidas: {len(ablacion['games'])}")
else:
    ablacion = None
    print("AVISO: aun no existe resultados/exp3_ablacion_partidas.csv (lo escribe "
          "tools/correr_experimentos.py).")

# Ablacion de la ordenacion: profundidad fija (Exp. 1, en vivo arriba) y con plazo (curva guardada).
_ruta_dt = os.path.join("resultados", "exp_profundidad_tiempo.csv")
if os.path.exists(_ruta_dt):
    _orden = ordering_ablation(exp1_filas, depth_time_load(_ruta_dt))
    _lineas = ["| Modo | Parámetro | Medida | Sin ordenación | Con ordenación | Con / sin |",
               "|---|---|---|---:|---:|---:|"]
    for _o in _orden:
        _lineas.append(f"| {_o['modo']} | {_o['parametro']} | {_o['medida']} | {_o['sin_ordenacion']} | "
                       f"{_o['con_ordenacion']} | {_o['razon_con_sin']} |")
    display(Markdown("**Ablación de la ordenación** (el resto fijo)\n\n" + "\n".join(_lineas)))
    if ablacion is not None:
        fig_ablation(ablacion["summary"], _orden)
        plt.show()
