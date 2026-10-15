# -*- coding: utf-8 -*-
"""Algoritmo genetico para permutaciones (secciones 12 y 12.1 del taller).

Representacion: el CROMOSOMA contiene todas las ciudades menos el origen fijo
(n-1 genes). Decodificar = anteponer el origen; el ciclo se cierra de forma
implicita en `tour_cost`. Asi el origen nunca se mueve ni se duplica, y todo
operador que preserve la permutacion de los genes produce una ruta valida.

Operadores: seleccion por TORNEO (costo minimo), cruce OX, mutacion por
INVERSION de un segmento (probabilidad pm por INDIVIDUO) y ELITISMO explicito.

Politicas que el enunciado pide declarar
----------------------------------------
* Contabilidad (14.1): cada cromosoma cuyo costo se CALCULA cuenta 1 en
  `candidate_evaluations`, la poblacion inicial incluida. No se reevalua:
    - una elite (costo conservado);
    - una copia de un padre que no se cruzo ni se mutó (hereda su costo).
  No se usa ninguna otra cache.
* Presupuesto: nunca se supera `max_evals`. Antes de cada generacion se exige
  que quede presupuesto para el PEOR caso (pop - elite evaluaciones); si no
  alcanza, se para ANTES con STOP_EVALS (no se completa a medias). El tiempo se
  consulta antes de cada evaluacion; si vence a mitad de generacion, esa
  generacion se descarta como poblacion (los hijos ya evaluados si cuentan para
  el mejor, porque son rutas reales evaluadas).
* Poblacion inicial incompleta (presupuesto menor que la poblacion): se devuelve
  la mejor ruta de las evaluadas; si no se evaluo ninguna, tour=None
  (ausencia explicita de ruta, OPT_NO_ROUTE).
* Duplicados: se PERMITEN en la poblacion (no se filtran ni se penalizan);
  se miden con `unique_fraction`. Filtrarlos obligaria a gastar evaluaciones
  extra y escondería justo el fenomeno que se quiere observar.
* Desempates: en el torneo gana el primero de los muestreados (la muestra es
  aleatoria, asi que el desempate es uniforme); en la elite, a igual costo gana
  el individuo de menor indice (orden estable); el mejor global solo cambia con
  mejora ESTRICTA (el primero hallado se conserva).
"""
import statistics

from tsp.modelo import (OPT_NO_ROUTE, OPT_NOT_PROVEN, STOP_EVALS, STOP_GENERATIONS,
                        STOP_TIME, RunResult, gap_percent, is_valid_tour,
                        random_tour, tour_cost)


# ----------------------------------------------------------------------------
# Operadores (funciones puras sobre listas de genes; no conocen el costo)
# ----------------------------------------------------------------------------
def _ox(parent1, parent2, left, right):
    """Cruce de orden OX, tal cual el pseudocodigo de la seccion 12.1.

    1. child[left..right] = parent1[left..right]  (mismas posiciones).
    2. Las posiciones vacias se recorren circularmente desde right+1.
    3. Los genes de parent2 se leen circularmente desde right+1; cada gene que
       aun no esta en el hijo ocupa la siguiente posicion vacia.
    Funciona con cualquier tipo de gen (en las pruebas, letras)."""
    size = len(parent1)
    child = [None] * size
    segment = set(parent1[left:right + 1])
    child[left:right + 1] = parent1[left:right + 1]
    # Posiciones vacias en el orden de relleno (empiezan en right+1, circular).
    empty = [(right + 1 + k) % size for k in range(size)
             if child[(right + 1 + k) % size] is None]
    # Genes de parent2 que NO estan en el segmento, en el orden de lectura.
    # Como parent2 es permutacion, "aun no esta en child" == "no esta en segment".
    genes = [parent2[(right + 1 + k) % size] for k in range(size)
             if parent2[(right + 1 + k) % size] not in segment]
    for position, gene in zip(empty, genes):
        child[position] = gene
    return child


def _invert_segment(chromosome, i, j):
    """Copia de `chromosome` con el segmento [i..j] invertido (i <= j)."""
    child = list(chromosome)
    child[i:j + 1] = reversed(child[i:j + 1])
    return child


def _canonical(route, origin=0):
    """Forma canonica de un ciclo: rotado para empezar en `origin` y, entre la
    ruta y su inversa, la lexicograficamente menor.

    Por que NO altera la evaluacion: (1) rotar un ciclo no cambia sus aristas;
    (2) invertirlo cambia el sentido de cada arista, y como D es simetrica
    (la auditoria de datos lo verifica) d(a,b)=d(b,a); en ambos casos el
    conjunto de aristas y el costo son identicos. La forma canonica solo se usa
    para CONTAR individuos distintos; la poblacion y el costo no se tocan."""
    k = list(route).index(origin)
    rotated = list(route[k:]) + list(route[:k])
    reverse = [rotated[0]] + rotated[:0:-1]
    return tuple(min(rotated, reverse))


def _unique_fraction(routes, origin=0):
    """Proporcion de ciclos distintos (modulo rotacion e inversion) en la
    poblacion: 1/N si todos son el mismo ciclo, 1 si todos son diferentes."""
    return len({_canonical(r, origin) for r in routes}) / len(routes)


def _edge_diversity(routes, n):
    """Aristas NO dirigidas distintas presentes en la poblacion (incluido el
    cierre del ciclo) sobre las n(n-1)/2 posibles."""
    edges = set()
    for r in routes:
        for k in range(len(r)):
            a, b = r[k], r[(k + 1) % len(r)]
            edges.add((a, b) if a < b else (b, a))
    return len(edges) / (n * (n - 1) / 2)


def _tournament(costs, rng, size):
    """Indice del ganador de un torneo: `size` individuos distintos al azar, gana
    el de menor costo (a igual costo, el primero muestreado)."""
    contenders = rng.sample(range(len(costs)), size)
    winner = contenders[0]
    for idx in contenders[1:]:
        if costs[idx] < costs[winner]:
            winner = idx
    return winner


# ----------------------------------------------------------------------------
# Algoritmo
# ----------------------------------------------------------------------------
def genetic_algorithm(inst, budget, rng, population_size=80, elite_count=2, pc=0.9,
                      pm=0.3, tournament_size=3, origin=0, max_generations=None):
    """GA basico (algorithm "GA"). Devuelve RunResult.

    `max_generations` es un parametro EXTRA opcional (por defecto sin limite): sirve
    para pruebas y para no iterar sin fin si el presupuesto no tiene ni evals ni
    segundos. Con generaciones completas agotadas, stop_reason = GENERATIONS_DONE.

    extras (una entrada por generacion; el indice 0 es la poblacion inicial):
      gen_evals, best, median, mean, unique_fraction, edge_diversity,
      best_so_far, y los totales generations / reused_costs."""
    if not 2 <= population_size:
        raise ValueError("population_size >= 2")
    if not 0 <= elite_count < population_size:
        raise ValueError("0 <= elite_count < population_size")
    if not 1 <= tournament_size <= population_size:
        raise ValueError("1 <= tournament_size <= population_size")
    if budget.max_evals is None and budget.max_seconds is None and max_generations is None:
        raise ValueError("sin limite de evals, segundos ni generaciones: no terminaria")

    D, n = inst.D, inst.n
    budget.start()
    parameters = dict(population_size=population_size, elite_count=elite_count, pc=pc,
                      pm=pm, tournament_size=tournament_size, origin=origin,
                      max_evals=budget.max_evals, max_seconds=budget.max_seconds,
                      max_generations=max_generations)
    genes_expected = set(range(n)) - {origin}
    length = n - 1                        # genes por cromosoma

    state = {"evals": 0, "best_cost": None, "best_route": None, "reused": 0}
    trace = []
    extras = {k: [] for k in ("gen_evals", "best", "median", "mean", "unique_fraction",
                              "edge_diversity", "best_so_far")}

    def evaluate(chromosome):
        """Unico punto donde se calcula costo en el GA: cuenta 1 evaluacion,
        verifica la permutacion y actualiza el mejor (mejora estricta)."""
        if len(chromosome) != length or set(chromosome) != genes_expected:
            raise AssertionError("cromosoma que no es permutacion: {0}".format(chromosome))
        route = [origin] + chromosome
        cost = tour_cost(D, route)
        state["evals"] += 1
        if state["best_cost"] is None or cost < state["best_cost"]:
            state["best_cost"], state["best_route"] = cost, route
            trace.append((state["evals"], cost, budget.elapsed()))
        return cost

    def record(population, costs):
        routes = [[origin] + c for c in population]
        extras["gen_evals"].append(state["evals"])
        extras["best"].append(min(costs))
        extras["median"].append(statistics.median(costs))
        extras["mean"].append(statistics.fmean(costs))
        extras["unique_fraction"].append(_unique_fraction(routes, origin))
        extras["edge_diversity"].append(_edge_diversity(routes, n))
        extras["best_so_far"].append(state["best_cost"])

    def finish(stop_reason, population_costs=None):
        if not trace or trace[-1][0] != state["evals"]:
            if state["best_cost"] is not None:
                trace.append((state["evals"], state["best_cost"], budget.elapsed()))
        extras["generations"] = max(0, len(extras["gen_evals"]) - 1)
        extras["reused_costs"] = state["reused"]
        tour, cost = state["best_route"], state["best_cost"]
        if tour is not None:
            assert is_valid_tour(tour, n, origin)
        return RunResult(
            instance=inst.name, algorithm="GA", parameters=parameters, tour=tour,
            cost=cost, gap_percent=gap_percent(cost, inst.optimum),
            elapsed_seconds=budget.elapsed(), candidate_evaluations=state["evals"],
            stop_reason=stop_reason,
            optimality_status=OPT_NOT_PROVEN if tour is not None else OPT_NO_ROUTE,
            trace=trace, extras=extras)

    # --- poblacion inicial: permutaciones aleatorias validas ------------------
    population, costs = [], []
    for _ in range(population_size):
        stop = budget.check(evals=state["evals"])
        if stop:
            if population:
                record(population, costs)     # lo evaluado hasta ahora
            return finish(stop)
        chromosome = random_tour(n, rng, origin)[1:]
        population.append(chromosome)
        costs.append(evaluate(chromosome))
    record(population, costs)

    # --- generaciones ----------------------------------------------------------
    needed = population_size - elite_count       # evaluaciones en el peor caso
    while True:
        done = len(extras["gen_evals"]) - 1
        if max_generations is not None and done >= max_generations:
            return finish(STOP_GENERATIONS)
        stop = budget.check(evals=state["evals"])
        if stop:
            return finish(stop)
        if budget.max_evals is not None and state["evals"] + needed > budget.max_evals:
            return finish(STOP_EVALS)            # no cabe una generacion completa

        # Elitismo explicito: copias de los mejores, con su costo conservado.
        order = sorted(range(population_size), key=lambda i: (costs[i], i))
        next_pop = [list(population[i]) for i in order[:elite_count]]
        next_costs = [costs[i] for i in order[:elite_count]]

        stopped = None
        while len(next_pop) < population_size and stopped is None:
            p1_idx = _tournament(costs, rng, tournament_size)
            p2_idx = _tournament(costs, rng, tournament_size)
            p1, p2 = population[p1_idx], population[p2_idx]
            crossed = rng.random() < pc
            if crossed:
                # Mismos cortes para los dos hijos (OX(p1,p2) y OX(p2,p1)).
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
                    # Copia exacta de un padre: hereda su costo (no se calcula).
                    parent_idx = p1_idx if slot == 0 else p2_idx
                    next_pop.append(child)
                    next_costs.append(costs[parent_idx])
                    state["reused"] += 1
                    continue
                stop = budget.check(evals=state["evals"])
                if stop:
                    stopped = stop
                    break
                next_pop.append(child)
                next_costs.append(evaluate(child))
        if stopped:
            return finish(stopped)
        population, costs = next_pop, next_costs
        record(population, costs)
