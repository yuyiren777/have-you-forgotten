param(
    [switch]$SkipAppBuild
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$IconSource = Join-Path $ProjectRoot 'resources\app-icon.png'
$IconTarget = Join-Path $ProjectRoot 'resources\app.ico'
$InstallerScript = Join-Path $ProjectRoot 'installer\AI-Memo.iss'
$ReleaseDir = Join-Path $ProjectRoot 'release'
$InstallerExe = Join-Path $ReleaseDir 'AI-Memo-Installer.exe'
$ReleaseZip = Join-Path $ReleaseDir 'AI-Memo-Installer.zip'
$BuildPython = Join-Path $ProjectRoot '.build-venv\Scripts\python.exe'
if (-not (Test-Path $BuildPython)) {
    $BuildPython = 'py'
}
$PythonBase = & $BuildPython -c "import sys; print(sys.base_prefix)"
$RuntimeBin = Join-Path $PythonBase 'Library\bin'
$RequiredRuntimeLibraries = @(
    'libssl-3-x64.dll', 'libcrypto-3-x64.dll', 'libexpat.dll', 'libbz2.dll', 'sqlite3.dll', 'ffi.dll',
    'vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll',
    'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
    'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll',
    'zlib.dll', 'zlib-ng2.dll'
)
$RuntimeBinaries = @()
foreach ($Library in $RequiredRuntimeLibraries) {
    $LibraryPath = Join-Path $RuntimeBin $Library
    if (Test-Path $LibraryPath) {
        $RuntimeBinaries += @('--add-binary', "$LibraryPath;.")
    }
}

if (-not (Test-Path $IconSource)) {
    throw "Missing app icon. Save the supplied icon as: $IconSource"
}

Push-Location $ProjectRoot
try {
    & $BuildPython installer\make_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon conversion failed.' }

    if (-not $SkipAppBuild) {
        # pyexpat depends on the Python distribution's libexpat.dll. Other tools
        # such as Graphviz can place an incompatible DLL with the same name on PATH.
        $OriginalPath = $env:PATH
        try {
            $env:PATH = "$RuntimeBin;$OriginalPath"
            & $BuildPython -m PyInstaller --noconfirm --clean --windowed --onedir --name AI-Memo --icon resources\app.ico --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 --collect-data tzdata --add-data "gui/styles.qss;gui" --add-data "gui/dark_styles.qss;gui" @RuntimeBinaries main.py
            if ($LASTEXITCODE -ne 0) { throw 'Application packaging failed.' }
        }
        finally {
            $env:PATH = $OriginalPath
        }

        $PythonExpat = Join-Path $RuntimeBin 'libexpat.dll'
        $BundledExpat = Join-Path $ProjectRoot 'dist\AI-Memo\_internal\libexpat.dll'
        if (-not (Test-Path $PythonExpat)) {
            throw "Python runtime library is missing: $PythonExpat"
        }
        Copy-Item -LiteralPath $PythonExpat -Destination $BundledExpat -Force
        if ((Get-FileHash $PythonExpat).Hash -ne (Get-FileHash $BundledExpat).Hash) {
            throw 'Bundled libexpat.dll does not match the Python runtime.'
        }
    }

    $IsccPath = (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source
    if (-not $IsccPath) {
        $IsccCandidates = @(
            'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
            (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
        )
        $IsccPath = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not (Test-Path $IsccPath)) {
        throw 'Inno Setup 6 is required. Install it with: winget install JRSoftware.InnoSetup'
    }

    & $IsccPath $InstallerScript
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }

    # Inno Setup may keep the output handle briefly after ISCC exits.
    Start-Sleep -Seconds 2
    if (Test-Path $ReleaseZip) { Remove-Item -LiteralPath $ReleaseZip -Force }
    Compress-Archive -LiteralPath $InstallerExe -DestinationPath $ReleaseZip -CompressionLevel Optimal -ErrorAction Stop
    Write-Host "Release package created: $ReleaseZip"
}
finally {
    Pop-Location
}
