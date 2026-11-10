"""Registro unico de los seis agentes: lo usan la interfaz, el torneo y los experimentos.

Cada fabrica recibe una configuracion con atributos `depth`, `time_limit_s`, `seed`
y `simulations` (por ejemplo `controller.AgentConfig`) y devuelve un agente NUEVO,
asi ninguna partida comparte estado interno (killers, arbol de MCTS) con otra.

* Minimax y Alfa-beta usan la profundidad configurada (profundidad fija: ignoran
  el plazo; el controlador registra los excesos, D-10).
* Alfa-beta es el NATURAL (sin ordenar): la ordenacion es justamente lo que agrega
  el agente mejorado, y asi la comparacion entre ambos la aisla.
* Alfa-beta mejorado usa el plazo (profundizacion iterativa).
* MCTS usa simulaciones fijas si `simulations` no es None (reproducible); si es
  None, el plazo.
"""
from __future__ import annotations

from chess_ai.agents_basic import RandomAgent, GreedyAgent
from chess_ai.search import MinimaxAgent, AlphaBetaAgent, AlphaBetaImprovedAgent
from chess_ai.mcts import MCTSAgent

AGENT_NAMES = ("Aleatorio", "Voraz", "Minimax", "Alfa-beta", "Alfa-beta mejorado", "MCTS")

AGENT_FACTORIES = {
    "Aleatorio": lambda cfg: RandomAgent(),
    "Voraz": lambda cfg: GreedyAgent(),
    "Minimax": lambda cfg: MinimaxAgent(depth=cfg.depth),
    "Alfa-beta": lambda cfg: AlphaBetaAgent(depth=cfg.depth, ordering=False),
    "Alfa-beta mejorado": lambda cfg: AlphaBetaImprovedAgent(),
    "MCTS": lambda cfg: MCTSAgent(simulations=cfg.simulations),
}


def make_agent(label: str, config):
    """Crea un agente del registro; error claro si la etiqueta no existe."""
    if label not in AGENT_FACTORIES:
        raise KeyError(f"agente desconocido: {label!r}; opciones: {', '.join(AGENT_NAMES)}")
    return AGENT_FACTORIES[label](config)
