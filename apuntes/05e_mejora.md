### Mejora adicional elegida: pesos de E ajustados por búsqueda local

De las tres mejoras que propone el enunciado (quietud; tabla de transposición; evaluación con pesos ajustados por búsqueda local) elegimos la **tercera**. Así, la misma implementación cuenta para la mejora con ablación y para la actividad 7C. Lo que hay en cada lugar del cuaderno:

| Qué | Dónde |
|---|---|
| Código del ajuste: datos de autojuego, objetivo, hill climbing y recocido con presupuesto | celda siguiente (`chess_ai/tuning.py`) |
| Pesos iniciales/finales, entrenamiento frente a prueba, ablación por peso y sobreajuste | sección 7C (resultados guardados en `resultados/pesos_ajustados.json`) |
| Ablación en partidas: el mismo alfa-beta con $E_0$ y con $E^*$, todo lo demás fijo | sección 9, Experimento 3 |

La quietud quedó como una **opción apagada** del alfa-beta mejorado (`quiescence=False`). No la presentamos como mejora porque cambia el árbol y sus valores ya no se comparan con minimax de profundidad fija (bitácora S-11).

Después del ajuste va el **registro de agentes** (`chess_ai/registry.py`): una sola tabla `AGENT_FACTORIES` con los seis agentes, que usan tanto la interfaz como el torneo. Así, lo que se juega en la interfaz es exactamente lo que se mide en el torneo. Minimax y alfa-beta usan la profundidad configurada; alfa-beta (el «natural», sin ordenar) se distingue del mejorado justamente por la ordenación y la profundización con plazo; MCTS usa simulaciones fijas si se indican y, si no, el plazo.
