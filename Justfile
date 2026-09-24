# Standard: Lokale Ausführung
default: run

run:
    uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy src/app.py

# Modul für macOS-Builds
mod macos 'build/macos/Justfile'
