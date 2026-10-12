param(
    [string]$PythonExe = 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe',
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw 'Pass -PythonExe with the path to an existing Python interpreter.'
}
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$output = Join-Path $project ('evidence\market_reacquisition_20261012\paper_auth_' + $stamp)
$arguments = @('-B', (Join-Path $PSScriptRoot 'check_alpaca_auth.py'), '--output', $output)
if ($PlanOnly) { $arguments += '--plan-only' }
& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw 'Authentication diagnostic did not finish. Review the message above.' }
