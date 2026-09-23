SIGN_ID := "Developer ID Application: Karsten Kroesch (4G75EJQZ5G)"
APP     := "Rosida.app"
RES     := APP / "Contents/Resources"
PY_DIR  := RES / "python"

# Standard-Ziel: Lokaler Start
default: run

run:
    uv run --with pyside6 --with sympy --with matplotlib --with numpy app.py

# Icons aus SVG generieren
icons:
    #!/bin/bash
    set -eo pipefail
    mkdir -p rosida.iconset
    for size in 16 32 64 128 256 512 1024; do
        rsvg-convert -w $size -h $size logo.svg -o rosida.iconset/icon_${size}x${size}.png
    done
    mkdir -p "{{RES}}"
    iconutil -c icns rosida.iconset -o "{{RES}}/AppIcon.icns"
    rm -rf rosida.iconset

# Standalone-Python und Abhängigkeiten in das Bundle installieren
@python:
    #!/bin/bash
    set -eo pipefail
    if [ ! -d "{{PY_DIR}}" ]; then
        echo "Kopiere Standalone-Python in das Bundle..."
        PY_BIN=$(uv python find 3.12)
        PY_ROOT=$(dirname $(dirname "$PY_BIN"))
        mkdir -p "{{PY_DIR}}"
        cp -a "$PY_ROOT/"* "{{PY_DIR}}/"
        rm -f "{{PY_DIR}}"/lib/python3.*/EXTERNALLY-MANAGED
    fi

    echo "Installiere Abhängigkeiten..."
    uv pip install --break-system-packages --python "{{PY_DIR}}/bin/python3" \
        pyside6 sympy matplotlib numpy

    "{{PY_DIR}}/bin/python3" -c "import PySide6, sympy, matplotlib, numpy; print('OK: Alle Module geladen')"

# Nur Python-Skripte und UI-Assets in das Bundle kopieren
macapp:
    mkdir -p "{{RES}}"
    cp -a actions palettes *.py "{{RES}}/"

# 1. Schwere C-Extensions und Binaries signieren (NUR nötig nach 'just python')
sign-runtime:
    find Rosida.app/Contents/Resources/python -type f \( -name "*.o" -o -name "*.a" \) -delete
    find "{{PY_DIR}}" -type f \( -name "*.so" -o -name "*.dylib" \) -exec \
        codesign --force --timestamp --options runtime --entitlements entitlements.plist --sign "{{SIGN_ID}}" {} +
    find "{{PY_DIR}}/bin" -type f -perm +111 -exec \
        codesign --force --timestamp --options runtime --entitlements entitlements.plist --sign "{{SIGN_ID}}" {} +

# 2. Schneller Entwicklungs-Signier-Schritt: Aktualisiert Assets und versiegelt nur das Bundle
sign: macapp
    # Versiegelt das Bundle ohne --deep (vorhandene Signaturen im python/-Ordner bleiben unberührt)
    codesign --force --timestamp --options runtime --entitlements entitlements.plist --sign "{{SIGN_ID}}" "{{APP}}"
    # Verifikation prüft trotzdem deep & strict, ob alles stimmig ist
    codesign --verify --deep --strict --verbose=2 "{{APP}}"

# Alles komplett signieren (z. B. im CI-Workflow oder nach Neuinstallation)
sign-all: sign-runtime sign

# DMG erstellen und signieren
dmg: sign
    rm -f Rosida.dmg
    create-dmg \
        --volname "Rosida" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "{{APP}}" 160 190 \
        --hide-extension "{{APP}}" \
        --app-drop-link 440 190 \
        --no-internet-enable \
        Rosida.dmg \
        "{{APP}}"
    codesign --force --timestamp --sign "{{SIGN_ID}}" Rosida.dmg

# Notarisieren und Ticket stapeln
notarize: dmg
    xcrun notarytool submit Rosida.dmg --keychain-profile "rosida-profile" --wait
    xcrun stapler staple Rosida.dmg
    spctl --assess --type open --context context:primary-signature --verbose Rosida.dmg

# Aufräumen
clean:
    rm -f Rosida.dmg
