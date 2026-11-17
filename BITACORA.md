# Bitácora — Taller 4 (backtracking y recorrido del caballo)

**Integrantes:** Santiago Guevara y Januar Mena. Formato: **Decisión · Alternativas · Por qué · Consecuencia**.

### B-01 · Mismo esquema de los talleres anteriores
- El código vive en `caballo/solver.py` con pruebas `pytest`. `tools/construir_cuaderno.py` parte del enunciado del primer commit, **completa** la celda plantilla de los Retos 1–3 con ese código y quita los comentarios de `probar_saltos()` y `probar_resolver()`, como pide el enunciado.
- Rama `taller-4` del repositorio `DjSantech/Taller_IA_UTP`. Entorno virtual `ia-taller4`, fuera de OneDrive.

### B-02 · Expansión contada al entrar a `buscar()`
- **Alternativas:** contar al generar hijos; contar solo los nodos internos.
- **Por qué:** el contrato cuenta «cada vez que entra a procesar un camino parcial, incluida la raíz y los casos base». La consecuencia útil es que `expansiones == avances + 1`, que una prueba verifica.

### B-03 · Presupuesto revisado antes de cada avance, no al entrar
- **Alternativas:** devolver límite al entrar a una llamada que ya no tiene presupuesto.
- **Por qué:** con esa alternativa se registraría un avance que no se procesa. Las pruebas del profesor con `presupuesto=1` y `presupuesto=2` fijan exactamente este punto: `[inicio, límite]` y `[inicio, avance, retroceso, límite]`.
- **Consecuencia:** una llamada ya contada puede reconocer el caso base exitoso aunque haya gastado la última expansión.

### B-04 · Ante un límite se desenrolla con retrocesos y no se prueban más destinos
- La traza registra cada retroceso hasta la raíz, así que el último evento es siempre `("límite", *inicio)`.

### B-05 · Warnsdorff con `sorted` estable
- El grado se calcula con el destino marcado como visitado. Gracias a la estabilidad de `sorted`, los empates conservan el orden recibido; una prueba lo comprueba rotando el orden.

### B-06 · Validación externa con `TRAZA_DEMO`
- Nuestra traza del 5×5 desde (0, 0) con el orden base es idéntica, evento por evento, a la `TRAZA_DEMO` del enunciado (58 eventos). La prueba busca la celda por su contenido, no por su índice, para que siga funcionando cuando el constructor inserta celdas antes.

### B-07 · ERROR CORREGIDO: circuito cerrado en 6×6 desde (0, 0)
- **Qué pasó:** la primera versión de la prueba del modo cerrado usaba 6×6 desde (0, 0) con Warnsdorff y daba **límite**, no éxito.
- **Diagnóstico:** Warnsdorff ordena por grado, pero no tiene en cuenta el salto de regreso. Desde (0, 0) se queda sin presupuesto incluso con 2 000 000 de expansiones. Desde (1, 1) encuentra el circuito en 36.
- **Corrección:** la prueba usa (1, 1), y el texto del Reto 3 explica que Warnsdorff no garantiza el cierre.
- **Lección:** una heurística de orden no cambia **qué** soluciones existen, solo **cuándo** se encuentran.

### B-08 · ERROR CORREGIDO: traza manual con el marco equivocado
- **Qué pasó:** en el primer borrador de la traza manual atribuimos la alternativa del evento 26 al marco de (2, 2).
- **Diagnóstico:** al calcular la lista de cada marco con `saltos_legales` vimos que (2, 2) ya había retrocedido en el evento 25. Quien elige (1, 1) es el marco de (3, 0), cuya lista era `[(2,2), (1,1)]`.
- **Corrección:** tabla rehecha con las listas de cada marco calculadas en código.
- **Lección:** es justo el tipo de pregunta de la sustentación: ¿qué marco elige el siguiente destino?

### B-09 · 5×5 cerrado: comprobación experimental de la paridad
- Con un presupuesto amplio, el árbol completo se agota en 1 735 079 expansiones (unos 4 s) y el resultado es **fracaso**, como predice el argumento de colores.
