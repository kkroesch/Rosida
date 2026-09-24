# In Repo-Wurzel ausführen: .\build\windows\build.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> 1. Standalone Python über uv bereitstellen..."
uv python install 3.12
uv venv .build-venv --python 3.12

Write-Host "==> 2. Minimale Abhängigkeiten installieren..."
& .build-venv\Scripts\uv.exe pip install `
    pyside6-essentials `
    polars `
    sympy `
    matplotlib `
    numpy `
    qtawesome `
    pyinstaller

Write-Host "==> 3. Windows Executable mit PyInstaller packen..."
& .build-venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --windowed `
    --name "Rosida" `
    --icon "logo.ico" `
    --add-data "src;src" `
    src/app.py

Write-Host "==> 4. Aufräumen..."
Remove-Item -Recurse -Force .build-venv

Write-Host "`nFertig! Die Anwendung liegt in: dist\Rosida\Rosida.exe"
