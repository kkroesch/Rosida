# Standard: Lokale Ausführung
default: run

# Nutzt pyproject.toml + uv.lock (projektbasiert statt --with), damit lokaler Lauf und
# Plattform-Builds exakt dieselben, gepinnten Paketversionen verwenden.
run:
    uv run src/app.py

# uv.lock nach Änderungen an pyproject.toml neu berechnen
lock:
    uv lock

icons:
    # Create PNG and ICO icons for Linux and Windows
    magick logo.svg -define icon:auto-resize=256,48,32,16 logo.ico
    magick logo.svg logo.png


# Zeigt das exportierte QMD File an
preview file="docs/example.qmd":
    QUARTO_PYTHON=$HOME/.local/quarto-1.6.42/venv/bin/python \
        ~/.local/quarto-1.6.42/bin/quarto preview {{file}}

# Startet ein interaktives IPython Notebook zum Ausprobieren
notebook:
    uv run --with matplotlib --with numpy --with polars \
           --with sympy --with pyqt6 --with ipython \
           ipython -i \
           -c "import numpy as np; \
               import matplotlib.pyplot as plt; \
               import polars as pl; \
               import sympy as sp"

import 'build/Justfile'

mod macos 'build/macos/Justfile'
mod linux 'build/linux/Justfile'
