$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 "$Root\install.py" @args
    exit $LASTEXITCODE
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python "$Root\install.py" @args
    exit $LASTEXITCODE
}
Write-Error "Python 3.11 or later is required."
exit 2
