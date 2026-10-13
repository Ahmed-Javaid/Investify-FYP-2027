param([Parameter(Mandatory=$true)][ValidateSet('Build','Render','Publish','Document','Verified','Commit','Package','Verify')][string]$Stage)
$ErrorActionPreference='Stop'
$projectPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($projectPath -ne 'E:\Uni_Stuff\FYP\Investify') { throw 'Use this workflow only in the intended project.' }
$env:TEMP='E:\AI-Tools\Temp'
$env:TMP='E:\AI-Tools\Temp'
$env:PYTHONDONTWRITEBYTECODE='1'
$pythonPath='E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe'
$reportBuild='E:\AI-Tools\Temp\investify-report-build-20261013-ci-roles-run02'
$deckBuild='E:\AI-Tools\Temp\investify-report-build-presentation-20261013-ci-roles-run02'
$reportRender='E:\AI-Tools\Temp\investify-mid1-report-qa-20261013-ci-roles-run02'
$deckRender='E:\AI-Tools\Temp\investify-presentation-qa-20261013-ci-roles-run02'
Push-Location -LiteralPath $projectPath
try {
    switch ($Stage) {
        'Document' {
            & $pythonPath -B tools/update_mid1_ci_handoff.py
            if ($LASTEXITCODE -ne 0) { throw 'Current navigation update failed.' }
        }
        'Verified' {
            & $pythonPath -B tools/update_mid1_ci_handoff.py --verified
            if ($LASTEXITCODE -ne 0) { throw 'Verified handover update failed.' }
        }
        'Build' {
            & $pythonPath -B tools/review_mid1_artifacts.py inputs --output E:/AI-Tools/Temp/investify-mid1-ci-role-inputs-20261013-run02.json
            if ($LASTEXITCODE -ne 0) { throw 'Source inventory failed.' }
            & $pythonPath -B tools/build_mid1_pdfs.py --run-id 20261013-ci-roles-run02
            if ($LASTEXITCODE -ne 0) { throw 'PDF build failed.' }
        }
        'Render' {
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $reportBuild 'main.pdf') -OutputDirectory $reportRender -Width 1400
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $deckBuild 'main.pdf') -OutputDirectory $deckRender -Width 1600
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $reportRender --output E:/AI-Tools/Temp/investify-report-sheets-20261013-ci-roles-run02
            if ($LASTEXITCODE -ne 0) { throw 'Report QA preparation failed.' }
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $deckRender --output E:/AI-Tools/Temp/investify-deck-sheets-20261013-ci-roles-run02
            if ($LASTEXITCODE -ne 0) { throw 'Slide QA preparation failed.' }
        }
        'Publish' {
            & $pythonPath -B tools/review_mid1_artifacts.py publish --inputs E:/AI-Tools/Temp/investify-mid1-ci-role-inputs-20261013-run02.json --report-build $reportBuild --report-render $reportRender --report-output deliverables/Investify_FYP1_Mid_Report_Work_Division_CI_20261013.pdf --deck-build $deckBuild --deck-render $deckRender --deck-output deliverables/Investify_FYP1_Mid_Presentation_Work_Division_CI_20261013.pdf --run-id 20261013_run03 --visually-reviewed
            if ($LASTEXITCODE -ne 0) { throw 'Reviewed PDF publication failed.' }
        }
        'Commit' {
            git add -- .gitignore .github/workflows/mideval-evidence.yml code/scripts/run_mid1_ci.py code/tests/test_ci_runner.py code/README.md README.md planning deliverables report presentation tools evidence
            if ($LASTEXITCODE -ne 0) { throw 'Local staging failed.' }
            git commit -m 'Reconcile proposal work division and execute shared Mid-1 CI jobs locally'
            if ($LASTEXITCODE -ne 0) { throw 'Local checkpoint failed.' }
        }
        'Package' {
            & $pythonPath -B tools/package_source_handover.py --output deliverables/investify_mid1_ci_work_division_review_20261013.zip --report-receipt evidence/handbook_report_delivery_20261013_run03.json --presentation-receipt evidence/handbook_presentation_delivery_20261013_run03.json
            if ($LASTEXITCODE -ne 0) { throw 'Clean source review packaging failed.' }
        }
        'Verify' {
            & $pythonPath -B tools/verify_source_handover.py --archive deliverables/investify_mid1_ci_work_division_review_20261013.zip --receipt-prefix ci_work_division_review_20261013
            if ($LASTEXITCODE -ne 0) { throw 'Actual source ZIP extraction check failed.' }
        }
    }
} finally { Pop-Location }
