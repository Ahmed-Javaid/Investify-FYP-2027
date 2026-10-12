param(
    [Parameter(Mandatory=$true)][string]$PdfPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [int]$Width = 1400,
    [int]$MaxPages = 0
)
$ErrorActionPreference = 'Stop'
$sourcePath = [IO.Path]::GetFullPath($PdfPath)
$outputPath = [IO.Path]::GetFullPath($OutputDirectory)
$projectPrefix = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')) + [IO.Path]::DirectorySeparatorChar
if (-not ($sourcePath.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase) -or $sourcePath.StartsWith('E:\AI-Tools\Temp\investify-report-build-', [StringComparison]::OrdinalIgnoreCase))) {
    throw 'Render only this project''s reference or deliverable PDFs.'
}
if (-not $outputPath.StartsWith('E:\AI-Tools\Temp\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'PDF render scratch must remain under E:\AI-Tools\Temp.'
}
if ($Width -lt 400 -or $Width -gt 2400 -or $MaxPages -lt 0) { throw 'Invalid render limits.' }
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null

function Wait-Operation($Operation, [Type]$ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetGenericArguments().Count -eq 1 -and
        $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -like 'IAsyncOperation*'
    } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait(20000)) { throw 'Windows PDF operation exceeded twenty seconds.' }
    return $task.Result
}

function Wait-Action($Operation) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and -not $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
    } | Select-Object -First 1
    $task = $method.Invoke($null, @($Operation))
    if (-not $task.Wait(20000)) { throw 'Windows PDF render exceeded twenty seconds.' }
}

$storageFile = Wait-Operation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($sourcePath)) ([Windows.Storage.StorageFile])
$document = Wait-Operation ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($storageFile)) ([Windows.Data.Pdf.PdfDocument])
if (Test-Path -LiteralPath $outputPath) { throw 'Preserve prior QA images; choose a new output directory.' }
New-Item -ItemType Directory -Path $outputPath | Out-Null
$count = $document.PageCount
if ($MaxPages -gt 0) { $count = [Math]::Min($count, $MaxPages) }
for ($index = 0; $index -lt $count; $index++) {
    $page = $document.GetPage($index)
    $buffer = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $options = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth = $Width
    Wait-Action ($page.RenderToStreamAsync($buffer, $options))
    $buffer.Seek(0)
    $readStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($buffer)
    $target = Join-Path $outputPath ('page-{0:D2}.png' -f ($index + 1))
    $fileStream = [IO.File]::Open($target, [IO.FileMode]::Create)
    $readStream.CopyTo($fileStream)
    $fileStream.Dispose()
    $readStream.Dispose()
    $page.Dispose()
}
Write-Output ('Rendered {0} of {1} PDF pages using Windows.Data.Pdf; scratch: {2}' -f $count, $document.PageCount, $outputPath)
