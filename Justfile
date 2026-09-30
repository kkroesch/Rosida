# Standard: Lokale Ausführung
default: run

# Nutzt pyproject.toml + uv.lock (projektbasiert statt --with), damit lokaler Lauf und
# Plattform-Builds exakt dieselben, gepinnten Paketversionen verwenden.
run:
    uv run src/app.py

# uv.lock nach Änderungen an pyproject.toml neu berechnen
lock:
    uv lock

# Screenshots aller Komponenten (isoliert, offscreen) nach out/screenshots
# z.B. `just screenshots --lang en` oder `just screenshots docs/anderes.md --show`
screenshots *args:
    uv run scripts/screenshots.py {{args}}

# Übersicht der Architekturentscheidungen nach docs/adr/README.md
adr-report *args:
    uv run scripts/adr_report.py {{args}}

# Übersetzungen: neue/geänderte tr()-Texte in die .ts übernehmen und .qm bauen.
# Übersetzt wird in assets/i18n/rosida_de.ts (Texteditor oder `uv run pyside6-linguist`).
i18n:
    uv run pyside6-lupdate $(git ls-files 'src/*.py') -ts assets/i18n/rosida_de.ts -source-language en -target-language de -no-obsolete
    uv run pyside6-lrelease assets/i18n/rosida_de.ts -qm assets/i18n/rosida_de.qm

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
    uv run --with ipython ipython -i \
    -c "import numpy as np; \
        import matplotlib.pyplot as plt; \
        import polars as pl; \
        import sympy as sp"

import 'build/Justfile'

mod macos 'build/macos/Justfile'
mod linux 'build/linux/Justfile'
