# -*- coding: utf-8 -*-
"""Visualizaciones obligatorias (seccion 15.2) y animacion didactica.

Reglas de este modulo:
  * Todas las figuras salen de REGISTROS (RunResult o filas de CSV), nunca de
    numeros escritos a mano.
  * Nada se dibuja dentro de una region cronometrada: se llama despues de medir.
  * Cada funcion devuelve la figura y NO llama a plt.show(); en el cuaderno la
    figura se muestra sola al ser el valor de la celda (o con plt.show()).
  * No se fija el backend de matplotlib aqui: lo decide el entorno (en el cuaderno
    es el integrado; en las pruebas se configura Agg).
  * Colores de la paleta Okabe-Ito (distinguibles con daltonismo) y un color FIJO
    por algoritmo en todas las figuras.
"""
import math
import warnings

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from tsp.modelo import RunResult, tour_cost
from tsp.experimentos import ALGORITHMS, TABLE_LABELS, EXACT_ALGORITHMS, LIMIT_REASONS

COLORS = {"A*+MST": "#0072B2", "RBFS+MST": "#56B4E9", "HC": "#D55E00",
          "HC-restarts": "#E69F00", "SA": "#009E73", "GA": "#CC79A7"}
_NEGRO, _GRIS = "#222222", "#8a8a8a"


def _label(alg):
    return TABLE_LABELS.get(alg, alg)


def _get(r, name, default=None):
    """Lee un campo de un RunResult o de una fila (dict) de CSV."""
    if isinstance(r, dict):
        return r.get(name, default)
    return getattr(r, name, default)


# --- Disposicion de las ciudades ------------------------------------------------
def _layout(inst):
    """(coordenadas, es_geografico). Sin coordenadas: disposicion circular que es
    SOLO esquematica; se rotula siempre como tal."""
    if inst.coords is not None:
        return np.array(inst.coords, dtype=float), True
    ang = np.linspace(0, 2 * math.pi, inst.n, endpoint=False)
    return np.column_stack([np.cos(ang), np.sin(ang)]), False


def _draw_route(ax, inst, route, pts, geo, title, color):
    cerrada = list(route) + [route[0]]
    ax.plot(pts[cerrada, 0], pts[cerrada, 1], "-", color=color, lw=1.4, zorder=1)
    ax.scatter(pts[:, 0], pts[:, 1], s=16, color=_NEGRO, zorder=2)
    o = route[0]
    ax.scatter([pts[o, 0]], [pts[o, 1]], s=90, marker="*", color="#F0E442",
               edgecolor=_NEGRO, zorder=3, label="origen")
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal", adjustable="datalim")
    if geo:
        ax.set_xlabel("x (coordenadas de dibujo)")
        ax.set_ylabel("y (coordenadas de dibujo)")
    else:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("disposición circular esquemática, no geografía real")


# --- 1. Rutas inicial y final ----------------------------------------------------------
def plot_routes(inst, initial_route, final_route, algorithm=None):
    """Rutas inicial y final. Con coordenadas: dibujo geografico. Sin ellas:
    disposicion circular rotulada como esquematica + mapa de calor de la matriz."""
    pts, geo = _layout(inst)
    paneles = 2 if geo else 3
    fig, axes = plt.subplots(1, paneles, figsize=(5.2 * paneles, 4.8), squeeze=False)
    axes = axes[0]
    ci, cf = tour_cost(inst.D, initial_route), tour_cost(inst.D, final_route)
    _draw_route(axes[0], inst, initial_route, pts, geo, "Ruta inicial (costo {0})".format(ci), _GRIS)
    _draw_route(axes[1], inst, final_route, pts, geo,
                "Ruta final{0} (costo {1})".format(" de " + _label(algorithm) if algorithm else "", cf),
                COLORS.get(algorithm, "#0072B2"))
    if not geo:
        im = axes[2].imshow(np.array(inst.D, dtype=float), cmap="viridis")
        axes[2].set_title("Mapa de calor de la matriz de pesos", fontsize=10)
        axes[2].set_xlabel("posición de ciudad")
        axes[2].set_ylabel("posición de ciudad")
        fig.colorbar(im, ax=axes[2], fraction=0.046, label="peso d(i,j)")
    fig.suptitle(inst.name, fontsize=12)
    fig.tight_layout()
    return fig


# --- 2. Convergencia ------------------------------------------------------------------------
def step_curves(results, by="evaluations", grid=None, n_grid=300):
    """Interpola cada traza como FUNCION ESCALONADA en una rejilla comun.
    Devuelve (rejilla, matriz [corridas x rejilla] con NaN antes del primer punto,
    vector con el valor final de x de cada corrida). Una traza (x, mejor, t) vale
    `mejor` desde x hasta el siguiente punto: el mejor costo solo cambia en una
    mejora estricta, no se interpola linealmente."""
    idx = 0 if by == "evaluations" else 2
    trazas = [_get(r, "trace") for r in results if _get(r, "trace")]
    if not trazas:
        raise ValueError("No hay trazas para graficar.")
    fines = np.array([float(t[-1][idx]) for t in trazas])
    if grid is None:
        grid = np.linspace(0, float(fines.max()), n_grid)
    M = np.full((len(trazas), len(grid)), np.nan)
    for i, t in enumerate(trazas):
        xs = np.array([float(p[idx]) for p in t])
        ys = np.array([float(p[1]) for p in t])
        pos = np.searchsorted(xs, grid, side="right") - 1
        ok = pos >= 0
        M[i, ok] = ys[pos[ok]]
    return np.asarray(grid), M, fines


def plot_convergence(results, by="evaluations", instance=None, algorithms=("HC", "SA", "GA"),
                     reference=None, logx=False, ax=None):
    """Mejor costo acumulado vs evaluaciones (by='evaluations') o vs tiempo
    (by='time'): mediana entre semillas y banda intercuartilica (Q1-Q3).

    Trazo continuo: la mitad o mas de las semillas todavia estaba EJECUTANDO.
    Trazo discontinuo: tras la parada de la mayoria, el valor es CONSERVADO (el
    mejor ya hallado), no evaluaciones realizadas (seccion 11.1)."""
    grupos = {}
    for r in results:
        if instance is not None and _get(r, "instance") != instance:
            continue
        if _get(r, "algorithm") in algorithms:
            grupos.setdefault(_get(r, "algorithm"), []).append(r)
    if not grupos:
        raise ValueError("Sin resultados para esa instancia/algoritmos.")
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure
    xmax = max(max(float(p[0 if by == "evaluations" else 2]) for p in _get(r, "trace")[-1:])
               for rs in grupos.values() for r in rs if _get(r, "trace"))
    grid = np.linspace(0, xmax, 400)
    for alg in [a for a in ALGORITHMS if a in grupos]:
        g, M, fines = step_curves(grupos[alg], by, grid)
        n = len(fines)
        with warnings.catch_warnings():       # tramos aun sin dato: todo NaN, es esperado
            warnings.simplefilter("ignore", RuntimeWarning)
            q1, med, q3 = (np.nanpercentile(M, q, axis=0) for q in (25, 50, 75))
        activo = (fines[:, None] >= g[None, :]).sum(axis=0) * 2 >= n   # >= mitad ejecutando
        c = COLORS[alg]
        ax.fill_between(g, q1, q3, color=c, alpha=0.18, lw=0)
        corte = int(np.argmin(activo)) if not activo.all() else len(g)
        ax.plot(g[:corte], med[:corte], color=c, lw=2, label="{0} (n={1})".format(_label(alg), n))
        if corte < len(g):
            ax.plot(g[max(corte - 1, 0):], med[max(corte - 1, 0):], color=c, lw=2, ls="--")
    if reference is not None:
        ax.axhline(reference, color=_NEGRO, ls=":", lw=1.2, label="óptimo de referencia")
    ax.plot([], [], color=_GRIS, ls="--", label="valor conservado tras la parada")
    ax.set_xlabel("Evaluaciones de candidatos" if by == "evaluations" else "Tiempo (s)")
    ax.set_ylabel("Mejor costo acumulado")
    if logx:
        ax.set_xscale("symlog", linthresh=10)
    ax.set_title("Convergencia{0}: mediana y banda intercuartílica entre semillas".format(
        " en " + instance if instance else ""), fontsize=11)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    return fig


def plot_convergence_both(results, instance=None, algorithms=("HC", "SA", "GA"), reference=None):
    """Las dos vistas de la seccion 11.1 lado a lado: evaluaciones y tiempo."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    plot_convergence(results, "evaluations", instance, algorithms, reference, ax=axes[0])
    plot_convergence(results, "time", instance, algorithms, reference, ax=axes[1])
    fig.tight_layout()
    return fig


# --- 3. Gap por algoritmo e instancia --------------------------------------------------------
def plot_gap_boxes(results, instances=None, algorithms=("HC", "HC-restarts", "SA", "GA")):
    """Cajas con puntos individuales (todas las semillas) del gap % por instancia.
    Las ejecuciones sin gap (N/A) no se dibujan; se informa cuantas faltan."""
    filas = [r for r in results if _get(r, "gap_percent") is not None
             and _get(r, "variant", "main") != "origin"]
    insts = list(instances or sorted({_get(r, "instance") for r in filas}))
    algs = [a for a in ALGORITHMS if a in algorithms]
    if not insts or not algs:
        raise ValueError("No hay gaps para graficar.")
    fig, ax = plt.subplots(figsize=(max(7, 2.2 * len(insts)), 5))
    ancho = 0.8 / len(algs)
    rng = np.random.default_rng(0)            # solo el desplazamiento visual de los puntos
    for j, alg in enumerate(algs):
        datos, posiciones = [], []
        for i, ins in enumerate(insts):
            v = [float(_get(r, "gap_percent")) for r in filas
                 if _get(r, "instance") == ins and _get(r, "algorithm") == alg]
            pos = i + (j - (len(algs) - 1) / 2) * ancho
            if v:
                datos.append(v)
                posiciones.append(pos)
                ax.scatter(pos + rng.uniform(-ancho / 5, ancho / 5, len(v)), v, s=14,
                           color=COLORS[alg], edgecolor=_NEGRO, lw=0.3, zorder=3)
        if datos:
            bp = ax.boxplot(datos, positions=posiciones, widths=ancho * 0.8, showfliers=False,
                            patch_artist=True, manage_ticks=False)
            for caja in bp["boxes"]:
                caja.set(facecolor=COLORS[alg], alpha=0.35)
            for m in bp["medians"]:
                m.set(color=_NEGRO, lw=1.6)
        ax.scatter([], [], color=COLORS[alg], label=_label(alg))
    ax.set_xticks(range(len(insts)))
    ax.set_xticklabels(insts)
    ax.set_xlabel("Instancia")
    ax.set_ylabel("Gap respecto al óptimo de referencia (%)")
    ax.set_title("Gap por algoritmo e instancia (cada punto es una semilla)", fontsize=11)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


# --- 4. Tiempo y memoria de A*/RBFS vs k ------------------------------------------------------
_MARCAS = ["o", "s", "^", "D", "v", "P"]


def plot_exact_scaling(results, instance=None):
    """Tiempo y memoria vs tamano k de subinstancia para A* y RBFS. Las
    ejecuciones INTERRUMPIDAS por un limite se marcan con una X roja: su tiempo o
    memoria es una cota inferior de lo que habria costado terminar."""
    filas = [r for r in results if _get(r, "algorithm") in EXACT_ALGORITHMS
             and _get(r, "k") is not None and _get(r, "variant", "main") != "origin"
             and (_get(r, "repetition") or 1) == 1]
    bases = sorted({str(_get(r, "instance")).split("[")[0] for r in filas})
    if instance is not None:
        bases = [instance]
    if not bases:
        raise ValueError("No hay ejecuciones exactas con k.")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
    for ib, base in enumerate(bases):
        for alg in EXACT_ALGORITHMS:
            sel = sorted((r for r in filas if str(_get(r, "instance")).split("[")[0] == base
                          and _get(r, "algorithm") == alg), key=lambda r: _get(r, "k"))
            if not sel:
                continue
            ks = [_get(r, "k") for r in sel]
            kw = dict(color=COLORS[alg], marker=_MARCAS[ib % len(_MARCAS)], lw=1.5,
                      label="{0} · {1}".format(_label(alg), base))
            a1.plot(ks, [max(_get(r, "elapsed_seconds"), 1e-6) for r in sel], **kw)
            a2.plot(ks, [_get(r, "peak_memory") / 1024 ** 2 for r in sel], **kw)
            cen = [r for r in sel if _get(r, "stop_reason") in LIMIT_REASONS]
            for ax, f in ((a1, lambda r: max(_get(r, "elapsed_seconds"), 1e-6)),
                          (a2, lambda r: _get(r, "peak_memory") / 1024 ** 2)):
                ax.scatter([_get(r, "k") for r in cen], [f(r) for r in cen], marker="X", s=140,
                           color="#D00000", edgecolor=_NEGRO, zorder=5)
    a1.scatter([], [], marker="X", s=100, color="#D00000", label="interrumpida por límite")
    a1.set_yscale("log")
    a1.set_xlabel("Tamaño de la subinstancia k")
    a1.set_ylabel("Tiempo (s, escala log)")
    a1.set_title("Tiempo vs k", fontsize=11)
    a2.set_xlabel("Tamaño de la subinstancia k")
    a2.set_ylabel("Memoria incremental máxima (MiB, tracemalloc)")
    a2.set_title("Memoria vs k", fontsize=11)
    for ax in (a1, a2):
        ax.grid(alpha=0.3)
    a1.legend(fontsize=7)
    fig.tight_layout()
    return fig


# --- 5. SA -------------------------------------------------------------------------------------
def _xs(series, total):
    """Posicion x de cada registro de una serie, repartida uniformemente sobre
    `total` (las series tienen un registro por bloque de propuestas; si el
    solver guarda `series_evals`, se usa ese eje exacto)."""
    n = len(series)
    return np.arange(1, n + 1) * (total / n) if n else np.array([])


def plot_sa(result, window=None):
    """Temperatura, costo actual (y mejor) y tasa de aceptacion de empeoramientos
    de UNA corrida de SA. `window` (propuestas por ventana) se declara en el eje."""
    ex = _get(result, "extras") or {}
    need = ("temperature", "current_cost", "accept_rate_worse")
    faltan = [k for k in need if k not in ex]
    if faltan:
        raise ValueError("Faltan series de SA en extras: {0}".format(faltan))
    window = window or ex.get("window") or (_get(result, "parameters") or {}).get("window") or 500
    total = _get(result, "candidate_evaluations") or len(ex["current_cost"])
    exact = ex.get("series_evals")
    fig, axes = plt.subplots(3, 1, figsize=(9, 8.5), sharex=True)
    x_t = np.array(exact) if exact and len(exact) == len(ex["temperature"]) else _xs(ex["temperature"], total)
    x_c = np.array(exact) if exact and len(exact) == len(ex["current_cost"]) else _xs(ex["current_cost"], total)
    x_a = np.array(exact) if exact and len(exact) == len(ex["accept_rate_worse"]) else _xs(ex["accept_rate_worse"], total)
    c = COLORS["SA"]
    axes[0].plot(x_t, ex["temperature"], color=c, lw=1.6)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Temperatura T (log)")
    axes[1].plot(x_c, ex["current_cost"], color=c, lw=1, alpha=0.8, label="costo actual")
    tr = _get(result, "trace")
    if tr:
        xs = [p[0] for p in tr]
        axes[1].step(xs, [p[1] for p in tr], where="post", color=_NEGRO, lw=1.6,
                     label="mejor costo acumulado")
    axes[1].set_ylabel("Costo")
    axes[1].legend(fontsize=8)
    axes[2].plot(x_a, ex["accept_rate_worse"], color="#E69F00", lw=1.4)
    axes[2].set_ylim(-0.02, 1.02)
    axes[2].set_ylabel("Aceptación de empeoramientos\n(ventana de {0} propuestas)".format(window))
    axes[2].set_xlabel("Evaluaciones de candidatos (incluye la calibración de T0)" if exact
                       else "Propuestas evaluadas (eje repartido uniformemente sobre el registro)")
    for ax in axes:
        ax.grid(alpha=0.3)
    axes[0].set_title("Recocido simulado: enfriamiento, costo y aceptación (semilla {0})".format(
        _get(result, "seed")), fontsize=11)
    fig.tight_layout()
    return fig


# --- 6. GA -------------------------------------------------------------------------------------
def plot_ga(result):
    """Mejor costo y costo mediano de la poblacion, y diversidad, por generacion."""
    ex = _get(result, "extras") or {}
    faltan = [k for k in ("best", "median", "unique_fraction") if k not in ex]
    if faltan:
        raise ValueError("Faltan series de GA en extras: {0}".format(faltan))
    gens = np.arange(len(ex["best"]))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    a1.plot(gens, ex["best"], color=COLORS["GA"], lw=2, label="mejor de la población")
    a1.plot(gens, ex["median"], color=_NEGRO, lw=1.4, ls="--", label="mediana de la población")
    if "mean" in ex:
        a1.plot(gens, ex["mean"], color=_GRIS, lw=1, ls=":", label="media de la población")
    a1.set_ylabel("Costo de la ruta")
    a1.legend(fontsize=8)
    a1.set_title("Algoritmo genético: costos y diversidad por generación (semilla {0})".format(
        _get(result, "seed")), fontsize=11)
    a2.plot(gens, ex["unique_fraction"], color="#0072B2", lw=1.8, label="fracción de individuos únicos")
    if "edge_diversity" in ex:
        a2.plot(gens, ex["edge_diversity"], color="#D55E00", lw=1.6, label="diversidad de aristas")
    a2.set_ylim(-0.02, 1.02)
    a2.set_ylabel("Diversidad (0 a 1)")
    a2.set_xlabel("Generación")
    a2.legend(fontsize=8)
    for ax in (a1, a2):
        ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


# --- 7. Animacion -------------------------------------------------------------------------------
def _pick_frames(history, max_frames):
    """Submuestrea el historial conservando SIEMPRE el primer y el ultimo cuadro."""
    n = len(history)
    if n <= max_frames:
        return list(history)
    idx = sorted({int(round(i * (n - 1) / (max_frames - 1))) for i in range(max_frames)})
    return [history[i] for i in idx]


def animate_improvements(inst, route_history, algorithm, path_gif=None, max_frames=40,
                         duration_ms=250, dpi=80):
    """Cuadros de las mejoras de una ruta. `route_history` = [(ruta, costo,
    evaluaciones)]. Cada cuadro muestra algoritmo, costo y trabajo acumulado.
    Devuelve la lista de imagenes PIL (para incrustar en el cuaderno) y, si
    `path_gif` no es None, escribe un GIF con Pillow. Se renderiza con Agg sin
    pasar por pyplot: no abre ventanas ni altera el backend del cuaderno."""
    if not route_history:
        raise ValueError("route_history vacio: ejecute con keep_history=True.")
    from PIL import Image
    pts, geo = _layout(inst)
    marco = _pick_frames(route_history, max_frames)
    pad = 0.05 * (pts.max(axis=0) - pts.min(axis=0)).max()
    lo, hi = pts.min(axis=0) - pad, pts.max(axis=0) + pad
    primero = marco[0][1]
    imagenes = []
    for ruta, costo, evals in marco:
        fig = Figure(figsize=(5.6, 5.2), dpi=dpi)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        cerrada = list(ruta) + [ruta[0]]
        ax.plot(pts[cerrada, 0], pts[cerrada, 1], "-", color=COLORS.get(algorithm, "#0072B2"), lw=1.5)
        ax.scatter(pts[:, 0], pts[:, 1], s=14, color=_NEGRO, zorder=3)
        ax.scatter([pts[ruta[0], 0]], [pts[ruta[0], 1]], s=80, marker="*", color="#F0E442",
                   edgecolor=_NEGRO, zorder=4)
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([])
        ax.set_yticks([])
        if not geo:
            ax.set_xlabel("disposición circular esquemática, no geografía real", fontsize=8)
        ax.set_title("{0} · {1}\ncosto {2} (inicial {3}) · trabajo: {4} evaluaciones".format(
            inst.name, _label(algorithm), costo, primero, evals), fontsize=9)
        fig.tight_layout()
        fig.canvas.draw()
        imagenes.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB"))
    if path_gif:
        imagenes[0].save(path_gif, save_all=True, append_images=imagenes[1:],
                         duration=duration_ms, loop=0, optimize=False)
    return imagenes


def show_frames(images, cols=4, indices=None):
    """Secuencia de cuadros en una sola figura (alternativa si no hay animacion)."""
    sel = list(images) if indices is None else [images[i] for i in indices]
    filas = math.ceil(len(sel) / cols)
    fig, axes = plt.subplots(filas, cols, figsize=(3.6 * cols, 3.4 * filas), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, im in zip(axes.ravel(), sel):
        ax.imshow(im)
    fig.tight_layout()
    return fig
