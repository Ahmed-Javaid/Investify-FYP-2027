param([Parameter(Mandatory=$true)][ValidateSet('Build','Render','Publish','Document','Verified','Commit','Package','Verify')][string]$Stage)
$ErrorActionPreference='Stop'
$projectPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($projectPath -ne 'E:\Uni_Stuff\FYP\Investify') { throw 'Use this workflow only in the intended project.' }
$env:TEMP='E:\AI-Tools\Temp'
$env:TMP='E:\AI-Tools\Temp'
$env:PYTHONDONTWRITEBYTECODE='1'
$pythonPath='E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe'
$reportBuild='E:\AI-Tools\Temp\investify-report-build-20261013-metadata-run01'
$deckBuild='E:\AI-Tools\Temp\investify-report-build-presentation-20261013-metadata-run01'
$reportRender='E:\AI-Tools\Temp\investify-mid1-report-qa-20261013-metadata-run01'
$deckRender='E:\AI-Tools\Temp\investify-presentation-qa-20261013-metadata-run01'
Push-Location -LiteralPath $projectPath
try {
    switch ($Stage) {
        'Build' {
            & $pythonPath -B tools/review_mid1_artifacts.py inputs --output E:/AI-Tools/Temp/investify-mid1-metadata-inputs-20261013-run01.json
            if ($LASTEXITCODE -ne 0) { throw 'Source inventory failed.' }
            & $pythonPath -B tools/build_mid1_pdfs.py --run-id 20261013-metadata-run01
            if ($LASTEXITCODE -ne 0) { throw 'PDF build failed.' }
        }
        'Render' {
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $reportBuild 'main.pdf') -OutputDirectory $reportRender -Width 1400
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $deckBuild 'main.pdf') -OutputDirectory $deckRender -Width 1600
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $reportRender --output E:/AI-Tools/Temp/investify-report-sheets-20261013-metadata-run01
            if ($LASTEXITCODE -ne 0) { throw 'Report QA preparation failed.' }
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $deckRender --output E:/AI-Tools/Temp/investify-deck-sheets-20261013-metadata-run01
            if ($LASTEXITCODE -ne 0) { throw 'Slide QA preparation failed.' }
        }
        'Publish' {
            & $pythonPath -B tools/review_mid1_artifacts.py publish --inputs E:/AI-Tools/Temp/investify-mid1-metadata-inputs-20261013-run01.json --report-build $reportBuild --report-render $reportRender --report-output deliverables/Investify_FYP1_Mid_Report_Fall_2026_20261013.pdf --deck-build $deckBuild --deck-render $deckRender --deck-output deliverables/Investify_FYP1_Mid_Presentation_Fall_2026_20261013.pdf --run-id 20261013_run05 --visually-reviewed --visual-review-receipt evidence/metadata_visual_review_20261013.json
            if ($LASTEXITCODE -ne 0) { throw 'Reviewed PDF publication failed.' }
        }
        'Document' {
            & $pythonPath -B tools/update_mid1_ci_handoff.py --member-allocation --fall-metadata --delivery-run-id 20261013_run05 --archive-id fall_2026_review_20261013
            if ($LASTEXITCODE -ne 0) { throw 'Current navigation update failed.' }
        }
        'Verified' {
            & $pythonPath -B tools/update_mid1_ci_handoff.py --member-allocation --fall-metadata --delivery-run-id 20261013_run05 --archive-id fall_2026_review_20261013 --verified
            if ($LASTEXITCODE -ne 0) { throw 'Verified navigation update failed.' }
        }
        'Commit' {
            git add -- README.md code/README.md planning deliverables report presentation tools evidence
            if ($LASTEXITCODE -ne 0) { throw 'Local staging failed.' }
            git commit -m 'Record Fall 2026 Mid-1 term and user-selected Sunday report date'
            if ($LASTEXITCODE -ne 0) { throw 'Local checkpoint failed.' }
        }
        'Package' {
            & $pythonPath -B tools/package_source_handover.py --output deliverables/investify_mid1_fall_2026_review_20261013.zip --report-receipt evidence/handbook_report_delivery_20261013_run05.json --presentation-receipt evidence/handbook_presentation_delivery_20261013_run05.json
            if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed.' }
        }
        'Verify' {
            & $pythonPath -B tools/verify_source_handover.py --archive deliverables/investify_mid1_fall_2026_review_20261013.zip --receipt-prefix fall_2026_review_20261013
            if ($LASTEXITCODE -ne 0) { throw 'Actual ZIP extraction verification failed.' }
        }
    }
} finally { Pop-Location }
