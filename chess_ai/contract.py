"""Contrato comun SUMINISTRADO por el enunciado (seccion 4), copiado sin cambios.

En el cuaderno estas clases ya estan definidas en la celda del profesor, por eso
el constructor del cuaderno NO inserta este modulo: solo existe para que el
paquete se pueda importar y probar con pytest fuera de Jupyter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SearchStats:
    nodes: int = 0
    leaves: int = 0
    cutoffs: int = 0
    completed_depth: int = 0
    elapsed_s: float = 0.0
    simulations: int = 0


@dataclass
class Decision:
    move: object | None
    score: float | None
    stats: SearchStats


class Agent(Protocol):
    name: str

    def choose(self, board, *, time_limit_s: float, seed: int) -> Decision:
        """Recibe copia con historia. Devuelve jugada legal y metricas."""
        ...
