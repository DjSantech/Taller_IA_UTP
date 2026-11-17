# ===== Reto 3: comparacion reproducible de estrategias (mismo presupuesto y orden) =====
from IPython.display import Markdown

# >>> Caso que asigna el docente en clase: cambie estos tres valores y vuelva a ejecutar. <<<
ASIGNADO_N = 6
ASIGNADO_INICIO = (0, 0)
ASIGNADO_ROTACION = 0          # orden = rotar(DESPLAZAMIENTOS, ASIGNADO_ROTACION)
PRESUPUESTO = 50_000

orden_asignado = rotar(DESPLAZAMIENTOS, ASIGNADO_ROTACION)
print("Orden asignado:", orden_asignado)
filas = comparar_estrategias([
    ("base", 5, (0, 0), DESPLAZAMIENTOS, False),
    ("asignado", ASIGNADO_N, ASIGNADO_INICIO, orden_asignado, False),
], presupuesto=PRESUPUESTO)
display(Markdown(tabla_markdown(filas)))

print("Modo cerrado, mismo presupuesto:")
display(Markdown(tabla_markdown(comparar_estrategias([
    ("5x5 cerrado", 5, (0, 0), DESPLAZAMIENTOS, True),
    ("6x6 cerrado", 6, (1, 1), DESPLAZAMIENTOS, True),
], presupuesto=PRESUPUESTO))))

estado_5c, _, _, exp_5c = resolver(5, (0, 0), cerrado=True, presupuesto=10_000_000)
print(f"5x5 cerrado con presupuesto amplio: {estado_5c} tras agotar el arbol completo "
      f"({exp_5c:,} expansiones).".replace(",", "."))

print("\nEfecto del orden en 5x5 desde (0, 0) (estrategia fija):")
for k in range(8):
    e, _, t, x = resolver(5, (0, 0), orden=rotar(DESPLAZAMIENTOS, k))
    print(f"  rotacion {k}: {e:7s} {x:>6} expansiones  {contar_eventos(t, 'retroceso'):>6} retrocesos")
