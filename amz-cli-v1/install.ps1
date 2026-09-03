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

$SdkWheels = @(Get-ChildItem (Join-Path $BundleDir "wheels\amz_cli_sdk-*.whl"))
if ($SdkWheels.Count -ne 1) {
    throw "Expected one amz-cli wheel in $BundleDir\wheels"
}

& $UvPath python install 3.12
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$PackageSpec = $SdkWheels[0].FullName + "[full]"
& $UvPath tool install --force --python 3.12 $PackageSpec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $UvPath tool update-shell | Out-Null

$UserBin = Join-Path $HOME ".local\bin"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathParts = @($UserPath -split ";" | Where-Object { $_ })
if ($PathParts -notcontains $UserBin) {
    $NewPath = (($PathParts + $UserBin) -join ";")
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
}
$env:Path = "$UserBin;$env:Path"

& (Join-Path $UserBin "amz.exe") version --json
Write-Host "amz is installed. Ask your Agent: 帮我配置 amz-cli"
Write-Host "New terminals will include it in PATH."
