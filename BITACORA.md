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

### D-03 · Entorno virtual fuera de la carpeta sincronizada

- **Decisión:** el entorno vive en `C:\Users\<usuario>\venvs\ia-taller1`, es decir **fuera** del proyecto, y
  `requirements.txt` fija las versiones exactas.
- **Alternativas:** `.venv` dentro del proyecto; instalar en el Python global.
- **Por qué:** dos razones distintas. (a) «Reproducible» incluye las versiones de
  las bibliotecas: SimpleAI y AIMA-Python son proyectos antiguos y su
  comportamiento cambia entre versiones, así que un entorno aislado y fijado
  evita que el cuaderno deje de ejecutarse. (b) El proyecto está dentro de
  OneDrive, y un entorno local son unos 3.000 archivos que OneDrive
  sincronizaría continuamente, con riesgo de corromperlo a mitad de una
  escritura.
- **Consecuencia:** hay que activar el entorno antes de abrir Jupyter, y el
  cuaderno debe usar el kernel `ia-taller1` registrado con `ipykernel`.

### D-04 · Los commits no llevan salidas de celda; la ejecución completa va al final

- **Decisión:** durante el desarrollo el cuaderno se versiona con las salidas
  limpias. El commit de entrega contiene una ejecución íntegra de arriba abajo.
- **Alternativas:** guardar las salidas en cada commit.
- **Por qué:** un `.ipynb` con salidas almacena las imágenes como base64 dentro
  del JSON, así que cada gráfica convierte el `diff` en miles de líneas
  ilegibles y el historial deja de servir como evidencia de proceso. Separar las
  dos cosas conserva lo que pide el enunciado —«todo el cuaderno debe ejecutarse
  desde el inicio en un entorno limpio»— y además un historial legible.
- **Consecuencia:** antes de entregar hay que hacer *Restart & Run All* y
  comprobar que no quede ninguna celda sin ejecutar ni fuera de orden.

### D-05 · AIMA-Python se vendoriza; SimpleAI se instala

- **Decisión:** SimpleAI entra por `pip`, porque está publicado en PyPI.
  AIMA-Python se copia al proyecto como `aima/search.py` y `aima/utils.py`, sin
  modificar una sola línea y con su procedencia citada.
- **Por qué:** AIMA-Python no se publica en PyPI, es un repositorio de
  referencia. Al 2026-09-21 sus módulos ya no están en la raíz del repositorio
  sino bajo `aima/`: la URL de la sección 14 del enunciado apunta a la ruta
  correcta, mientras que la ruta histórica devuelve 404. Vendorizar deja el
  cuaderno ejecutable sin depender de que el repositorio remoto no vuelva a
  reorganizarse.
- **Consecuencia:** el enunciado exige instrumentar «sin alterar permanentemente
  el repositorio», así que los contadores irán en subclases y envoltorios, nunca
  editando los archivos vendorizados. Tocarlos sería una falta.

### D-06 · Verificación temprana del riesgo de compatibilidad

- **Decisión:** antes de escribir cualquier algoritmo se comprobó que SimpleAI
  0.8.3 (publicado en 2021) importa y resuelve un `SearchProblem` mínimo de
  cuatro nodos bajo Python 3.13.7.
- **Por qué:** si la biblioteca no funcionara, la versión 2 del taller —12% de la
  nota— exigiría otra estrategia, y descubrirlo al final obligaría a rehacer
  trabajo. Comprobarlo ahora costó un minuto.
- **Resultado:** funciona. `breadth_first(..., graph_search=True)` devuelve el
  camino esperado como lista de pares `(acción, estado)`.

---
