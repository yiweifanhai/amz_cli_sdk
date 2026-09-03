param(
    [switch]$Setup
)

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = if ($env:AMZ_CLI_HOME) { $env:AMZ_CLI_HOME } else { Join-Path $HOME ".local\share\amz-cli" }
$env:UV_CACHE_DIR = Join-Path $InstallRoot "uv-cache"
$env:UV_PYTHON_INSTALL_BIN = "0"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $InstallRoot "python"
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue

if ($UvCommand) {
    $UvPath = $UvCommand.Source
}
else {
    $LocalUv = Join-Path $HOME ".local\bin\uv.exe"
    if (-not (Test-Path $LocalUv)) {
        Write-Host "Installing uv..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    $UvPath = $LocalUv
}

& $UvPath python install 3.12
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$PythonPath = (& $UvPath python find 3.12).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonPath (Join-Path $RepoDir "manager.py") verify
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $PythonPath (Join-Path $RepoDir "manager.py") install --uv $UvPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "amz-cli is installed. Existing files under ~/.amz were not changed."
Write-Host "Restart the terminal if ~/.local/bin is not on PATH."

if ($Setup) {
    $PublicBin = if ($env:AMZ_CLI_BIN_DIR) { $env:AMZ_CLI_BIN_DIR } else { Join-Path $HOME ".local\bin" }
    $PreviousSkipUpdate = $env:AMZ_CLI_SKIP_UPDATE
    try {
        $env:AMZ_CLI_SKIP_UPDATE = "1"
        & (Join-Path $PublicBin "amz.cmd") setup --web
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        $env:AMZ_CLI_SKIP_UPDATE = $PreviousSkipUpdate
    }
}
