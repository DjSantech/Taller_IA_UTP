# ===== Validación antes de las instancias completas (sección 13) =====
from IPython.display import Markdown, display

VALIDACION = run_validation_suite(INSTANCES)
display(Markdown(format_validation(VALIDACION)))
fallidas = [f for f in VALIDACION if not f[2]]
assert not fallidas, "Hay comprobaciones fallidas: {0}".format([f[:2] for f in fallidas])
print("✔ {0} de {0} comprobaciones de la tabla 13 pasan.".format(len(VALIDACION)))
