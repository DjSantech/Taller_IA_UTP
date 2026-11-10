# ===== 7.C: resultados del ajuste de pesos (corrida guardada) y su verificacion =====
# La corrida completa (run_tuning(TuningConfig()), ~80 s) produjo los archivos de resultados/.
# Aqui se LEEN, se comprueban contra los datos guardados y se grafican; no se reajusta nada.
import csv
import json
import os

import matplotlib.pyplot as plt
import numpy as np

with open(os.path.join("resultados", "pesos_ajustados.json"), encoding="utf-8") as _fh:
    _rep = json.load(_fh)
_obj = _rep["objective"]
print(f"Metodo elegido: {_rep['chosen_method']} ({_rep['selection_rule']}); K = {_rep['K']:.1f} cp")
print(f"{'':<22}{'wm':>8}{'wp':>8}{'wk':>9}{'wa':>7}{'J entren.':>12}{'J prueba':>11}")
print(f"{'iniciales E0':<22}" + "".join(f"{w:>8.3g}" for w in _rep["initial_weights"])
      + f"{_obj['train_initial']:>13.6f}{_obj['test_initial']:>11.6f}")
print(f"{'ajustados E*':<22}" + "".join(f"{w:>8.4g}" for w in _rep["weights"])
      + f"{_obj['train_tuned']:>13.6f}{_obj['test_tuned']:>11.6f}")
print(f"{'solo material (ref.)':<22}{'':>32}{_obj['train_material_only']:>13.6f}{_obj['test_material_only']:>11.6f}")
for _m, _info in _rep["methods"].items():
    print(f"  {_m}: {_info['evals']} evaluaciones de J ({_info['stop_reason']}), "
          f"J entren. = {_info['train_obj']:.8f}, pesos {_info['best_weights']}")

# Entrenamiento y prueba separados: ninguna partida ni posicion compartida.
_pos = {"train": {}, "test": {}}
with open(os.path.join("resultados", "tuning_posiciones.csv"), encoding="utf-8") as _fh:
    for _fila in csv.DictReader(_fh):
        _pos[_fila["split"]][" ".join(_fila["fen"].split()[:4])] = (_fila["game_id"], float(_fila["label"]))
_juegos = {s: {g for g, _ in v.values()} for s, v in _pos.items()}
assert not set(_pos["train"]) & set(_pos["test"]) and not _juegos["train"] & _juegos["test"]
print(f"\nPosiciones: {len(_pos['train'])} de entrenamiento ({len(_juegos['train'])} partidas) y "
      f"{len(_pos['test'])} de prueba ({len(_juegos['test'])} partidas); sin FEN ni partida en comun.")

# Recalcular J de prueba con los pesos guardados y la E del cuaderno: debe dar lo mismo.
_F = np.array([features(chess.Board(f + " 0 1")) for f in _pos["test"]], dtype=float)
_y = np.array([lab for _, lab in _pos["test"].values()], dtype=float)
_j0 = tuning_objective(_rep["initial_weights"], _F, _y, _rep["K"])
_j1 = tuning_objective(_rep["weights"], _F, _y, _rep["K"])
assert abs(_j0 - _obj["test_initial"]) < 1e-9 and abs(_j1 - _obj["test_tuned"]) < 1e-9
print(f"J de prueba recalculado aqui: E0 = {_j0:.6f}, E* = {_j1:.6f} (coincide con el JSON).")

print("\nAblacion a nivel de objetivo (devolver UN peso a su valor inicial):")
with open(os.path.join("resultados", "tuning_ablacion.csv"), encoding="utf-8") as _fh:
    for _fila in csv.DictReader(_fh):
        print(f"  {_fila['weight']}: {float(_fila['value_tuned']):g} -> {float(_fila['value_initial']):g}"
              f"   J entren. {float(_fila['train_obj']):.6f}   J prueba {float(_fila['test_obj']):.6f}")
_pt = _rep["paired_test_by_game"]
print(f"Comparacion pareada por partida en prueba: diferencia media {_pt['mean_diff']:+.5f} "
      f"(error estandar {_pt['se']:.5f}, {_pt['games']} partidas); E* mejor en "
      f"{100 * _pt['frac_games_improved']:.2f} % de ellas.")

# Historial de la busqueda local: mejor J de entrenamiento frente a evaluaciones gastadas.
_hist = {}
with open(os.path.join("resultados", "tuning_historial.csv"), encoding="utf-8") as _fh:
    for _fila in csv.DictReader(_fh):
        _hist.setdefault(_fila["method"], []).append((int(_fila["eval"]), float(_fila["best_obj"]),
                                                      float(_fila["candidate_obj"])))
_fig, _ax = plt.subplots(figsize=(8, 3.6))
for _m, _serie in _hist.items():
    _ax.plot([e for e, _, _ in _serie], [c for _, _, c in _serie], ".", ms=3, alpha=0.35,
             label=f"{_m}: J del candidato")
    _ax.plot([e for e, _, _ in _serie], [b for _, b, _ in _serie], "-", lw=2, label=f"{_m}: mejor J")
_ax.axhline(_obj["train_initial"], color="gray", ls="--", lw=1, label="J entren. con E0")
_ax.set_xlabel("evaluaciones de J (presupuesto 300 por metodo)")
_ax.set_ylabel("J de entrenamiento")
_ax.set_ylim(_obj["train_tuned"] - 0.0003, _obj["train_initial"] + 0.0006)
_ax.set_title("Busqueda local de pesos: hill climbing frente a recocido simulado")
_ax.legend(fontsize=7, ncol=2)
_ax.grid(alpha=0.3)
plt.show()
