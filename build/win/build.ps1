# In Repo-Wurzel ausführen: .\build\win\build.ps1
# Ergebnis: dist\Rosida\Rosida.exe und dist\Rosida-<version>-windows-x64.zip
$ErrorActionPreference = "Stop"

# Native Programme setzen keinen PowerShell-Fehler, deshalb Exit-Code prüfen
# (einfache Funktion mit $args, damit "--flag" unverändert durchgereicht wird)
function Invoke-Checked {
    $Exe, $Rest = $args
    & $Exe @Rest
    if ($LASTEXITCODE -ne 0) { throw "$Exe fehlgeschlagen (Exit-Code $LASTEXITCODE)" }
}

$Version = (Select-String -Path pyproject.toml -Pattern '^version = "(.*)"').Matches[0].Groups[1].Value
Write-Host "==> Rosida $Version"

Write-Host "==> 1. Standalone Python über uv bereitstellen..."
Invoke-Checked uv python install 3.12
Invoke-Checked uv venv .build-venv --python 3.12
$Python = ".build-venv\Scripts\python.exe"

Write-Host "==> 2. Gepinnte Abhängigkeiten aus uv.lock installieren..."
Invoke-Checked uv export --frozen --no-hashes --no-emit-project --group win-build -o requirements.lock.txt
Invoke-Checked uv pip install --python $Python -r requirements.lock.txt
Remove-Item requirements.lock.txt

Write-Host "==> 3. Windows Executable mit PyInstaller packen..."
# markdown lädt seine Erweiterungen (extra, codehilite, ...) per Name nach,
# ziamath/ziafont/latex2mathml bringen Schriften und Symboltabellen als Daten mit.
Invoke-Checked .build-venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --windowed `
    --name "Rosida" `
    --icon "logo.ico" `
    --add-data "src;src" `
    --add-data "assets/fonts;assets/fonts" `
    --add-data "assets/i18n;assets/i18n" `
    --add-data "docs/quickstart*.md;docs" `
    --add-data "logo.svg;." `
    --collect-submodules markdown `
    --collect-data ziamath `
    --collect-data ziafont `
    --collect-data latex2mathml `
    src/app.py

Write-Host "==> 4. ZIP-Archiv erstellen..."
$Zip = "dist\Rosida-$Version-windows-x64.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path dist\Rosida -DestinationPath $Zip

Write-Host "==> 5. Aufräumen..."
Remove-Item -Recurse -Force .build-venv

Write-Host "`nFertig! Die Anwendung liegt in: dist\Rosida\Rosida.exe"
Write-Host "Archiv: $Zip"
