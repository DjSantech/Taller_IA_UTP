"""Mejora adicional: pesos de E(s) ajustados por busqueda local (apartado 7C).

Resumen del metodo (detalles y justificacion en apuntes/07c_ajuste.md y en la
bitacora T-01 .. T-xx):

1. DATOS. Posiciones muestreadas de partidas de autojuego entre jugadores
   epsilon-voraces: en cada ply el jugador juega al azar con probabilidad eps
   (Aleatorio) y si no juega el Voraz de un ply con SOLO material. Cada bando de
   cada partida sortea su eps en `eps_range`. Entrenamiento y prueba usan
   generadores de semillas distintos (`train_seed`, `test_seed`), se separan
   POR PARTIDA (nunca una misma partida en ambos lados) y se eliminan los
   duplicados por FEN (colocacion, turno, enroques y al paso): una posicion de
   prueba que tambien aparezca en entrenamiento se descarta.
   Se descartan: partidas truncadas (sin resultado oficial), posiciones
   terminales, posiciones en jaque y posiciones cuya ultima jugada fue una
   captura (intercambio a medias: E estatica mide mal el material).
2. ETIQUETA (estilo Texel). y = resultado final de la partida desde blancas:
   1 (ganan blancas), 0.5 (tablas), 0 (ganan negras). No viene de ningun motor.
   Es ruidosa: una posicion buena puede perderse por una jugada aleatoria
   posterior. El ruido se promedia con muchas posiciones; no se elimina.
3. OBJETIVO. J(w) = media[(sigmoide(E_w(s)/K) - y)^2] sobre ENTRENAMIENTO, con
   E_w = w . features(s) recortada a +-EVAL_BOUND (igual que `evaluate`).
   K (centipeones) se calibra UNA vez, con los pesos iniciales y solo con
   entrenamiento (seccion dorada sobre log K); despues queda fija.
4. ESCALA. wm = 100 queda FIJO: fija la unidad (centipeones). Si wm fuera
   libre, multiplicar todos los pesos y K por la misma constante daria el
   mismo J: la escala no estaria identificada.
5. BUSQUEDA LOCAL con presupuesto EXPLICITO de evaluaciones de J (cuenta todo:
   la evaluacion inicial y la calibracion de T0 del recocido):
   * Hill climbing por coordenadas: vecinos w_i +- paso_i de cada peso libre;
     se mueve al mejor vecino si mejora ESTRICTAMENTE; si ninguno mejora, los
     pasos se reducen a la mitad. Es el HC del Taller 2 (TSP) con otra vecindad.
   * Recocido simulado con semilla: perturba un peso al azar, acepta empeorar
     con prob. exp(-delta/T) (Metropolis), enfriamiento geometrico; T0 se
     calibra como en el Taller 2: T0 = -mediana(deltas>0)/ln(p0).
   Regla de eleccion fijada ANTES de mirar prueba: el resultado final es el de
   menor J de ENTRENAMIENTO entre HC y SA (empate -> HC).
6. REPORTE. Pesos inicial/final, J de entrenamiento y de prueba antes/despues,
   historial (CSV para graficar), ablacion por peso (devolver UN peso del
   ajustado al inicial) y una comparacion pareada en prueba agrupada por
   partida. Prueba solo se mira DESPUES de terminar la busqueda.

Salidas de `run_tuning`: resultados/pesos_ajustados.json (pesos y
configuracion), resultados/tuning_historial.csv, resultados/tuning_posiciones.csv
(posiciones de entrenamiento y prueba con su etiqueta) y
resultados/tuning_ablacion.csv. `load_tuned_evaluator()` devuelve
`Evaluator(pesos, "E*")` para la ablacion a nivel de partidas.
"""
from __future__ import annotations

import csv
import json
import math
import os
import platform
import random
import time
from dataclasses import asdict, dataclass

import chess
import numpy as np

from chess_ai.agents_basic import GreedyAgent, RandomAgent
from chess_ai.environment import EVAL_BOUND, game_outcome, search_outcome
from chess_ai.evaluation import DEFAULT_WEIGHTS, FEATURE_NAMES, PIECE_VALUES, Evaluator, features

_TUNE_WEIGHT_KEYS = ("wm", "wp", "wk", "wa")
_TUNE_ROUND = 3            # decimales de los pesos candidatos (lo guardado = lo evaluado)
_TUNE_IMPROVE_EPS = 1e-12  # mejora estricta minima en J


@dataclass
class TuningConfig:
    """Configuracion completa de una corrida (se guarda junto a los pesos)."""
    # --- datos ---
    train_games: int = 600
    test_games: int = 300
    train_seed: int = 31
    test_seed: int = 7919
    eps_range: tuple = (0.0, 0.5)
    max_plies: int = 200
    min_ply: int = 8          # no se muestrean las primeras jugadas (apertura casi fija)
    stride: int = 3           # una posicion cada `stride` plies (menos correlacion)
    # --- objetivo ---
    k_evals: int = 30         # evaluaciones de J usadas para calibrar K
    k_bounds: tuple = (20.0, 5000.0)
    # --- busqueda local ---
    initial_weights: tuple = DEFAULT_WEIGHTS
    free: tuple = (1, 2, 3)   # indices libres: wp, wk, wa (wm fijo = escala)
    bounds: tuple = ((100.0, 100.0), (0.0, 100.0), (0.0, 100.0), (0.0, 30.0))
    steps: tuple = (0.0, 8.0, 8.0, 2.0)
    min_step_ratio: float = 1.0 / 64.0
    max_evals: int = 300      # presupuesto de evaluaciones de J POR metodo
    sa_seed: int = 2026
    sa_p0: float = 0.5
    sa_calib: int = 20
    sa_t_final_ratio: float = 1e-3


@dataclass(frozen=True)
class TuningSample:
    """Una posicion etiquetada. `label` es el resultado final desde blancas."""
    fen: str
    label: float
    game_id: str
    ply: int


# ---------------------------------------------------------------- datos
def _tune_material_white(board: chess.Board) -> float:
    """Solo material (centipeones, desde blancas): evaluador de los jugadores de autojuego.

    Se usa SOLO material para generar partidas: asi los datos no presuponen los
    pesos posicionales (wp, wk, wa) que luego se ajustan.
    """
    total = 0.0
    for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        total += PIECE_VALUES[pt] * (chess.popcount(board.pieces_mask(pt, chess.WHITE))
                                     - chess.popcount(board.pieces_mask(pt, chess.BLACK)))
    return 100.0 * total


def _tune_position_key(board: chess.Board) -> str:
    """Clave de duplicado: colocacion, turno, enroques y al paso (sin relojes)."""
    return " ".join(board.fen().split()[:4])


def _tune_play_game(game_seed: int, cfg: TuningConfig):
    """Juega una partida eps-voraz contra eps-voraz.

    Devuelve (resultado, terminacion, posiciones) donde posiciones es una lista
    de (ply, fen, clave) muestreadas segun min_ply/stride y el filtro de quietud.
    resultado es None si la partida se trunca en `max_plies`.
    """
    rng = random.Random(game_seed)
    lo, hi = cfg.eps_range
    eps = {chess.WHITE: rng.uniform(lo, hi), chess.BLACK: rng.uniform(lo, hi)}
    greedy = GreedyAgent(_tune_material_white, name="VorazMaterial")
    rand = RandomAgent()
    board = chess.Board()
    sampled = []
    last_was_capture = False
    while True:
        outcome = game_outcome(board)
        if outcome is not None:
            return outcome.result(), outcome.termination.name.lower(), sampled
        ply = len(board.move_stack)
        if ply >= cfg.max_plies:
            return None, "truncated", sampled
        if (ply >= cfg.min_ply and (ply - cfg.min_ply) % cfg.stride == 0
                and not last_was_capture and not board.is_check()
                and search_outcome(board) is None):
            sampled.append((ply, board.fen(), _tune_position_key(board)))
        agent = rand if rng.random() < eps[board.turn] else greedy
        move = agent.choose(board, time_limit_s=0.0, seed=rng.randrange(2 ** 31)).move
        last_was_capture = board.is_capture(move)
        board.push(move)


def _tune_collect(n_games: int, base_seed: int, split: str, cfg: TuningConfig, exclude):
    """Juega `n_games` partidas y devuelve (muestras, info). `exclude`: claves prohibidas."""
    master = random.Random(base_seed)
    samples, seen = [], set()
    info = {"games": n_games, "truncated_games": 0, "results": {}, "terminations": {},
            "positions_sampled": 0, "duplicates_dropped": 0, "excluded_by_other_split": 0}
    for g in range(n_games):
        game_seed = master.randrange(2 ** 31)
        result, termination, positions = _tune_play_game(game_seed, cfg)
        info["terminations"][termination] = info["terminations"].get(termination, 0) + 1
        if result is None:
            info["truncated_games"] += 1
            continue
        info["results"][result] = info["results"].get(result, 0) + 1
        label = {"1-0": 1.0, "0-1": 0.0}.get(result, 0.5)
        game_id = f"{split}-{g:04d}"
        for ply, fen, key in positions:
            info["positions_sampled"] += 1
            if exclude is not None and key in exclude:
                info["excluded_by_other_split"] += 1
                continue
            if key in seen:
                info["duplicates_dropped"] += 1
                continue
            seen.add(key)
            samples.append(TuningSample(fen, label, game_id, ply))
    info["positions_kept"] = len(samples)
    return samples, info


def generate_tuning_data(cfg: TuningConfig | None = None) -> dict:
    """Posiciones de entrenamiento y prueba SEPARADAS (por partida y por FEN).

    Devuelve {"train": [TuningSample], "test": [TuningSample], "info": {...}}.
    Reproducible: depende solo de la configuracion (semillas incluidas).
    """
    cfg = cfg or TuningConfig()
    train, info_train = _tune_collect(cfg.train_games, cfg.train_seed, "train", cfg, None)
    train_keys = {_tune_position_key(chess.Board(s.fen)) for s in train}
    test, info_test = _tune_collect(cfg.test_games, cfg.test_seed, "test", cfg, train_keys)
    return {"train": train, "test": test, "info": {"train": info_train, "test": info_test}}


def tuning_feature_matrix(samples) -> tuple:
    """(F, y): matriz n x 4 de features (M, P, K, A) y vector de etiquetas."""
    feats = np.array([features(chess.Board(s.fen)) for s in samples], dtype=float).reshape(-1, 4)
    labels = np.array([s.label for s in samples], dtype=float)
    return feats, labels


# ---------------------------------------------------------------- objetivo
def tuning_objective(weights, feats, labels, k: float) -> float:
    """J = media[(sigmoide(E_w/K) - y)^2]. E_w se recorta a +-EVAL_BOUND como en `evaluate`."""
    e = np.clip(feats @ np.asarray(weights, dtype=float), -EVAL_BOUND, EVAL_BOUND)
    p = 1.0 / (1.0 + np.exp(-e / k))
    return float(np.mean((p - labels) ** 2))


def fit_scale_k(feats, labels, weights, bounds=(20.0, 5000.0), evals: int = 30):
    """Calibra K por seccion dorada sobre log K (solo datos de entrenamiento).

    Devuelve (K, evaluaciones usadas). J(K) es unimodal en la practica para
    esta familia; si no lo fuera, la seccion dorada da un minimo local.
    """
    a, b = math.log(bounds[0]), math.log(bounds[1])
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = b - inv_phi * (b - a), a + inv_phi * (b - a)
    fc = tuning_objective(weights, feats, labels, math.exp(c))
    fd = tuning_objective(weights, feats, labels, math.exp(d))
    used = 2
    while used < evals:
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - inv_phi * (b - a)
            fc = tuning_objective(weights, feats, labels, math.exp(c))
        else:
            a, c, fc = c, d, fd
            d = a + inv_phi * (b - a)
            fd = tuning_objective(weights, feats, labels, math.exp(d))
        used += 1
    return math.exp(c if fc < fd else d), used


# ---------------------------------------------------------------- busqueda local
def _tune_clip(value: float, lo: float, hi: float) -> float:
    return round(min(hi, max(lo, value)), _TUNE_ROUND)


def _tune_row(method, n_eval, cand, f_cand, f_cur, f_best, accepted, control):
    row = {"method": method, "eval": n_eval, "candidate_obj": f_cand,
           "current_obj": f_cur, "best_obj": f_best, "accepted": int(bool(accepted)),
           "control": control}
    row.update({k: v for k, v in zip(_TUNE_WEIGHT_KEYS, cand)})
    return row


def hill_climb_weights(objective_fn, initial, *, free, bounds, steps, max_evals: int,
                       min_step_ratio: float = 1.0 / 64.0, shrink: float = 0.5) -> dict:
    """Hill climbing por coordenadas con reduccion de paso y presupuesto explicito.

    Vecindad: para cada indice libre i, w_i + paso_i y w_i - paso_i (recortado a
    `bounds`; un vecino igual al actual no se evalua). Se evaluan los vecinos y
    se acepta el MEJOR si mejora estrictamente J (ascenso mas empinado). Si
    ninguno mejora, todos los pasos se multiplican por `shrink`; se para cuando
    todos son menores que paso_inicial * min_step_ratio (optimo local a esa
    resolucion) o cuando se agota el presupuesto. Cada llamada a
    `objective_fn` cuenta 1, incluida la del punto inicial. Nunca empeora J.
    """
    if max_evals < 1:
        raise ValueError("max_evals debe ser >= 1")
    current = [float(x) for x in initial]
    f_cur = objective_fn(tuple(current))
    evals = 1
    history = [_tune_row("HC", evals, current, f_cur, f_cur, f_cur, True, "inicio")]
    step = [float(s) for s in steps]
    min_step = [s * min_step_ratio for s in steps]
    stop = "presupuesto"
    while evals < max_evals:
        best_cand, best_f, best_row = None, f_cur, None
        control = "paso=" + "/".join(f"{step[j]:g}" for j in free)
        for i in free:
            for sgn in (1.0, -1.0):
                if evals >= max_evals:
                    break
                cand = list(current)
                cand[i] = _tune_clip(current[i] + sgn * step[i], *bounds[i])
                if cand[i] == current[i]:
                    continue
                f = objective_fn(tuple(cand))
                evals += 1
                if f < best_f - _TUNE_IMPROVE_EPS:
                    best_cand, best_f = cand, f
                    best_row = len(history)
                # best_obj de la fila = mejor J conocido hasta esta evaluacion
                history.append(_tune_row("HC", evals, cand, f, f_cur, best_f, False, control))
        if best_cand is not None:
            current, f_cur = best_cand, best_f
            history[best_row]["accepted"] = 1
        else:
            if evals >= max_evals:
                break
            step = [s * shrink for s in step]
            if all(step[i] < min_step[i] for i in free):
                stop = "optimo_local"
                break
    return {"method": "HC", "best_weights": tuple(current), "best_obj": f_cur,
            "initial_obj": history[0]["candidate_obj"], "evals": evals,
            "stop_reason": stop, "final_steps": tuple(step), "history": history}


def anneal_weights(objective_fn, initial, *, free, bounds, steps, max_evals: int, seed: int,
                   p0: float = 0.5, calib_samples: int = 20, t_final_ratio: float = 1e-3) -> dict:
    """Recocido simulado con semilla y presupuesto explicito (Metropolis).

    Propuesta: un indice libre al azar, w_i + U(-paso_i, paso_i), recortado.
    Calibracion (cuenta en el presupuesto): `calib_samples` vecinos del punto
    inicial; T0 = -mediana(deltas > 0)/ln(p0) (si no hay deltas positivos se
    usa la mediana de |delta| y, en ultimo caso, 1e-6). Enfriamiento
    geometrico tal que T llega a T0 * t_final_ratio al agotar el presupuesto.
    Se devuelve la MEJOR solucion vista (nunca peor que la inicial).
    """
    if max_evals < 1:
        raise ValueError("max_evals debe ser >= 1")
    rng = random.Random(seed)
    current = [float(x) for x in initial]
    f_cur = objective_fn(tuple(current))
    evals = 1
    best, f_best = list(current), f_cur
    history = [_tune_row("SA", evals, current, f_cur, f_cur, f_best, True, "inicio")]

    def propose(point):
        i = rng.choice(free)
        cand = list(point)
        cand[i] = _tune_clip(point[i] + rng.uniform(-steps[i], steps[i]), *bounds[i])
        return cand

    deltas = []
    for _ in range(min(calib_samples, max_evals - evals)):
        cand = propose(current)
        f = objective_fn(tuple(cand))
        evals += 1
        deltas.append(f - f_cur)
        if f < f_best - _TUNE_IMPROVE_EPS:
            best, f_best = cand, f
        history.append(_tune_row("SA", evals, cand, f, f_cur, f_best, False, "calibracion"))
    pos = sorted(d for d in deltas if d > 0) or sorted(abs(d) for d in deltas if d != 0)
    scale = pos[len(pos) // 2] if pos else 1e-6
    t0 = -scale / math.log(p0)
    remaining = max(1, max_evals - evals)
    alpha = t_final_ratio ** (1.0 / remaining)
    temp = t0
    while evals < max_evals:
        cand = propose(current)
        f = objective_fn(tuple(cand))
        evals += 1
        delta = f - f_cur
        accepted = delta <= 0 or rng.random() < math.exp(-delta / temp)
        if accepted:
            current, f_cur = cand, f
        if f < f_best - _TUNE_IMPROVE_EPS:
            best, f_best = cand, f
        history.append(_tune_row("SA", evals, cand, f, f_cur, f_best, accepted, f"T={temp:.3e}"))
        temp *= alpha
    return {"method": "SA", "best_weights": tuple(best), "best_obj": f_best,
            "initial_obj": history[0]["candidate_obj"], "evals": evals,
            "stop_reason": "presupuesto", "t0": t0, "seed": seed, "history": history}


# ---------------------------------------------------------------- reporte
def _tune_paired_by_game(samples, feats, labels, k, w_old, w_new) -> dict:
    """Diferencia pareada del error cuadratico (nuevo - viejo) promediada por PARTIDA.

    Las posiciones de una misma partida estan correlacionadas (misma etiqueta),
    por eso la unidad independiente es la partida, no la posicion. Negativo =
    los pesos nuevos predicen mejor. Se reporta media, error estandar entre
    partidas y fraccion de partidas donde mejora.
    """
    def sq_err(w):
        e = np.clip(feats @ np.asarray(w, dtype=float), -EVAL_BOUND, EVAL_BOUND)
        return (1.0 / (1.0 + np.exp(-e / k)) - labels) ** 2
    diff = sq_err(w_new) - sq_err(w_old)
    per_game = {}
    for s, d in zip(samples, diff):
        per_game.setdefault(s.game_id, []).append(float(d))
    means = np.array([np.mean(v) for v in per_game.values()], dtype=float)
    n = len(means)
    se = float(np.std(means, ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    return {"games": n, "mean_diff": float(np.mean(means)) if n else float("nan"),
            "se": se, "frac_games_improved": float(np.mean(means < 0)) if n else float("nan")}


def run_tuning(cfg: TuningConfig | None = None, out_dir: str | None = None,
               write: bool = True, verbose: bool = False) -> dict:
    """Corrida completa: datos -> K -> HC y SA (solo entrenamiento) -> reporte en prueba.

    Si `write`, guarda en `out_dir` (por defecto resultados/ del proyecto):
    pesos_ajustados.json, tuning_historial.csv, tuning_posiciones.csv y
    tuning_ablacion.csv. Devuelve el mismo diccionario que se guarda en el JSON
    (mas "history" y "data").
    """
    cfg = cfg or TuningConfig()
    t_start, cpu_start = time.perf_counter(), time.process_time()
    data = generate_tuning_data(cfg)
    t_data, cpu_data = time.perf_counter() - t_start, time.process_time() - cpu_start
    if not data["train"] or not data["test"]:
        raise ValueError("no hay posiciones suficientes: aumente train_games/test_games")
    f_tr, y_tr = tuning_feature_matrix(data["train"])
    f_te, y_te = tuning_feature_matrix(data["test"])
    w0 = tuple(float(x) for x in cfg.initial_weights)

    # --- solo entrenamiento a partir de aqui hasta elegir los pesos ---
    k, k_used = fit_scale_k(f_tr, y_tr, w0, cfg.k_bounds, cfg.k_evals)

    def obj_train(w):
        return tuning_objective(w, f_tr, y_tr, k)

    t_search = time.perf_counter()
    hc = hill_climb_weights(obj_train, w0, free=cfg.free, bounds=cfg.bounds, steps=cfg.steps,
                            max_evals=cfg.max_evals, min_step_ratio=cfg.min_step_ratio)
    sa = anneal_weights(obj_train, w0, free=cfg.free, bounds=cfg.bounds, steps=cfg.steps,
                        max_evals=cfg.max_evals, seed=cfg.sa_seed, p0=cfg.sa_p0,
                        calib_samples=cfg.sa_calib, t_final_ratio=cfg.sa_t_final_ratio)
    t_search = time.perf_counter() - t_search
    chosen = hc if hc["best_obj"] <= sa["best_obj"] else sa
    w_star = tuple(chosen["best_weights"])

    # --- recien ahora se mira prueba (los pesos ya estan elegidos) ---
    def obj_test(w):
        return tuning_objective(w, f_te, y_te, k)

    const = float(np.mean(y_tr))
    material_only = (w0[0], 0.0, 0.0, 0.0)
    ablation = []
    for i in cfg.free:
        w = list(w_star)
        w[i] = w0[i]
        ablation.append({"weight": _TUNE_WEIGHT_KEYS[i], "feature": FEATURE_NAMES[i],
                         "value_tuned": w_star[i], "value_initial": w0[i],
                         "train_obj": obj_train(w), "test_obj": obj_test(w)})
    report = {
        "weights": list(w_star),
        "weight_names": list(_TUNE_WEIGHT_KEYS),
        "feature_names": list(FEATURE_NAMES),
        "initial_weights": list(w0),
        "chosen_method": chosen["method"],
        "selection_rule": "menor J de entrenamiento entre HC y SA (empate -> HC); prueba no participa",
        "K": k,
        "k_calibration_evals": k_used,
        "objective": {
            "train_initial": obj_train(w0), "train_tuned": obj_train(w_star),
            "test_initial": obj_test(w0), "test_tuned": obj_test(w_star),
            "train_material_only": obj_train(material_only),
            "test_material_only": obj_test(material_only),
            "train_constant": float(np.mean((const - y_tr) ** 2)),
            "test_constant": float(np.mean((const - y_te) ** 2)),
            "constant_prediction": const,
        },
        "methods": {
            m["method"]: {"best_weights": list(m["best_weights"]), "train_obj": m["best_obj"],
                          "test_obj": obj_test(m["best_weights"]), "evals": m["evals"],
                          "stop_reason": m["stop_reason"],
                          **({"t0": m["t0"], "seed": m["seed"]} if m["method"] == "SA" else {}),
                          **({"final_steps": list(m["final_steps"])} if m["method"] == "HC" else {})}
            for m in (hc, sa)},
        "ablation": ablation,
        "paired_test_by_game": _tune_paired_by_game(data["test"], f_te, y_te, k, w0, w_star),
        "dataset": {"train_positions": len(data["train"]), "test_positions": len(data["test"]),
                    "train_label_mean": float(np.mean(y_tr)), "test_label_mean": float(np.mean(y_te)),
                    **data["info"]},
        "config": {k2: (list(v) if isinstance(v, tuple) else v) for k2, v in asdict(cfg).items()},
        "versions": {"python": platform.python_version(), "chess": chess.__version__,
                     "numpy": np.__version__},
        # pared (incluye esperas o suspension del equipo) y CPU del proceso (trabajo real)
        "timing_s": {"data": t_data, "search": t_search, "total": time.perf_counter() - t_start,
                     "cpu_data": cpu_data, "cpu_total": time.process_time() - cpu_start},
    }
    if verbose:
        print("K =", round(k, 2), "| pesos iniciales", w0, "-> ajustados", w_star,
              "(" + chosen["method"] + ")")
        print("J entrenamiento", report["objective"]["train_initial"], "->",
              report["objective"]["train_tuned"], "| J prueba",
              report["objective"]["test_initial"], "->", report["objective"]["test_tuned"])
    if write:
        out_dir = out_dir or os.path.dirname(TUNED_WEIGHTS_PATH)
        os.makedirs(out_dir, exist_ok=True)
        save_tuned_weights(report, os.path.join(out_dir, "pesos_ajustados.json"))
        _tune_write_csv(os.path.join(out_dir, "tuning_historial.csv"), hc["history"] + sa["history"])
        _tune_write_csv(os.path.join(out_dir, "tuning_ablacion.csv"), ablation)
        _tune_write_csv(os.path.join(out_dir, "tuning_posiciones.csv"),
                        [{"split": split, "game_id": s.game_id, "ply": s.ply, "label": s.label,
                          "fen": s.fen}
                         for split in ("train", "test") for s in data[split]])
    report["history"] = hc["history"] + sa["history"]
    report["data"] = data
    return report


def _tune_write_csv(path: str, rows) -> None:
    rows = list(rows)
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------- guardar / cargar
def _tune_project_root() -> str:
    """Raiz del proyecto: junto al paquete si hay __file__; si no (cuaderno), el cwd."""
    here = globals().get("__file__")
    if here:
        return os.path.dirname(os.path.dirname(os.path.abspath(here)))
    return os.getcwd()


TUNED_WEIGHTS_PATH = os.path.join(_tune_project_root(), "resultados", "pesos_ajustados.json")


def save_tuned_weights(report: dict, path: str | None = None) -> str:
    """Guarda pesos + configuracion + metricas en JSON (sin historial ni datos)."""
    path = path or TUNED_WEIGHTS_PATH
    payload = {k: v for k, v in report.items() if k not in ("history", "data")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def load_tuned_weights(path: str | None = None, missing_ok: bool = False):
    """Lee los pesos ajustados (tupla de 4). Con `missing_ok`, None si no existe el archivo."""
    path = path or TUNED_WEIGHTS_PATH
    if not os.path.exists(path):
        if missing_ok:
            return None
        raise FileNotFoundError(f"no existe {path}: ejecute run_tuning() primero")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    weights = tuple(float(x) for x in payload["weights"])
    if len(weights) != 4:
        raise ValueError("el archivo de pesos debe tener 4 pesos (wm, wp, wk, wa)")
    return weights


def load_tuned_evaluator(path: str | None = None, name: str = "E*") -> Evaluator:
    """`Evaluator(pesos ajustados, "E*")` para la ablacion E0 vs E* en partidas."""
    return Evaluator(load_tuned_weights(path), name)


# Pesos producidos por la ultima corrida real guardada (None si aun no se ha corrido).
# Leer un JSON pequeno es la unica accion a nivel de modulo; el ajuste no se ejecuta aqui.
TUNED_WEIGHTS = load_tuned_weights(missing_ok=True)
