import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Posiciones del enunciado (seccion 8), copiadas tal cual para las pruebas.
POSITIONS = {
    "initial": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "castling": "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "promotion": "7k/P7/8/8/8/8/8/7K w - - 0 1",
    "en_passant": "7k/8/8/3pP3/8/8/8/7K w - d6 0 2",
    "mate_in_one": "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
    "checkmate": "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1",
    "stalemate": "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
}
