# Bitácora N — Cuaderno, README y entrega

Formato: **Decisión · Alternativas · Por qué · Consecuencia**. Errores reales: **ERROR CORREGIDO**.

---

### N-01 · El cuaderno se construye desde el enunciado del primer commit
- **Decisión:** `tools/construir_cuaderno.py` lee el `.ipynb` del primer commit con `git show`, conserva sus 28 celdas (falla si no son 28) e inserta módulos, celdas propias y apuntes según un `PLAN` por índice de celda.
- **Alternativas:** editar el cuaderno a mano; partir del cuaderno ya construido.
- **Por qué:** es idempotente (reconstruir no duplica nada) y garantiza que el enunciado y el pseudocódigo siguen intactos. Es el esquema del Taller 2.
- **Consecuencia:** cualquier cambio se hace en `chess_ai/`, `celdas/` o `apuntes/` y se reconstruye.

### N-02 · Choques de nombres: módulo contra módulo y celda propia contra módulo
- **Decisión:** el constructor falla si dos módulos definen el mismo nombre de nivel superior **o** si una celda de `celdas/` redefine uno. Las variables de las celdas propias llevan prefijo `_`.
- **Por qué:** al concatenar en un solo espacio de nombres, una redefinición tapa a otra en silencio (una demo podría cambiar lo que usa el torneo).
- **Consecuencia:** también se eliminan los bloques `if __name__ == "__main__":`, que en un cuaderno sí se ejecutarían.

### N-03 · Arquitectura después del contrato, no antes
- **Decisión:** `04_arquitectura.md` y `environment` van después de la celda 8 (contrato) y no después de la 7, como sugería el plan inicial.
- **Por qué:** el texto dice que `SearchStats`, `Decision` y `Agent` son «los de la celda anterior»; así es verdad.

### N-04 · Celdas de demostración que solo afirman invariantes
- **Decisión:** las demos de cada implementación y las 7 pruebas de §8 usan `time_limit_s=0` o simulaciones fijas para todo lo que se afirma con `assert`. Lo que depende del reloj (profundidad alcanzada con 0,2 s) solo se imprime.
- **Por qué:** lección de S-17: una prueba de reloj falla según la carga de la máquina.
- **Consecuencia:** el cuaderno pasa igual con la máquina cargada (el torneo corría en paralelo).

### N-05 · Experimentos largos: se cargan; Exp. 1 y una partida se repiten en vivo
- **Decisión:** el Exp. 1 se re-ejecuta y se compara fila a fila (valor y nodos) con `resultados/exp1_ahorro.csv`. Torneo, ablación y Exp. 4 se cargan de `resultados/`, y se repite en vivo una muestra del Exp. 4 y una partida corta. `EJECUTAR_COMPLETO = False` permite repetir el torneo en el cuaderno.
- **Alternativas:** repetir todo (horas); solo mostrar imágenes PNG.
- **Por qué:** el cuaderno debe correr en minutos y demostrar que los archivos salen de este mismo código. Las figuras se regeneran desde los CSV, no desde imágenes.
- **Consecuencia:** si faltan los archivos, las celdas avisan en vez de fallar; basta reconstruir y ejecutar cuando existan.

### N-06 · Cifras que el constructor calcula en vez de escribirse a mano
- **Decisión:** el número de pruebas de la suite (`{{N_PRUEBAS}}`) se cuenta con `pytest --collect-only` al construir; `{{Q10}}` se reemplaza por `apuntes/12_q10.md` si existe.
- **Por qué:** un número escrito a mano queda desactualizado cuando se agregan pruebas.

### N-07 · El constructor no aborta si falta un archivo del plan
- **Decisión:** los faltantes (resultados del otro frente de trabajo) se avisan al final.
- **Por qué:** el torneo se corría en paralelo; el cuaderno se tiene que poder construir y probar antes.

### N-08 · Las celdas no muestran rutas personales
- **Decisión:** la celda de entorno imprime solo el nombre del entorno virtual (`sys.prefix`), no la ruta completa; README y apuntes usan `<usuario>`.
- **Consecuencia:** queda una ruta personal en `apuntes/bitacora_D.md` (D-03), y por eso también en `BITACORA.md`; se reportó para corregirla en esa bitácora.

### N-09 · Posiciones de prueba propias verificadas por el programa antes de fijarlas
- **Decisión:** las dos posiciones de reglas (captura al paso ilegal por clavada; enroque corto prohibido) se comprueban con `is_valid()` y con `legal_moves` dentro de la celda.
- **Por qué:** lección de S-16 e I-14: una posición «conocida» también se verifica.
