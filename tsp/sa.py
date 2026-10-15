# -*- coding: utf-8 -*-
"""Simulated Annealing (recocido simulado) sobre la vecindad 2-opt (seccion 11).

Misma vecindad que HC (comparacion controlada 11.1): un par valido uniforme de
`random_valid_pair`, delta O(1) con `two_opt_delta`. Se acepta delta <= 0 siempre
y delta > 0 con probabilidad exp(-delta/T) (criterio de Metropolis).

Dos objetos distintos: la ruta ACTUAL (puede empeorar) y la MEJOR observada
(copia independiente, solo se reemplaza con una mejora estricta). Se devuelve la
mejor. Enfriamiento geometrico por bloques: T <- alpha*T cada `steps` propuestas.

Contabilidad: cada propuesta evaluada = 1 evaluacion; se consulta el Budget ANTES
de evaluar. El costo de la ruta inicial no se cuenta (igual que en HC). El trabajo
de calibrar T0 SI se cuenta: se pasa como `initial_evals`.
"""
import math
import statistics

from tsp.modelo import (STOP_COOLED, OPT_NOT_PROVEN, RunResult, gap_percent,
                        tour_cost)
from tsp.vecindad import random_valid_pair, two_opt_apply_inplace, two_opt_delta

MAX_SERIES_POINTS = 2000


def calibrate_t0(inst, route, rng, p0, samples=200):
    """T0 = -mediana(deltas positivos) / ln(p0), con `samples` movimientos 2-opt
    aleatorios evaluados sobre `route` (la ruta NO se modifica).

    Con ese T0 un empeoramiento "tipico" (la mediana) se acepta con
    probabilidad p0 al comenzar. Devuelve (T0, evals_used) con evals_used =
    samples (trabajo de calibracion que el llamador debe sumar al presupuesto).

    Alternativa si NO hay deltas positivos (ruta en un optimo local de la
    muestra, o matriz degenerada): se usa la mediana de |delta| de los deltas
    distintos de cero; si tampoco los hay, la mediana de los pesos positivos de
    las aristas de la ruta; y como ultimo recurso 1.0. Asi T0 siempre es > 0."""
    if not 0.0 < p0 < 1.0:
        raise ValueError("p0 debe estar en (0, 1)")
    D = inst.D
    deltas = []
    for _ in range(samples):
        i, j = random_valid_pair(len(route), rng)
        deltas.append(two_opt_delta(D, route, i, j))
    positivos = [d for d in deltas if d > 0]
    if positivos:
        escala = statistics.median(positivos)
    else:
        no_cero = [abs(d) for d in deltas if d != 0]
        if no_cero:
            escala = statistics.median(no_cero)
        else:
            aristas = [D[route[k]][route[(k + 1) % len(route)]] for k in range(len(route))]
            aristas = [w for w in aristas if w > 0]
            escala = statistics.median(aristas) if aristas else 1.0
    return -escala / math.log(p0), samples


class _Series:
    """Series muestreadas con tope de puntos: al pasar de MAX_SERIES_POINTS se
    descarta un punto de cada dos y se duplica el intervalo de registro."""

    def __init__(self):
        self.x, self.temperature, self.current_cost, self.accept_rate_worse = [], [], [], []
        self.every = 1
        self.windows = 0

    def add(self, x, t, c, rate, force=False):
        self.windows += 1
        if not force and (self.windows - 1) % self.every != 0:
            return
        self.x.append(x)
        self.temperature.append(t)
        self.current_cost.append(c)
        self.accept_rate_worse.append(rate)
        if len(self.x) > MAX_SERIES_POINTS:
            self.x = self.x[::2]
            self.temperature = self.temperature[::2]
            self.current_cost = self.current_cost[::2]
            self.accept_rate_worse = self.accept_rate_worse[::2]
            self.every *= 2


def simulated_annealing(inst, initial_route, budget, rng, T0, Tmin, alpha, steps,
                        keep_history=False, window=500, initial_evals=0):
    """Recocido simulado desde `initial_route` (no se modifica).

    `initial_evals`: evaluaciones ya gastadas (calibracion de T0); cuentan en
    candidate_evaluations y contra budget.max_evals.

    extras:
      "series_evals", "temperature", "current_cost", "accept_rate_worse": series
          alineadas, un punto por ventana de `window` propuestas (maximo ~2000
          puntos; si hay mas se adelgazan). accept_rate_worse = aceptados /
          propuestos entre los empeoramientos de ESA ventana (None si no hubo).
      "accepted", "accepted_worse", "proposed_worse", "final_temperature",
      "final_current_route", "final_current_cost": para auditar la diferencia
          entre ruta actual y mejor.
      "route_history" (si keep_history): [(ruta, costo, evals), ...] con la ruta
          inicial y cada NUEVA mejor ruta (no cada movimiento aceptado)."""
    if not (T0 > 0 and Tmin > 0 and 0 < alpha < 1 and steps >= 1 and window >= 1):
        raise ValueError("se exige T0>0, Tmin>0, 0<alpha<1, steps>=1, window>=1")
    D = inst.D
    n = inst.n
    budget.start()
    current = list(initial_route)
    cur_cost = tour_cost(D, current)
    best = list(current)
    best_cost = cur_cost
    evals = initial_evals
    trace = [(evals, best_cost, budget.elapsed())]
    history = [(list(best), best_cost, evals)] if keep_history else None
    series = _Series()
    series.add(evals, T0, cur_cost, None)

    T = T0
    accepted = accepted_worse = proposed_worse = 0
    w_prop = w_worse = w_worse_acc = 0
    stop = None
    exp = math.exp
    rand = rng.random

    if n < 4:                                    # sin vecindario no hay propuestas
        stop = STOP_COOLED
    while stop is None and T > Tmin:
        for _ in range(steps):
            stop = budget.check(evals)
            if stop:
                break
            i, j = random_valid_pair(n, rng)
            delta = two_opt_delta(D, current, i, j)
            evals += 1
            w_prop += 1
            if delta <= 0:
                take = True                      # mejora o empate: siempre
            else:
                proposed_worse += 1
                w_worse += 1
                take = rand() < exp(-delta / T)
                if take:
                    accepted_worse += 1
                    w_worse_acc += 1
            if take:
                two_opt_apply_inplace(current, i, j)
                cur_cost += delta
                accepted += 1
                if cur_cost < best_cost:
                    best_cost = cur_cost
                    best = list(current)         # copia: `current` seguira cambiando
                    trace.append((evals, best_cost, budget.elapsed()))
                    if history is not None:
                        history.append((list(best), best_cost, evals))
            if w_prop >= window:
                series.add(evals, T, cur_cost, (w_worse_acc / w_worse) if w_worse else None)
                w_prop = w_worse = w_worse_acc = 0
        if stop:
            break
        T *= alpha
    if stop is None:
        stop = STOP_COOLED
    if w_prop:                                   # ventana parcial final
        series.add(evals, T, cur_cost, (w_worse_acc / w_worse) if w_worse else None, force=True)

    final = tour_cost(D, best)
    if final != best_cost or cur_cost != tour_cost(D, current):
        raise RuntimeError("costo incremental distinto del costo completo")
    trace.append((evals, final, budget.elapsed()))
    extras = {
        "series_evals": series.x, "temperature": series.temperature,
        "current_cost": series.current_cost, "accept_rate_worse": series.accept_rate_worse,
        "accepted": accepted, "accepted_worse": accepted_worse,
        "proposed_worse": proposed_worse, "final_temperature": T,
        "final_current_route": list(current), "final_current_cost": cur_cost,
    }
    if history is not None:
        extras["route_history"] = history
    return RunResult(
        instance=inst.name, algorithm="SA",
        parameters={"T0": T0, "Tmin": Tmin, "alpha": alpha, "steps": steps,
                    "window": window, "initial_evals": initial_evals},
        tour=best, cost=final, gap_percent=gap_percent(final, inst.optimum),
        elapsed_seconds=budget.elapsed(), candidate_evaluations=evals,
        stop_reason=stop, optimality_status=OPT_NOT_PROVEN, trace=trace, extras=extras)
