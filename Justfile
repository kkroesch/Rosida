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

# GUI-Tests (pytest-qt), headless via Qt's Offscreen-Plattform
test:
    QT_QPA_PLATFORM=offscreen uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome --with pytest --with pytest-qt \
        python -m pytest tests/ -v

# Wie `just test`, aber mit echten, sichtbaren Fenstern zum Zusehen (wie Playwrights headed-Modus)
# und einer kurzen Pause nach jeder simulierten Interaktion. Pausendauer per ROSIDA_TEST_SLOWMO (ms) einstellbar.
test-watch:
    ROSIDA_TEST_SLOWMO="{{env('ROSIDA_TEST_SLOWMO', '300')}}" uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome --with pytest --with pytest-qt \
        python -m pytest tests/ -v -s

# Code-Metriken (LOC, McCabe-Komplexität, Wartbarkeitsindex, Ruff, toter Code) -> metrics-report.md
metrics:
    uv run --with radon --with ruff --with vulture python scripts/metrics.py

mod macos 'build/macos/Justfile'
mod linux 'build/linux/Justfile'
