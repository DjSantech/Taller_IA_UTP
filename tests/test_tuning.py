import json
import math
import os

import chess
import numpy as np
import pytest

from chess_ai.environment import search_outcome
from chess_ai.evaluation import DEFAULT_WEIGHTS, evaluate
from chess_ai.tuning import (TuningConfig, anneal_weights, fit_scale_k, generate_tuning_data,
                             hill_climb_weights, load_tuned_evaluator, load_tuned_weights,
                             run_tuning, tuning_feature_matrix, tuning_objective)

SMALL = TuningConfig(train_games=6, test_games=4, max_evals=40, k_evals=12, sa_calib=5)
BOUNDS = ((100.0, 100.0), (0.0, 100.0), (0.0, 100.0), (0.0, 30.0))
STEPS = (0.0, 8.0, 8.0, 2.0)


def _key(fen):
    return " ".join(fen.split()[:4])


@pytest.fixture(scope="module")
def small_data():
    return generate_tuning_data(SMALL)


class _Counted:
    """Objetivo sintetico cuadratico (minimo en (100, 40, 3, 7)) que cuenta sus llamadas."""

    def __init__(self):
        self.calls = 0

    def __call__(self, w):
        self.calls += 1
        target = (100.0, 40.0, 3.0, 7.0)
        return sum((a - b) ** 2 for a, b in zip(w, target))


# ---------------------------------------------------------------- datos
def test_train_and_test_are_separated(small_data):
    train, test = small_data["train"], small_data["test"]
    assert train and test
    assert not {_key(s.fen) for s in train} & {_key(s.fen) for s in test}
    assert not {s.game_id for s in train} & {s.game_id for s in test}
    # sin duplicados dentro de cada conjunto
    assert len({_key(s.fen) for s in train}) == len(train)
    assert len({_key(s.fen) for s in test}) == len(test)


def test_positions_are_non_terminal_quiet_and_labelled_by_result(small_data):
    for s in small_data["train"] + small_data["test"]:
        b = chess.Board(s.fen)
        assert search_outcome(b) is None and not b.is_check()
        assert s.label in (0.0, 0.5, 1.0)
        assert s.ply >= SMALL.min_ply


def test_dataset_is_reproducible(small_data):
    again = generate_tuning_data(SMALL)
    assert again["train"] == small_data["train"] and again["test"] == small_data["test"]


# ---------------------------------------------------------------- objetivo
def test_objective_uses_the_same_E_as_evaluate(small_data):
    samples = small_data["train"][:20]
    feats, _ = tuning_feature_matrix(samples)
    for s, row in zip(samples, feats):
        assert float(row @ np.array(DEFAULT_WEIGHTS)) == pytest.approx(evaluate(chess.Board(s.fen)))


def test_fit_scale_k_recovers_known_scale():
    rng = np.random.default_rng(0)
    m = rng.uniform(-10, 10, size=4000)
    feats = np.column_stack([m, np.zeros_like(m), np.zeros_like(m), np.zeros_like(m)])
    labels = 1.0 / (1.0 + np.exp(-100.0 * m / 300.0))      # K verdadero = 300
    k, used = fit_scale_k(feats, labels, DEFAULT_WEIGHTS, evals=40)
    assert used == 40 and k == pytest.approx(300.0, rel=0.02)


# ---------------------------------------------------------------- busqueda local
@pytest.mark.parametrize("budget", [1, 7, 60, 500])
def test_hill_climb_respects_budget_and_never_worsens(budget):
    obj = _Counted()
    r = hill_climb_weights(obj, DEFAULT_WEIGHTS, free=(1, 2, 3), bounds=BOUNDS, steps=STEPS,
                           max_evals=budget)
    assert obj.calls == r["evals"] <= budget
    assert r["best_obj"] <= r["initial_obj"]
    best = [row["best_obj"] for row in r["history"]]
    assert all(b2 <= b1 for b1, b2 in zip(best, best[1:]))  # el mejor conocido nunca sube
    assert r["best_weights"][0] == 100.0                     # wm fijo (escala)
    for (lo, hi), w in zip(BOUNDS, r["best_weights"]):
        assert lo <= w <= hi


def test_hill_climb_reaches_optimum_of_quadratic():
    r = hill_climb_weights(_Counted(), DEFAULT_WEIGHTS, free=(1, 2, 3), bounds=BOUNDS,
                           steps=STEPS, max_evals=1000)
    assert r["stop_reason"] == "optimo_local"
    assert r["best_weights"] == pytest.approx((100.0, 40.0, 3.0, 7.0), abs=0.2)


@pytest.mark.parametrize("budget", [1, 10, 200])
def test_annealing_respects_budget_seed_and_never_worsens(budget):
    obj = _Counted()
    kw = dict(free=(1, 2, 3), bounds=BOUNDS, steps=STEPS, max_evals=budget, seed=5, calib_samples=5)
    r = anneal_weights(obj, DEFAULT_WEIGHTS, **kw)
    assert obj.calls == r["evals"] <= budget
    assert r["best_obj"] <= r["initial_obj"]
    assert anneal_weights(_Counted(), DEFAULT_WEIGHTS, **kw)["best_weights"] == r["best_weights"]


def test_local_search_on_real_training_objective_never_worsens(small_data):
    feats, labels = tuning_feature_matrix(small_data["train"])
    k, _ = fit_scale_k(feats, labels, DEFAULT_WEIGHTS, evals=10)

    def obj(w):
        return tuning_objective(w, feats, labels, k)
    r = hill_climb_weights(obj, DEFAULT_WEIGHTS, free=(1, 2, 3), bounds=BOUNDS, steps=STEPS,
                           max_evals=30)
    assert r["best_obj"] <= obj(DEFAULT_WEIGHTS) and r["evals"] <= 30


# ---------------------------------------------------------------- corrida y archivos
def test_run_tuning_writes_files_and_loads_evaluator(tmp_path):
    report = run_tuning(SMALL, out_dir=str(tmp_path))
    for name in ("pesos_ajustados.json", "tuning_historial.csv", "tuning_ablacion.csv",
                 "tuning_posiciones.csv"):
        assert os.path.exists(tmp_path / name)
    path = str(tmp_path / "pesos_ajustados.json")
    with open(path, encoding="utf-8") as fh:
        saved = json.load(fh)
    assert saved["config"]["train_seed"] == SMALL.train_seed and "history" not in saved
    assert saved["objective"]["train_tuned"] <= saved["objective"]["train_initial"]
    assert saved["methods"]["HC"]["evals"] <= SMALL.max_evals
    assert saved["methods"]["SA"]["evals"] <= SMALL.max_evals
    assert [a["weight"] for a in saved["ablation"]] == ["wp", "wk", "wa"]
    ev = load_tuned_evaluator(path)
    assert ev.name == "E*" and ev.weights == tuple(report["weights"])
    assert load_tuned_weights(path) == tuple(report["weights"])
    assert math.isfinite(ev(chess.Board()))


def test_missing_weights_file(tmp_path):
    missing = str(tmp_path / "no_existe.json")
    assert load_tuned_weights(missing, missing_ok=True) is None
    with pytest.raises(FileNotFoundError):
        load_tuned_evaluator(missing)
