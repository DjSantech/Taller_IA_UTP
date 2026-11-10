# ===== 7.A y 7.B: microproblema de la torre (BFS, DFS, UCS, A*, voraz) =====
import matplotlib.pyplot as plt


def _imprimir_filas(filas, extra=()):
    cols = ("algoritmo", "modelo", "longitud", "costo_unitario", "costo_distancia", "expandidos",
            "generados", "frontera_max") + tuple(extra)
    print("  " + " | ".join(f"{c[:12]:>12}" for c in cols) + " | ruta")
    for f in filas:
        print("  " + " | ".join(f"{str(f[c])[:12]:>12}" for c in cols) + f" | {f['ruta']}")


_tablas_torre = {}
for _nombre, _prob in rook_scenarios().items():
    _tablas_torre[_nombre] = rook_results_table(_prob)
    _ucs_u = rook_ucs(_prob.with_cost("unit"))
    print(f"\n=== {_nombre} (BFS y DFS ignoran el costo; UCS, A* y voraz usan el modelo de la fila) ===")
    print(rook_board_text(_prob, _ucs_u.path))
    _imprimir_filas(_tablas_torre[_nombre])

# Longitud frente a costo con obstaculos: menos movimientos != menos casillas.
_obs = rook_scenarios()["a1->h8 obstaculos"]
_ru, _rd = rook_ucs(_obs.with_cost("unit")), rook_ucs(_obs.with_cost("distance"))
assert _ru.length < _rd.length and _rd.cost_distance < _ru.cost_distance
print(f"\nCon obstaculos: UCS unitario {_ru.length} movimientos / {_ru.cost_distance} casillas; "
      f"UCS por distancia {_rd.length} movimientos / {_rd.cost_distance} casillas.")

print("\nDFS depende del orden de las acciones (el optimo no):")
for _f in rook_dfs_order_demo():
    print(f"  {_f['orden']:<24} longitud {_f['longitud']:>2}, expandidos {_f['expandidos']:>2}, "
          f"optimo (UCS unitario) {_f['ucs_unit_cost']}")

print("\n7.B Verificacion exhaustiva de las heuristicas contra h* (Dijkstra hacia atras):")
for _etq, _h, _modelo in (("consigna", h_rook_lines, "unit"), ("Manhattan", h_manhattan, "distance"),
                          ("Manhattan", h_manhattan, "unit")):
    for _esc in ("a1->h8", "a1->h8 obstaculos"):
        _c = rook_check_heuristic(rook_scenarios()[_esc].with_cost(_modelo), _h)
        print(f"  {_etq:<10} costo {_modelo:<9} {_esc:<18} estados={_c['states']:>2}  "
              f"h>h*: {len(_c['not_admissible']):>2}  exceso max: {_c['max_overestimate']:>2}  "
              f"inconsistentes: {_c['inconsistent']:>3}")

_ce = rook_unit_manhattan_counterexample()
print(f"\nContraejemplo (Manhattan con costo unitario): BFS {_ce['optimal'].route_text()} "
      f"({_ce['optimal'].length} mov.) frente a A*(Manhattan) {_ce['manhattan'].route_text()} "
      f"({_ce['manhattan'].length} mov.); h(a1)={_ce['a1_h']} y h*(a1)={_ce['a1_true']}.")
print(rook_board_text(_ce["problem"], _ce["manhattan"].path))

_fig = plot_rook_expansions(_tablas_torre)      # misma figura que resultados/torre_expansiones.png
plt.show()
