param([switch]$Apply)

$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath('E:\Uni_Stuff\FYP').TrimEnd('\')
$project = Join-Path $workspace 'Investify'
$archiveRoot = Join-Path $workspace '_archives'
$receiptPath = Join-Path $project 'evidence\workspace_reorganization_20261012.json'

function Assert-WorkspacePath([string]$path) {
    $resolved = [IO.Path]::GetFullPath($path)
    if (-not $resolved.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes the explicit workspace: $resolved"
    }
    return $resolved
}

$legacyNames = @(
    'backup_pre_fix', 'Mid_Eval', 'old', 'poc', 'reference', 'slides',
    'FUTURE_WORK_staleness_gate.md', 'Investify Updated (1).pptx',
    'Investify_Concept.docx', 'Investify_Concept.pdf', 'Investify_Defence_Concept.pptx',
    'Investify_Defence_Full.pptx', 'Investify_PoC.zip', 'Investify_Proposal_Full.docx',
    'Investify_Proposal_Full.pdf', 'PROJECT_STATUS.md'
)
$moves = @([ordered]@{ old_relative = 'GPT_MIDEVAL'; new_relative = '_archives\workspaces\GPT_MIDEVAL' })
foreach ($name in $legacyNames) {
    $moves += [ordered]@{ old_relative = $name; new_relative = '_archives\legacy_fyp_20261012\' + $name }
}

if (Test-Path -LiteralPath $receiptPath) { throw 'Preserve the existing relocation receipt; do not repeat this move.' }
$files = @()
foreach ($move in $moves) {
    $source = Assert-WorkspacePath (Join-Path $workspace $move.old_relative)
    $target = Assert-WorkspacePath (Join-Path $workspace $move.new_relative)
    if (-not $target.StartsWith($archiveRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Destination must be inside the workspace archive directory.'
    }
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing source: $source" }
    if (Test-Path -LiteralPath $target) { throw "Existing destination would be overwritten: $target" }
    $entry = Get-Item -LiteralPath $source -Force
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Preserve reparse point: $source" }
    if ($entry.PSIsContainer) {
        $children = @(Get-ChildItem -LiteralPath $source -Recurse -Force)
        if ($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
            throw "Source contains a reparse point: $source"
        }
        $sourceFiles = @($children | Where-Object { -not $_.PSIsContainer })
    } else { $sourceFiles = @($entry) }
    foreach ($file in $sourceFiles) {
        $oldRelative = $file.FullName.Substring($workspace.Length + 1)
        $suffix = $file.FullName.Substring($source.Length)
        $newRelative = $move.new_relative + $suffix
        $files += [ordered]@{
            old_relative = $oldRelative; new_relative = $newRelative
            bytes = $file.Length; sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    $move.status = 'planned'
}

Write-Output ("Verified move plan: {0} entries, {1} files; canonical Investify stays in place." -f $moves.Count, $files.Count)
if (-not $Apply) { return }

$receipt = [ordered]@{
    schema = 'investify-workspace-relocation-v1'
    started_utc = [DateTime]::UtcNow.ToString('o'); workspace = $workspace
    canonical_project = $project; status = 'in_progress'; passed = $false
    moves = $moves; files = $files; content_changes = $false
    scope = 'Reversible local organization; preserves old bytes, Git histories and existing ZIP archives.'
}
function Save-Receipt { $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8 }
Save-Receipt
foreach ($move in $moves) {
    $source = Assert-WorkspacePath (Join-Path $workspace $move.old_relative)
    $target = Assert-WorkspacePath (Join-Path $workspace $move.new_relative)
    $targetParent = Assert-WorkspacePath ([IO.Path]::GetDirectoryName($target))
    New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    $move.status = 'moving'; Save-Receipt
    Move-Item -LiteralPath $source -Destination $target
    $move.status = 'moved'; Save-Receipt
}

$mismatches = @()
foreach ($file in $files) {
    $target = Assert-WorkspacePath (Join-Path $workspace $file.new_relative)
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { $mismatches += $file.new_relative; continue }
    $entry = Get-Item -LiteralPath $target -Force
    if ($entry.Length -ne $file.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) {
        $mismatches += $file.new_relative
    }
}
$receipt.completed_utc = [DateTime]::UtcNow.ToString('o')
$receipt.mismatches = $mismatches
$receipt.passed = ($mismatches.Count -eq 0)
$receipt.status = if ($receipt.passed) { 'verified' } else { 'verification_failed' }
Save-Receipt
if (-not $receipt.passed) { throw 'Moved-file verification failed; consult the retained receipt.' }
Write-Output ("All {0} moved files retain their sizes and SHA256 hashes." -f $files.Count)
