param(
    [Parameter(Mandatory=$true)][ValidateSet('qwen25','qwen3')][string]$ModelKey,
    [Parameter(Mandatory=$true)][string]$Directory,
    [Parameter(Mandatory=$true)][string]$Receipt,
    [ValidateRange(1024,65535)][int]$Port = 1235
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$catalog = Get-Content -Encoding UTF8 -LiteralPath (Join-Path $projectRoot 'code/artifacts/mid_eval/official_model_catalog.json') -Raw | ConvertFrom-Json
$model = $catalog.models.$ModelKey
$receiptPath = [IO.Path]::GetFullPath($Receipt)
if (-not $receiptPath.StartsWith($projectRoot + '\evidence\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'New runtime receipt must remain under this working project evidence directory.'
}
& python -B (Join-Path $projectRoot 'code/scripts/verify_official_model.py') --model-key $ModelKey --directory $Directory --output $receiptPath
if ($LASTEXITCODE -ne 0) { throw 'Publisher identity verification failed. No model is launched.' }
$runtime = Get-Content -Encoding UTF8 -LiteralPath $receiptPath -Raw | ConvertFrom-Json
$backend = 'E:\AI-Tools\LMStudio\home\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.50.0\llama-server.exe'
$vendor = 'E:\AI-Tools\LMStudio\home\extensions\backends\vendor\win-llama-cuda12-vendor-v2'
if (-not (Test-Path -LiteralPath $backend) -or -not (Test-Path -LiteralPath $vendor)) { throw 'Declared installed backend or CUDA vendor directory is missing.' }
$log = Join-Path 'E:\AI-Tools\Temp' ('investify-official-' + $ModelKey + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$env:PATH = $vendor + ';' + $env:PATH
$launch = @('--model', $runtime.verified_files[0].path, '--host', '127.0.0.1', '--port', $Port,
            '--alias', $model.served_alias, '--ctx-size', '16384', '--parallel', '1',
            '--gpu-layers', '99', '--flash-attn', 'on', '--offline', '--log-file', $log)
if ($ModelKey -eq 'qwen3') { $launch += @('--jinja', '--reasoning', 'off', '--chat-template-kwargs', '{"enable_thinking":false}') }
$runtime | Add-Member -NotePropertyName backend_path -NotePropertyValue $backend
$runtime | Add-Member -NotePropertyName backend_sha256 -NotePropertyValue (Get-FileHash -Algorithm SHA256 -LiteralPath $backend).Hash.ToLowerInvariant()
$runtime | Add-Member -NotePropertyName launch_arguments -NotePropertyValue $launch
$runtime | Add-Member -NotePropertyName launch_identity_scope -NotePropertyValue 'Verified files supplied directly to task-owned loopback server. Subsequent endpoint aliases require launch mapping; aliases alone do not establish publisher identity.'
$runtime | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 -LiteralPath $receiptPath
Write-Output ('Starting verified publisher model on loopback port {0}; log {1}. Ctrl+C stops this task-owned server.' -f $Port, $log)
& $backend @launch
