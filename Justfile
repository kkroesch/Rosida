# Standard: Lokale Ausführung
default: run

run:
    uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome src/app.py

mod macos 'build/macos/Justfile'
mod linux 'build/linux/Justfile'

