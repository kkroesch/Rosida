# Standard: Lokale Ausführung
default: run

run:
    uv run --with pyside6 --with polars --with sympy --with matplotlib --with numpy --with qtawesome src/app.py

icons:
    # Create PNG and ICO icons for Linux and Windows
    magick logo.svg -define icon:auto-resize=256,48,32,16 logo.ico
    magick logo.svg logo.png

mod macos 'build/macos/Justfile'
mod linux 'build/linux/Justfile'
