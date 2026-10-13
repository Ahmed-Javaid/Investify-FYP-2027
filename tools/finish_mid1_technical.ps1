param([Parameter(Mandatory=$true)][ValidateSet('Build','Render','Publish','Document','Verified','Commit','Package','Verify','ConfigureRemote','Push')][string]$Stage)
$ErrorActionPreference='Stop'
$projectPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($projectPath -ne 'E:\Uni_Stuff\FYP\Investify') { throw 'Use this workflow only in the intended project.' }
$env:TEMP='E:\AI-Tools\Temp'
$env:TMP='E:\AI-Tools\Temp'
$env:PYTHONDONTWRITEBYTECODE='1'
$pythonPath='E:\AI-Tools\Temp\investify-ui-py311\Scripts\python.exe'
$reportBuild='E:\AI-Tools\Temp\investify-report-build-20261013-technical-run03'
$deckBuild='E:\AI-Tools\Temp\investify-report-build-presentation-20261013-technical-run03'
$reportRender='E:\AI-Tools\Temp\investify-mid1-report-qa-20261013-technical-run03'
$deckRender='E:\AI-Tools\Temp\investify-presentation-qa-20261013-technical-run03'
Push-Location -LiteralPath $projectPath
try {
    switch ($Stage) {
        'ConfigureRemote' {
            $remoteUrl='https://github.com/Ahmed-Javaid/Investify-FYP-2027.git'
            if ((git remote) -contains 'origin') {
                $existing=git remote get-url origin
                if ($existing -ne $remoteUrl) { throw 'An unrelated origin already exists; preserve it.' }
            } else {
                git remote add origin $remoteUrl
                if ($LASTEXITCODE -ne 0) { throw 'Destination remote configuration failed.' }
            }
        }
        'Push' {
            $remoteUrl=git remote get-url origin
            if ($remoteUrl -ne 'https://github.com/Ahmed-Javaid/Investify-FYP-2027.git') { throw 'Push only to the user-specified destination.' }
            if (git status --porcelain) { throw 'Save the reviewed local checkpoint before pushing.' }
            git -c credential.interactive=never push -u origin main
            if ($LASTEXITCODE -ne 0) { throw 'Authorized push failed.' }
        }
        'Build' {
            & $pythonPath -B tools/review_mid1_artifacts.py inputs --output E:/AI-Tools/Temp/investify-mid1-technical-inputs-20261013-run03.json
            if ($LASTEXITCODE -ne 0) { throw 'Source inventory failed.' }
            & $pythonPath -B tools/build_mid1_pdfs.py --run-id 20261013-technical-run03
            if ($LASTEXITCODE -ne 0) { throw 'PDF build failed.' }
        }
        'Render' {
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $reportBuild 'main.pdf') -OutputDirectory $reportRender -Width 1400
            & '.\tools\render_pdf_windows.ps1' -PdfPath (Join-Path $deckBuild 'main.pdf') -OutputDirectory $deckRender -Width 1600
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $reportRender --output E:/AI-Tools/Temp/investify-report-sheets-20261013-technical-run03
            if ($LASTEXITCODE -ne 0) { throw 'Report QA preparation failed.' }
            & $pythonPath -B tools/review_mid1_artifacts.py montage --source $deckRender --output E:/AI-Tools/Temp/investify-deck-sheets-20261013-technical-run03
            if ($LASTEXITCODE -ne 0) { throw 'Slide QA preparation failed.' }
        }
        'Publish' {
            & $pythonPath -B tools/review_mid1_artifacts.py publish --inputs E:/AI-Tools/Temp/investify-mid1-technical-inputs-20261013-run03.json --report-build $reportBuild --report-render $reportRender --report-output deliverables/Investify_FYP1_Mid_Report_Technical_Completion_20261013.pdf --deck-build $deckBuild --deck-render $deckRender --deck-output deliverables/Investify_FYP1_Mid_Presentation_Technical_Completion_20261013.pdf --run-id 20261013_run06 --visually-reviewed --visual-review-receipt evidence/technical_visual_review_20261013.json
            if ($LASTEXITCODE -ne 0) { throw 'Reviewed PDF publication failed.' }
        }
        'Document' {
            & $pythonPath -B tools/update_mid1_technical_status.py
            if ($LASTEXITCODE -ne 0) { throw 'Current navigation update failed.' }
        }
        'Verified' {
            & $pythonPath -B tools/update_mid1_technical_status.py --verified
            if ($LASTEXITCODE -ne 0) { throw 'Verified navigation update failed.' }
        }
        'Commit' {
            git add -- .github code README.md planning deliverables report presentation tools evidence
            if ($LASTEXITCODE -ne 0) { throw 'Local staging failed.' }
            git commit -m 'Complete technical Mid-1 scope and gated CI delivery'
            if ($LASTEXITCODE -ne 0) { throw 'Local checkpoint failed.' }
        }
        'Package' {
            & $pythonPath -B tools/package_source_handover.py --output deliverables/investify_mid1_technical_review_20261013.zip --report-receipt evidence/handbook_report_delivery_20261013_run06.json --presentation-receipt evidence/handbook_presentation_delivery_20261013_run06.json
            if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed.' }
        }
        'Verify' {
            & $pythonPath -B tools/verify_source_handover.py --archive deliverables/investify_mid1_technical_review_20261013.zip --receipt-prefix technical_review_20261013
            if ($LASTEXITCODE -ne 0) { throw 'Actual ZIP extraction verification failed.' }
        }
    }
} finally { Pop-Location }
