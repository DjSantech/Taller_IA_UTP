# ===== Entorno de ejecución (sección A) =====
from IPython.display import Markdown, display

_info = environment_report()
display(Markdown("\n".join("- **{0}:** {1}".format(k, v) for k, v in _info.items())))
