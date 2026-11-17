# ===== Cambio de parametros: prediccion escrita ANTES de ejecutar, y comprobacion =====
predicciones = [
    ("rotar el orden 2 posiciones -> primer evento despues del inicio",
     ("avance", 2, 1), lambda: resolver(5, (0, 0), orden=rotar(DESPLAZAMIENTOS, 2))[2][1]),
    ("presupuesto=30 en 5x5 -> estado y ultimo evento",
     ("límite", ("límite", 0, 0)), lambda: (lambda r: (r[0], r[2][-1]))(resolver(5, (0, 0), presupuesto=30))),
    ("6x6 cerrado desde (1, 1) con Warnsdorff -> ¿hay circuito?",
     "éxito", lambda: resolver(6, (1, 1), estrategia="warnsdorff", cerrado=True)[0]),
    ("5x5 cerrado -> ¿hay circuito? (argumento de paridad)",
     "fracaso", lambda: resolver(5, (0, 0), cerrado=True, presupuesto=10_000_000)[0]),
]
for texto, predicho, ejecutar in predicciones:
    obtenido = ejecutar()
    print(f"{texto}\n   predicho: {predicho}\n   obtenido: {obtenido}   "
          f"{'OK' if obtenido == predicho else 'DISTINTO'}")
    assert obtenido == predicho
