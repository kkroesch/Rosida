run:
    uv run --with pyside6 --with sympy --with matplotlib --with numpy app.py

icons:
    #!/bin/bash
    set -eo
    mkdir rosida.iconset
    for size in 16 32 64 128 256 512 1024; do
        rsvg-convert -w $size -h $size logo.svg -o rosida.iconset/icon_${size}x${size}.png
    done
    iconutil -c icns rosida.iconset -o Rosida.app/Contents/Resources/AppIcon.icns
    rm rosida.iconset


@bundle:
    uv venv Rosida.app/Contents/Resources/venv --python 3.12 --seed
    uv pip install --python Rosida.app/Contents/Resources/venv/bin/python \
        pyside6 sympy matplotlib numpy

copy:
    cp app.py document.py Rosida.app/Contents/Resources/
