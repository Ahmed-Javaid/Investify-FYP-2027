param([Parameter(Mandatory=$true)][ValidateSet('Clone','Checks','Delivery')][string]$Stage)
$ErrorActionPreference='Stop'
$projectPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($projectPath -ne 'E:\Uni_Stuff\FYP\Investify') { throw 'Use the intended source workspace.' }
$checkout='E:\AI-Tools\Work\investify-ci-clone-20261013-run01'
if (-not $checkout.StartsWith('E:\AI-Tools\Work\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid clean checkout path.' }
$env:TEMP='E:\AI-Tools\Temp'
$env:TMP='E:\AI-Tools\Temp'
$env:PYTHONDONTWRITEBYTECODE='1'
$pythonPath='E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe'
if ($Stage -eq 'Clone') {
    if (Test-Path -LiteralPath $checkout) { throw 'Preserve previous clean checkouts.' }
    git -c core.autocrlf=false clone --no-local $projectPath $checkout
    if ($LASTEXITCODE -ne 0) { throw 'Clean clone failed.' }
    exit
}
if (-not (Test-Path -LiteralPath (Join-Path $checkout '.git'))) { throw 'Create the clean checkout first.' }
Push-Location -LiteralPath $checkout
try {
    if ($Stage -eq 'Checks') {
        & $pythonPath -B tools/restore_ci_checkout.py
        if ($LASTEXITCODE -ne 0) { throw 'Reviewed byte restoration failed.' }
        git config core.autocrlf true
        Push-Location -LiteralPath code
        try {
            & $pythonPath -B scripts/run_mid1_ci.py --job evidence --output artifacts/ci_evidence/evidence
            if ($LASTEXITCODE -ne 0) { throw 'Clean-checkout portable job failed.' }
            & $pythonPath -B scripts/run_mid1_ci.py --job streamlit-ui --output artifacts/ci_evidence/streamlit-ui --ruff-executable E:/AI-Tools/Work/investify-quality-tools/bin/ruff.exe
            if ($LASTEXITCODE -ne 0) { throw 'Clean-checkout UI job failed.' }
        } finally { Pop-Location }
        & $pythonPath -B -m unittest discover -s code/tests -p test_delivery_pipeline.py -v
        if ($LASTEXITCODE -ne 0) { throw 'Delivery admission guards failed.' }
    } else {
        & $pythonPath -B tools/run_mid1_delivery.py --ci-root code/artifacts/ci_evidence --output code/artifacts/ci_evidence/delivery
        if ($LASTEXITCODE -ne 0) { throw 'Clean-checkout artifact delivery failed.' }
    }
} finally { Pop-Location }
