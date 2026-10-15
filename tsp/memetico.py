# -*- coding: utf-8 -*-
"""Algoritmo MEMETICO = GA + 2-opt sobre los descendientes (ampliacion de 12.1).

Se reporta APARTE del GA basico (algorithm "GA+2opt") porque la mejora que
produce la busqueda local no debe atribuirse al cruce (enunciado, 12.1).

Mismos operadores y mismas politicas que `tsp.ga` (se importan de alli), con
estas diferencias:

* Cada hijo NUEVO (cruzado o mutado) pasa por una busqueda local 2-opt de
  PRIMERA MEJORA: se recorren los pares validos de `tsp.vecindad` en orden
  aleatorio, se aplica cada movimiento con delta < 0 y se repite hasta no
  hallar mejora (optimo local) o hasta gastar `ls_max_evals` evaluaciones.
  Las copias exactas de un padre heredan su costo y no se vuelven a optimizar.
* Contabilidad (14.1): el costo completo del hijo cuenta 1 evaluacion y CADA
  delta 2-opt examinado cuenta 1 evaluacion mas, aunque se calcule en O(1).
  Todo el trabajo extra de la busqueda local esta, pues, dentro de
  `candidate_evaluations` y se desglosa en extras["ls_evals"] / ["child_evals"].
* Como la busqueda local no tiene costo conocido de antemano, NO se puede
  reservar una generacion completa: el presupuesto se consulta antes de cada
  evaluacion y, si se agota a mitad de generacion, esa generacion se descarta
  como poblacion (los hijos ya optimizados si cuentan para el mejor). Nunca se
  excede `max_evals`.
"""
import statistics

from tsp.ga import (_edge_diversity, _invert_segment, _ox, _tournament,
                    _unique_fraction)
from tsp.modelo import (OPT_NO_ROUTE, OPT_NOT_PROVEN, STOP_GENERATIONS, RunResult,
                        gap_percent, is_valid_tour, random_tour, tour_cost)
from tsp.vecindad import two_opt_apply_inplace, two_opt_delta, valid_pairs


def memetic_algorithm(inst, budget, rng, population_size=40, elite_count=2, pc=0.9,
                      pm=0.3, tournament_size=3, origin=0, ls_max_evals=None,
                      max_generations=None):
    """GA + 2-opt (algorithm "GA+2opt"). `ls_max_evals` limita las evaluaciones de
    delta por hijo (None = hasta el optimo local). Devuelve RunResult con extras
    como `genetic_algorithm` mas ls_evals, child_evals, ls_moves."""
    if population_size < 2 or not 0 <= elite_count < population_size:
        raise ValueError("poblacion >= 2 y 0 <= elite_count < population_size")
    if not 1 <= tournament_size <= population_size:
        raise ValueError("1 <= tournament_size <= population_size")
    if budget.max_evals is None and budget.max_seconds is None and max_generations is None:
        raise ValueError("sin limite de evals, segundos ni generaciones: no terminaria")

    D, n = inst.D, inst.n
    budget.start()
    parameters = dict(population_size=population_size, elite_count=elite_count, pc=pc,
                      pm=pm, tournament_size=tournament_size, origin=origin,
                      ls_max_evals=ls_max_evals, max_evals=budget.max_evals,
                      max_seconds=budget.max_seconds, max_generations=max_generations)
    length = n - 1
    genes_expected = set(range(n)) - {origin}
    pairs = list(valid_pairs(n)) if n >= 4 else []
    st = {"evals": 0, "child": 0, "ls": 0, "moves": 0, "reused": 0,
          "best_cost": None, "best_route": None}
    trace = []
    extras = {k: [] for k in ("gen_evals", "best", "median", "mean", "unique_fraction",
                              "edge_diversity", "best_so_far")}

    def note_best(route, cost):
        if st["best_cost"] is None or cost < st["best_cost"]:
            st["best_cost"], st["best_route"] = cost, list(route)
            trace.append((st["evals"], cost, budget.elapsed()))

    def improve(chromosome):
        """Evalua el hijo y le aplica 2-opt. Devuelve (cromosoma, costo, stop):
        stop != None si el presupuesto se agoto antes de poder evaluarlo (en ese
        caso cromosoma es None)."""
        if len(chromosome) != length or set(chromosome) != genes_expected:
            raise AssertionError("cromosoma que no es permutacion: {0}".format(chromosome))
        stop = budget.check(evals=st["evals"])
        if stop:
            return None, None, stop
        route = [origin] + chromosome
        cost = tour_cost(D, route)
        st["evals"] += 1
        st["child"] += 1
        note_best(route, cost)
        used, improved = 0, True
        while improved:
            improved = False
            rng.shuffle(pairs)
            for i, j in pairs:
                if ls_max_evals is not None and used >= ls_max_evals:
                    return route[1:], cost, None
                stop = budget.check(evals=st["evals"])
                if stop:
                    return route[1:], cost, stop     # hijo parcial pero valido
                delta = two_opt_delta(D, route, i, j)
                st["evals"] += 1
                st["ls"] += 1
                used += 1
                if delta < 0:
                    two_opt_apply_inplace(route, i, j)
                    cost += delta
                    st["moves"] += 1
                    improved = True
                    note_best(route, cost)
        return route[1:], cost, None

    def record(population, costs):
        routes = [[origin] + c for c in population]
        extras["gen_evals"].append(st["evals"])
        extras["best"].append(min(costs))
        extras["median"].append(statistics.median(costs))
        extras["mean"].append(statistics.fmean(costs))
        extras["unique_fraction"].append(_unique_fraction(routes, origin))
        extras["edge_diversity"].append(_edge_diversity(routes, n))
        extras["best_so_far"].append(st["best_cost"])

    def finish(stop_reason):
        if st["best_cost"] is not None and (not trace or trace[-1][0] != st["evals"]):
            trace.append((st["evals"], st["best_cost"], budget.elapsed()))
        extras["generations"] = max(0, len(extras["gen_evals"]) - 1)
        extras.update(ls_evals=st["ls"], child_evals=st["child"], ls_moves=st["moves"],
                      reused_costs=st["reused"])
        tour, cost = st["best_route"], st["best_cost"]
        if tour is not None:
            assert is_valid_tour(tour, n, origin) and cost == tour_cost(D, tour)
        return RunResult(
            instance=inst.name, algorithm="GA+2opt", parameters=parameters, tour=tour,
            cost=cost, gap_percent=gap_percent(cost, inst.optimum),
            elapsed_seconds=budget.elapsed(), candidate_evaluations=st["evals"],
            stop_reason=stop_reason,
            optimality_status=OPT_NOT_PROVEN if tour is not None else OPT_NO_ROUTE,
            trace=trace, extras=extras)

    # Poblacion inicial: aleatoria valida; tambien se optimiza (todo individuo del
    # memetico es un optimo local o un parcial por presupuesto).
    population, costs = [], []
    while len(population) < population_size:
        chrom, cost, stop = improve(random_tour(n, rng, origin)[1:])
        if chrom is not None:
            population.append(chrom)
            costs.append(cost)
        if stop:
            if population:
                record(population, costs)
            return finish(stop)
    record(population, costs)

    while True:
        if max_generations is not None and len(extras["gen_evals"]) - 1 >= max_generations:
            return finish(STOP_GENERATIONS)
        stop = budget.check(evals=st["evals"])
        if stop:
            return finish(stop)
        order = sorted(range(population_size), key=lambda k: (costs[k], k))
        next_pop = [list(population[k]) for k in order[:elite_count]]
        next_costs = [costs[k] for k in order[:elite_count]]
        stopped = None
        while len(next_pop) < population_size and stopped is None:
            a = _tournament(costs, rng, tournament_size)
            b = _tournament(costs, rng, tournament_size)
            p1, p2 = population[a], population[b]
            crossed = rng.random() < pc
            if crossed:
                left, right = sorted((rng.randrange(length), rng.randrange(length)))
                children = [_ox(p1, p2, left, right), _ox(p2, p1, left, right)]
            else:
                children = [list(p1), list(p2)]
            for slot, child in enumerate(children):
                if len(next_pop) >= population_size:
                    break
                mutated = length >= 2 and rng.random() < pm
                if mutated:
                    i, j = sorted(rng.sample(range(length), 2))
                    child = _invert_segment(child, i, j)
                if not crossed and not mutated:
                    next_pop.append(child)
                    next_costs.append(costs[a if slot == 0 else b])
                    st["reused"] += 1
                    continue
                chrom, cost, stopped = improve(child)
                if chrom is not None and stopped is None:
                    next_pop.append(chrom)
                    next_costs.append(cost)
                if stopped:
                    break
        if stopped:
            return finish(stopped)
        population, costs = next_pop, next_costs
        record(population, costs)
