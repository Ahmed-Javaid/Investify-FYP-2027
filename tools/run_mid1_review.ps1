param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Build','Render','Rebuild','Check','Record','Checkpoint','Verified','Publish','Commit','Package','Verify')]
    [string]$Stage
)
$ErrorActionPreference = 'Stop'
$projectPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($projectPath -ne 'E:\Uni_Stuff\FYP\Investify') { throw 'Use this workflow only in the intended Investify project.' }
$env:TEMP='E:\AI-Tools\Temp'
$env:TMP='E:\AI-Tools\Temp'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:MPLCONFIGDIR='E:\AI-Tools\Cache\matplotlib'
$env:NUMBA_CACHE_DIR='E:\AI-Tools\Cache\numba'
$pythonPath='E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe'
$reportBuildPath='E:\AI-Tools\Temp\investify-report-build-20261013-browser-run07'
$deckBuildPath='E:\AI-Tools\Temp\investify-report-build-presentation-20261013-browser-run07'
$reportRenderPath='E:\AI-Tools\Temp\investify-mid1-report-qa-20261013-browser-run07'
$deckRenderPath='E:\AI-Tools\Temp\investify-presentation-qa-20261013-browser-run07'
$archivePath='deliverables/investify_mid1_browser_review_20261013.zip'
Push-Location -LiteralPath $projectPath
try {
    switch ($Stage) {
        'Record' {
            & $pythonPath -B tools/record_mid1_review.py evidence
            if ($LASTEXITCODE -ne 0) { throw 'Source-bound review evidence failed.' }
        }
        'Checkpoint' {
            & $pythonPath -B tools/record_mid1_review.py checkpoint
            if ($LASTEXITCODE -ne 0) { throw 'Current checkpoint reconciliation failed.' }
        }
        'Verified' {
            & $pythonPath -B tools/record_mid1_review.py verified
            if ($LASTEXITCODE -ne 0) { throw 'Verified handover reconciliation failed.' }
        }
        'Rebuild' {
            & $PSCommandPath -Stage Build
            & $PSCommandPath -Stage Render
        }
        'Build' {
            & $pythonPath -B tools/review_mid1_artifacts.py inputs --output E:/AI-Tools/Temp/investify-mid1-review-inputs-20261013-run07.json
            if ($LASTEXITCODE -ne 0) { throw 'Build input inventory failed.' }
            & $pythonPath -B tools/build_mid1_pdfs.py --run-id 20261013-browser-run07
            if ($LASTEXITCODE -ne 0) { throw 'PDF compilation failed.' }
        }
        'Render' {
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $reportBuildPath 'main.pdf') -OutputDirectory $reportRenderPath -Width 1400
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $deckBuildPath 'main.pdf') -OutputDirectory $deckRenderPath -Width 1600
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $reportRenderPath --output E:/AI-Tools/Temp/investify-report-sheets-20261013-browser-run07
            if ($LASTEXITCODE -ne 0) { throw 'Report QA sheets failed.' }
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $deckRenderPath --output E:/AI-Tools/Temp/investify-deck-sheets-20261013-browser-run07
            if ($LASTEXITCODE -ne 0) { throw 'Slide QA sheets failed.' }
        }
        'Check' {
            & 'E:\AI-Tools\Work\investify-quality-tools\bin\ruff.exe' check --no-cache --select E4,E9,F code/app/streamlit_app.py code/app/presenter.py code/app/presenter_data.py code/app/presenter_style.py code/tests/test_presenter_ui.py tools/audit_calibration_bounds.py tools/review_presenter_browser.py tools/package_source_handover.py tools/review_mid1_artifacts.py tools/build_mid1_pdfs.py
            if ($LASTEXITCODE -ne 0) { throw 'Scoped source checks failed.' }
            git -c core.whitespace=cr-at-eol diff --check
            if ($LASTEXITCODE -ne 0) { throw 'Source whitespace checks failed.' }
            if (Test-Path -LiteralPath 'evidence/originals_preservation_browser_20261013_run02.json') { throw 'Preserve prior original-byte receipts.' }
            & $pythonPath -B tools/check_originals.py --output evidence/originals_preservation_browser_20261013_run02.json
            if ($LASTEXITCODE -ne 0) {
                $literal = Get-Content -LiteralPath 'evidence/originals_preservation_browser_20261013_run02.json' -Raw | ConvertFrom-Json
                $explained = Get-Content -LiteralPath 'evidence/originals_preservation_browser_metadata_20261013.json' -Raw | ConvertFrom-Json
                $externalConfig='E:\Uni_Stuff\investify_repo\.git\config'
                if ($literal.changed_originals.Count -ne 1 -or $literal.changed_originals[0].checked_path -ne $externalConfig -or -not $explained.in_memory_removal_reconstructs_original_bytes -or (Get-FileHash -LiteralPath $externalConfig -Algorithm SHA256).Hash.ToLowerInvariant() -ne $explained.current_sha256) {
                    throw 'A protected difference extends beyond the documented editor bookmark.'
                }
                Write-Output '223 exact original-byte matches; the sole Git editor bookmark divergence matches its retained byte-exact explanation. Literal all-file equality remains false.'
            }
        }
        'Publish' {
            # Invoke only after the assistant has inspected every rendered page.
            & $pythonPath -B tools/review_mid1_artifacts.py publish --inputs E:/AI-Tools/Temp/investify-mid1-review-inputs-20261013-run07.json --report-build $reportBuildPath --report-render $reportRenderPath --report-output deliverables/Investify_FYP1_Mid_Report_UI_Review_20261013.pdf --deck-build $deckBuildPath --deck-render $deckRenderPath --deck-output deliverables/Investify_FYP1_Mid_Presentation_UI_Review_20261013.pdf --run-id 20261013_run02 --visually-reviewed
            if ($LASTEXITCODE -ne 0) { throw 'Source-bound artifact publication failed.' }
        }
        'Commit' {
            git add -- README.md .github/workflows/mideval-evidence.yml code/app code/tests/test_presenter_ui.py code/requirements-quality.txt deliverables planning report presentation tools evidence
            if ($LASTEXITCODE -ne 0) { throw 'Could not stage the reviewed local Mid-1 increment.' }
            git commit -m 'Finish Mid-1 browser review and source-bound report and Beamer delivery'
            if ($LASTEXITCODE -ne 0) { throw 'Could not commit the reviewed local increment.' }
        }
        'Package' {
            & $pythonPath -B tools/package_source_handover.py --output $archivePath --report-receipt evidence/handbook_report_delivery_20261013_run02.json --presentation-receipt evidence/handbook_presentation_delivery_20261013_run02.json
            if ($LASTEXITCODE -ne 0) { throw 'Clean source snapshot packaging failed.' }
        }
        'Verify' {
            & $pythonPath -B tools/verify_source_handover.py --archive $archivePath --receipt-prefix browser_review_20261013
            if ($LASTEXITCODE -ne 0) { throw 'Isolated source archive verification failed.' }
        }
    }
} finally { Pop-Location }
