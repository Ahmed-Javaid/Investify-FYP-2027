param(
    [string]$PythonExe = 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe',
    [string]$SnapshotName = '',
    [switch]$Resume,
    [switch]$PlanOnly,
    [int]$MaximumPages = 1000
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw 'Pass -PythonExe with an existing interpreter.'
}
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
if (-not $SnapshotName) {
    if ($Resume) { throw 'Pass the existing snapshot name with -Resume.' }
    $SnapshotName = 'alpaca_nvda_' + $stamp
}
if ($SnapshotName -notmatch '^alpaca_nvda_[A-Za-z0-9_]+$') {
    throw 'SnapshotName must be an Alpaca snapshot basename.'
}
$output = Join-Path $project ('code\data\raw\snapshots\' + $SnapshotName)
$receipt = Join-Path $project ('evidence\market_reacquisition_20261012\news_acquisition_' + $stamp + '.json')
$arguments = @('-B', (Join-Path $PSScriptRoot 'acquire_alpaca_news.py'),
    '--output', $output, '--receipt', $receipt, '--maximum-pages', $MaximumPages)
if ($Resume) { $arguments += '--resume' }
if ($PlanOnly) { $arguments += '--plan-only' }
& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw 'Acquisition paused or failed. Review the receipt; retained pages can be resumed.' }
