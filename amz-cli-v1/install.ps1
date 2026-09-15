$ErrorActionPreference = "Stop"
$BundleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$UvCommand = Get-Command uv -ErrorAction SilentlyContinue
if (-not $UvCommand) {
    $LocalUv = Join-Path $HOME ".local\bin\uv.exe"
    if (Test-Path $LocalUv) {
        $UvPath = $LocalUv
    }
    else {
        Write-Host "Installing uv..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        $UvPath = $LocalUv
    }
}
else {
    $UvPath = $UvCommand.Source
}

& $UvPath python install 3.12
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$PythonPath = (& $UvPath python find 3.12).Trim()
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $PythonPath (Join-Path $BundleDir "install.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$UserBin = Join-Path $HOME ".local\bin"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathParts = @($UserPath -split ";" | Where-Object { $_ })
if ($PathParts -notcontains $UserBin) {
    $NewPath = (($PathParts + $UserBin) -join ";")
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
}
$env:Path = "$UserBin;$env:Path"

& (Join-Path $UserBin "amz.cmd") version --json
Write-Host "amz is installed. Ask your Agent: 帮我配置 amz-cli"
Write-Host "New terminals will include it in PATH."
