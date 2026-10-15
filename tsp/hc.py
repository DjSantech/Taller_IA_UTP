# -*- coding: utf-8 -*-
"""Hill Climbing (descenso de costo) sobre la vecindad 2-opt (seccion 10).

Tres usos:
  * `hill_climbing(..., strategy="best")`   variante principal: recorre TODO el
    vecindario y aplica la MEJOR mejora estricta (delta < 0).
  * `hill_climbing(..., strategy="first")`  primera mejora: aplica la primera
    que encuentra (solo para comparar en subinstancias; no mezclar resultados).
  * `hill_climbing_restarts(...)`           reinicios aleatorios con UN presupuesto
    global compartido; conserva la mejor ruta global.

Contabilidad de trabajo: cada delta evaluado cuenta como UNA evaluacion en
`candidate_evaluations`; se consulta el presupuesto ANTES de evaluar, asi que
nunca se excede `max_evals` ni en una unidad. El costo de la ruta inicial (una
suma O(n)) NO se cuenta como evaluacion de candidato; es igual para HC y SA y
queda documentado para la comparacion controlada de la seccion 11.1.

Parada: LOCAL_OPTIMUM solo si se examino TODO el vecindario sin hallar mejora
estricta. Si el presupuesto interrumpe, se devuelve la ruta actual (valida) con
el motivo del Budget y sin afirmar optimo local. Ningun resultado de HC es
OPTIMO GLOBAL, por eso optimality_status es siempre NOT_PROVEN.
"""
from tsp.modelo import (STOP_LOCAL_OPT, OPT_NOT_PROVEN, RunResult, gap_percent,
                        random_tour, tour_cost)
from tsp.vecindad import two_opt_apply_inplace, two_opt_delta, valid_pairs


def _climb(D, route, cost, budget, evals, strategy, on_improve):
    """Un ascenso completo desde `route` (se modifica EN SITIO).

    Devuelve (cost, evals, stop) con stop = LOCAL_OPTIMUM o el motivo del
    Budget. `on_improve(route, cost, evals)` se llama tras cada movimiento
    aplicado. El costo se lleva incrementalmente (cost += delta); quien llama
    lo valida contra `tour_cost` al final."""
    n = len(route)
    while True:
        best_delta = 0
        best_move = None
        for i, j in valid_pairs(n):
            stop = budget.check(evals)
            if stop:
                return cost, evals, stop
            delta = two_opt_delta(D, route, i, j)
            evals += 1
            if delta < best_delta:
                best_delta = delta
                best_move = (i, j)
                if strategy == "first":
                    break                      # primera mejora: no seguir explorando
        if best_move is None:
            # Se evaluaron todos los pares sin delta < 0: optimo local verificado.
            return cost, evals, STOP_LOCAL_OPT
        two_opt_apply_inplace(route, best_move[0], best_move[1])
        cost += best_delta
        on_improve(route, cost, evals)


def _check_strategy(strategy):
    if strategy not in ("best", "first"):
        raise ValueError("strategy debe ser 'best' o 'first'")


def hill_climbing(inst, initial_route, budget, strategy="best", keep_history=False):
    """Hill Climbing desde `initial_route` (no se modifica). Ver el modulo.

    extras: "improvements" (movimientos aplicados) y, con keep_history=True,
    "route_history" = [(ruta, costo, evals), ...]: la ruta inicial (evals=0) y
    luego cada mejora aplicada, para una animacion posterior."""
    _check_strategy(strategy)
    D = inst.D
    budget.start()
    route = list(initial_route)
    cost = tour_cost(D, route)
    trace = [(0, cost, budget.elapsed())]
    history = [(list(route), cost, 0)] if keep_history else None
    count = [0]

    def on_improve(r, c, evals):
        count[0] += 1
        trace.append((evals, c, budget.elapsed()))
        if history is not None:
            history.append((list(r), c, evals))

    inc_cost, evals, stop = _climb(D, route, cost, budget, 0, strategy, on_improve)
    final = tour_cost(D, route)
    if final != inc_cost:                       # el delta debe coincidir SIEMPRE
        raise RuntimeError("costo incremental {0} != costo completo {1}".format(inc_cost, final))
    trace.append((evals, final, budget.elapsed()))
    extras = {"improvements": count[0]}
    if history is not None:
        extras["route_history"] = history
    return RunResult(
        instance=inst.name, algorithm="HC" if strategy == "best" else "HC-first",
        parameters={"strategy": strategy}, tour=route, cost=final,
        gap_percent=gap_percent(final, inst.optimum),
        elapsed_seconds=budget.elapsed(), candidate_evaluations=evals,
        stop_reason=stop, optimality_status=OPT_NOT_PROVEN, trace=trace, extras=extras)


def hill_climbing_restarts(inst, rng_init, budget, strategy="best"):
    """HC con reinicios aleatorios y UN presupuesto global compartido.

    Cada reinicio parte de `random_tour(n, rng_init, 0)`; el PRIMERO coincide con
    la ruta inicial que usarian HC de una ruta y SA si se siembran igual
    (comparacion controlada 11.1). Se conserva la mejor ruta global. Si el
    presupuesto interrumpe un ascenso, su ruta parcial (valida) tambien compite
    por ser la mejor, pero no se anota como optimo local.

    stop_reason es el motivo del Budget (EVAL_LIMIT, TIME_LIMIT...). Si el
    presupuesto es ilimitado el bucle no terminaria: se exige un limite.
    extras: "restarts" (ascensos iniciados), "local_optima_costs" (costo de cada
    optimo local terminado) e "interrupted_last" (el ultimo ascenso quedo cortado)."""
    _check_strategy(strategy)
    if budget.max_evals is None and budget.max_seconds is None:
        raise ValueError("los reinicios necesitan max_evals o max_seconds")
    D, n = inst.D, inst.n
    budget.start()
    best_route, best_cost = None, None
    trace = []
    evals = 0
    local_costs = []
    restarts = 0
    interrupted = False
    stop = None

    while True:
        # El primer ascenso siempre arranca (hace falta UNA ruta que devolver, y
        # un presupuesto agotado lo corta en su primera evaluacion).
        stop = budget.check(evals) if restarts > 0 else None
        if stop:
            break
        route = random_tour(n, rng_init, 0)
        cost = tour_cost(D, route)
        restarts += 1
        if best_cost is None or cost < best_cost:
            best_route, best_cost = list(route), cost
            trace.append((evals, best_cost, budget.elapsed()))

        def on_improve(r, c, ev):
            nonlocal best_route, best_cost
            if c < best_cost:
                best_route, best_cost = list(r), c
                trace.append((ev, c, budget.elapsed()))

        inc_cost, evals, why = _climb(D, route, cost, budget, evals, strategy, on_improve)
        if inc_cost != tour_cost(D, route):
            raise RuntimeError("costo incremental distinto del completo")
        if why == STOP_LOCAL_OPT:
            local_costs.append(inc_cost)
            if n < 4:                            # sin vecindario: reiniciar no aporta
                stop = why
                break
        else:
            interrupted = True
            stop = why
            break

    final = tour_cost(D, best_route)
    if final != best_cost:
        raise RuntimeError("mejor costo incremental distinto del completo")
    trace.append((evals, final, budget.elapsed()))
    return RunResult(
        instance=inst.name, algorithm="HC-restarts", parameters={"strategy": strategy},
        tour=best_route, cost=final, gap_percent=gap_percent(final, inst.optimum),
        elapsed_seconds=budget.elapsed(), candidate_evaluations=evals,
        stop_reason=stop, optimality_status=OPT_NOT_PROVEN, trace=trace,
        extras={"restarts": restarts, "local_optima_costs": local_costs,
                "interrupted_last": interrupted})
