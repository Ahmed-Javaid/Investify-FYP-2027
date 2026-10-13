param(
    [string]$PythonExe = 'E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe',
    [ValidateRange(1024,65535)][int]$Port = 8507
)
$ErrorActionPreference = 'Stop'
$projectPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$codePath = Join-Path $projectPath 'code'
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'Viewer Python is unavailable. Supply -PythonExe for a prepared compatible environment.' }
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw "Port $Port is already used. Choose another port or stop only your own existing demo." }
$env:TEMP='E:\AI-Tools\Temp'
$env:TMP='E:\AI-Tools\Temp'
$env:MPLCONFIGDIR='E:\AI-Tools\Cache\matplotlib'
$env:NUMBA_CACHE_DIR='E:\AI-Tools\Cache\numba'
$env:PYTHONDONTWRITEBYTECODE='1'
& $PythonExe -B -c "import streamlit; from packaging.version import Version; assert Version(streamlit.__version__) >= Version('1.63.0'), 'Guided navigation requires Streamlit 1.63 or later'"
if ($LASTEXITCODE -ne 0) { throw 'The viewer dependency check failed.' }
Write-Output "Guided demo: http://127.0.0.1:$Port ; stop with Ctrl+C."
Push-Location -LiteralPath $codePath
try {
    & $PythonExe -B -m streamlit run app/streamlit_app.py --server.address=127.0.0.1 --server.port=$Port --theme.base=light --server.headless=true --browser.gatherUsageStats=false
} finally {
    Pop-Location
}
