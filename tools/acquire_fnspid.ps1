param(
    [string]$PythonExe = 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe',
    [switch]$Full,
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw 'Pass -PythonExe with an existing Python interpreter; this acquisition uses only the standard library.'
}
$arguments = @('-B', (Join-Path $PSScriptRoot 'acquire_fnspid.py'))
if ($Full) { $arguments += '--full' }
if ($PlanOnly) { $arguments += '--plan-only' }
if ($Full) {
    Write-Output 'Full mode: 23.2 GB publisher transfer to E:\AI-Tools\Cache, SHA256 verification, then AAPL/NVDA/TSLA extraction into a new project raw-data snapshot.'
} else {
    Write-Output 'Sample mode: at most 1 MiB of actual FNSPID CSV; no Alpaca keys, package install or full-corpus transfer.'
}
& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw 'FNSPID acquisition is incomplete; consult the printed receipt and retained partial bytes.' }
