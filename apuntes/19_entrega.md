### Lista de entrega: estado y evidencia

| | Punto | Evidencia en este cuaderno |
|---|---|---|
| ✅ | El cuaderno se ejecuta desde un kernel reiniciado con archivos de datos locales | `tools/ejecutar_cuaderno.py` lo ejecuta de arriba abajo en un kernel nuevo y falla en la primera celda con error; los datos están en `datos/` |
| ✅ | Las cuatro instancias obligatorias están auditadas y los pesos son oficiales | §3: fichas, fórmulas EUC_2D y ATT comparadas en todos los pares, rutas óptimas oficiales con costo exacto |
| ✅ | Los cinco algoritmos tienen implementación propia y pruebas pertinentes | `tsp/astar.py`, `rbfs.py`, `hc.py`, `sa.py`, `ga.py`; batería de §13 y `tests/` |
| ✅ | El costo incluye cierre y todas las rutas entregadas son permutaciones válidas | `tour_cost` único; las celdas de las escalas A y B validan cada `RunResult` (ruta válida, costo recalculado, gap no negativo) |
| ✅ | Hay pruebas pequeñas de optimalidad para A\* y RBFS | §13 (enumeración exhaustiva) y escala A (Held-Karp como tercer certificado, invarianza del origen) |
| ✅ | Se distinguen swap, 2-opt y mutación por inversión | §1.A y §6.2 (swap contra 2-opt con un ejemplo), §9, §12 |
| ✅ | Los registros incluyen semillas, parámetros, presupuestos y causas de parada | `RunResult` y `resultados/*.csv` y `*.json` |
| ✅ | Las comparaciones estadísticas incluyen las diez semillas y los resultados censurados | tablas de §14: «válidas/previstas» con censuradas, figuras 3 y 4 |
| ✅ | Las gráficas proceden de registros y las conclusiones remiten a evidencia | §15.2 y §16: cada respuesta cita su tabla, figura o prueba |
| ✅ | Se entrega el cuaderno con salidas guardadas y los datos o instrucciones de descarga | este archivo; `datos/` y `tools/descargar_datos.py` |
| ⬜ | Los integrantes pueden explicar cualquier fragmento y hacer un cambio durante la sustentación | se comprueba en la sustentación; guías de estudio por etapa en `estudio/` |
