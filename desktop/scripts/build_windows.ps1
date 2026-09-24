param(
    [string]$Python = 'python',
    [string]$Pnpm = 'pnpm'
)
$ErrorActionPreference = 'Stop'
$desktopRoot = Split-Path $PSScriptRoot -Parent
$projectRoot = Split-Path $desktopRoot -Parent
function Check-NativeExit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed with exit code $LASTEXITCODE. Read the build output; do not bypass Windows security restrictions." }
}
Push-Location $desktopRoot
try {
    if (!(Test-Path -LiteralPath "$desktopRoot/public/engine.glb")) {
        & $Python scripts/prepare_assets.py
        Check-NativeExit 'CAD asset preparation'
    }
    & $Pnpm install --frozen-lockfile
    Check-NativeExit 'Dependency installation'
    & $Python -m pytest tests -q
    Check-NativeExit 'Companion tests'
    & $Pnpm test
    Check-NativeExit 'IPC policy tests'
    & $Pnpm run build
    Check-NativeExit 'Frontend build'
    & $Python -m PyInstaller --noconfirm --onedir --console --name aerotrace-server `
        --distpath "$desktopRoot/backend-bundle" --workpath "$desktopRoot/backend-build" `
        --specpath "$desktopRoot/python" --paths "$projectRoot/backend" --collect-submodules uvicorn `
        --exclude-module matplotlib --exclude-module scipy --exclude-module pandas `
        --exclude-module IPython --exclude-module PIL `
        --add-data "$projectRoot/backend/artifacts/model.json;assets" `
        --add-data "$projectRoot/backend/config/cad_sensor_map.json;assets" `
        "$desktopRoot/python/desktop_server.py"
    Check-NativeExit 'Python bundle'
    & $Pnpm run package
    Check-NativeExit 'Windows installer packaging'
    Write-Host 'Packaging finished. Native launch, install/uninstall, offline and lifecycle checks are still required before release.'
} finally {
    Pop-Location
}
