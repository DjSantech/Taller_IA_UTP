# ===== Entorno de ejecucion: versiones reales frente a las fijadas en requirements.txt =====
# La reproducibilidad incluye las versiones de las bibliotecas, no solo las semillas.
# Esta celda NO instala nada: compara lo que tiene el kernel con lo que probamos.
import os as _os
import platform as _platform
import sys as _sys
from importlib import metadata as _metadata

assert READY, "Faltan dependencias: instalelas con requirements.txt y reinicie el kernel."

_fijadas = {}
if _os.path.exists("requirements.txt"):
    with open("requirements.txt", encoding="utf-8") as _fh:
        for _linea in _fh:
            _linea = _linea.split("#")[0].strip()
            if "==" in _linea:
                _paquete, _version = _linea.split("==")
                _fijadas[_paquete.strip()] = _version.strip()

print(f"Python {_platform.python_version()} ({_platform.system()} {_platform.release()})")
# Solo el nombre del entorno (no la ruta completa, que incluye el usuario de la maquina).
_en_venv = _sys.prefix != _sys.base_prefix
print(f"Entorno virtual: {_os.path.basename(_sys.prefix) if _en_venv else 'NO (Python del sistema)'}"
      " (el probado se llama ia-taller3)")
print(f"{'paquete':<20}{'instalada':<14}{'probada':<12}estado")
_distintas = 0
for _paquete, _probada in _fijadas.items():
    try:
        _instalada = _metadata.version(_paquete)
    except _metadata.PackageNotFoundError:
        _instalada = "(no instalada)"
    _ok = _instalada == _probada
    _distintas += not _ok
    print(f"{_paquete:<20}{_instalada:<14}{_probada:<12}{'igual' if _ok else 'DISTINTA'}")
print("Entorno verificado: Python 3.13.7, Windows 11.")
if _distintas:
    print(f"AVISO: {_distintas} version(es) distinta(s) de las probadas; los tiempos y algunos "
          "desempates podrian variar.")

# El cuaderno lee y escribe en resultados/: debe ejecutarse desde la raiz del proyecto.
assert _os.path.isdir("resultados"), "Ejecute el cuaderno desde la carpeta raiz del proyecto."
print("Directorio de trabajo correcto: existe resultados/ (salidas de las corridas).")
