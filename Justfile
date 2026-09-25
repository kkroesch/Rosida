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

mod macos 'build/macos/Justfile'
mod linux 'build/linux/Justfile'
