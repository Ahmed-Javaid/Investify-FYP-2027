param(
    [string]$PythonExe = 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe',
    [switch]$PlanOnly
)

$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$probe = Join-Path $PSScriptRoot 'probe_market_reacquisition.py'
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$output = Join-Path $project ('evidence\market_reacquisition_20261012\normal_terminal_' + $stamp)

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw 'Python runtime not found. Pass -PythonExe with the path to an existing Python interpreter; this probe uses only the standard library.'
}
if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) { throw 'Market probe is missing from this project.' }
if (Test-Path -LiteralPath $output) { throw 'Preserve prior results. Run again to obtain a new output identity.' }

Write-Output 'Checks Yahoo, publisher FNSPID metadata and one Alpaca news response.'
Write-Output 'Reads the local code\.env pair; credential values are excluded from the report.'
Write-Output ('New result directory: ' + $output)
if ($PlanOnly) {
    Write-Output 'Plan only: no requests or files created.'
    return
}

& $PythonExe -B $probe --output $output
if ($LASTEXITCODE -ne 0) { throw 'Probe did not finish. Review the error above; existing receipts are preserved.' }
$report = Get-Content -LiteralPath (Join-Path $output 'probe.json') -Raw | ConvertFrom-Json
$report.results | Select-Object source,status,http_status,winerror | Format-Table -AutoSize

if (@($report.results | Where-Object { $_.status -eq 'connection_failed' }).Count -gt 0) {
    Write-Output 'Next step: run this check in your normal network-enabled PowerShell terminal. If it still fails there, check the expected proxy/VPN configuration and provider reachability.'
}
$alpaca = $report.results | Where-Object { $_.source -eq 'Alpaca/Benzinga' }
if ($alpaca.status -eq 'response_received') {
    Write-Output 'Alpaca returned a response. Connectivity and access to this bounded news request are verified; full historical coverage is a separate check.'
} elseif ($alpaca.status -eq 'http_error') {
    Write-Output ('Alpaca returned HTTP ' + $alpaca.http_status + '. Network access now reaches the provider.')
    if ($alpaca.http_status -in @(401, 403)) {
        Write-Output 'Next step for paper-account keys: run tools\check_alpaca_auth.ps1 in this terminal to compare paper-account and market-news access with the same pair.'
    } else {
        Write-Output 'Next step: check the provider status and response classification before retrying.'
    }
}
if (@($report.results | Where-Object { $_.source -eq 'Yahoo Finance' -and $_.http_status -eq 429 }).Count -gt 0) {
    Write-Output 'Yahoo throttled this request. Wait before retrying; use cached prices or a verified alternative provider as a separately identified new snapshot.'
}
if (-not $report.credentials.alpaca_pair_present) {
    Write-Output 'Next step: set both ALPACA_API_KEY and ALPACA_API_SECRET in the project code\.env, then rerun.'
}
