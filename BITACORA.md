# Bitácora de decisiones

Registro breve y fechado de las decisiones de diseño, los errores cometidos y su
corrección. El enunciado exige poder explicar en la defensa **una decisión que
produjo un error y cómo se corrigió**: esa evidencia se construye aquí, no al final.

Formato de cada entrada:

- **ID** — identificador estable para poder citarlo en el cuaderno.
- **Decisión** — qué se eligió.
- **Alternativas** — qué se descartó.
- **Por qué** — criterio que resolvió el empate.
- **Consecuencia** — qué habría que cambiar si la decisión fuera distinta.

---

## Etapa 0 — Estructura del repositorio (2026-09-21)

### D-01 · El entregable es la propia plantilla, no un cuaderno nuevo

- **Decisión:** completar el cuaderno recibido, conservando su numeración y sus
  secciones, en vez de escribir uno propio desde cero.
- **Alternativas:** cuaderno nuevo con estructura propia; código en módulos `.py`
  importados por un cuaderno delgado.
- **Por qué:** la sección 13 («Entrega») enumera las once partes esperadas en el
  orden de la plantilla, y penaliza «celdas fuera de orden» y «dependencias
  implícitas». Un cuaderno autocontenido es la lectura más literal y más segura
  de ese requisito.
- **Consecuencia:** el código vive en celdas, no en módulos; a cambio, hay que
  cuidar que cada celda dependa únicamente de celdas anteriores.

### D-02 · Primer commit con el enunciado intacto

- **Decisión:** el commit inicial contiene la plantilla tal como se recibió, sin
  una sola línea de solución.
- **Por qué:** hace verificable en el historial qué fue entregado por el docente
  y qué fue escrito por el estudiante. Sin ese punto de partida, el `diff` de
  autoría no existe.
- **Consecuencia:** ninguna; es gratis y solo se puede hacer una vez.

### D-03 · Entorno virtual local con versiones fijadas

- **Decisión:** `.venv` dentro del proyecto (ignorado por git) y `requirements.txt`
  con versiones exactas.
- **Alternativas:** instalar las dependencias en el Python global del sistema.
- **Por qué:** «reproducible» incluye las versiones de las bibliotecas. SimpleAI
  y AIMA-Python son proyectos antiguos y su comportamiento puede cambiar entre
  versiones; fijarlas evita que el cuaderno deje de ejecutarse.
- **Consecuencia:** hay que activar el entorno antes de abrir Jupyter.

---
