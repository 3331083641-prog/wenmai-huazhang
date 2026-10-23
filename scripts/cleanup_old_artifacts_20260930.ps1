$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath('D:\wenmai-huazhang')
$reportRoot = Join-Path $root 'iCAN_应用方案'
$sourceRoot = Join-Path $reportRoot '01_源文件'
$revision = Join-Path $reportRoot 'figures\revision_02'
$tex = Join-Path $sourceRoot '纹脉华章_2026iCAN_AI应用创新挑战赛_应用方案.tex'
$pdf = Join-Path $sourceRoot '纹脉华章_2026iCAN_AI应用创新挑战赛_应用方案.pdf'
$targets = [Collections.Generic.List[string]]::new()
function Add-Target([string]$path) {
    if (Test-Path -LiteralPath $path) { $targets.Add([IO.Path]::GetFullPath($path)) }
}
$texText = Get-Content -LiteralPath $tex -Raw -Encoding UTF8
$protected = [Collections.Generic.List[string]]::new()
foreach ($path in @($tex,$pdf,(Join-Path $root 'backend\app.py'),(Join-Path $root 'backend\provider_service.py'),(Join-Path $root 'frontend\src\pages\AICreator.tsx'),(Join-Path $revision 'sources\figure_03_ScientificIllustrator.pptx'))) {
    $protected.Add([IO.Path]::GetFullPath($path))
}
foreach ($m in [regex]::Matches($texText, '\\includegraphics\[[^\]]*\]\{([^}]+)\}')) {
    $protected.Add([IO.Path]::GetFullPath((Join-Path $sourceRoot $m.Groups[1].Value)))
}
foreach ($case in Get-ChildItem -LiteralPath (Join-Path $reportRoot '05_生成案例\正式验收_20260929') -File -Recurse) {
    $protected.Add($case.FullName)
}
foreach ($path in $protected) {
    if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing current artifact: $path" }
}
$beforeHashes = @{}
foreach ($path in $protected) { $beforeHashes[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
# Keep only the compact final review records; rendered inspection pages are disposable.
foreach ($name in @('final_audit.json','dense_layout_audit.json','review_geometry.json')) {
    $old = Join-Path $sourceRoot "_pdf_review_clean\$name"
    if (Test-Path -LiteralPath $old) { Copy-Item -LiteralPath $old -Destination (Join-Path $revision "reviews\$name") -Force }
}
foreach ($rel in @(
    'backup','01_源文件\修改前备份','01_源文件\_pdf_review','01_源文件\_pdf_review_clean','01_源文件\_pdf_review_final',
    '01_源文件\assets','01_源文件\延期功能归档','figures\_redraw','figures\_evidence','figures\final',
    'figures\scientific_illustrator','figures\revision_02\backup','figures\revision_02\runtime',
    'figures\scientific_illustrator_source\previews','figures\scientific_illustrator_source\render_checks'
)) { Add-Target (Join-Path $reportRoot $rel) }
foreach ($rel in @('00_original_zip','release\wenmai-huazhang-submit','release\wenmai-huazhang-submit.zip','outputs\video\dry','outputs\video\explore','outputs\video\verify3')) { Add-Target (Join-Path $root $rel) }
foreach ($rel in @('figures\figure_01.png','figures\figure_02.png','figures\figure_03.png','figures\figure_04.png','figures\figure_05.png','figures\review_sources_contact.png','figures\revision_02\assets\figure_03_user_matrix_all_text_removed.png','figures\revision_02\assets\figure_06_dual_model_all_text_removed.png','figures\revision_02\assets\figure04_landscape_crop.png')) { Add-Target (Join-Path $reportRoot $rel) }
foreach ($path in @('D:\Codex\backups\wenmai-huazhang','D:\Codex\backups\figure_01_reconstruction_spec_STALE_20260930.md','D:\Codex\temp\wenmai_application_review','D:\Codex\temp\wenmai-qwen-migration')) { Add-Target $path }
# Browser exports from this project are already represented by the formal D-drive evidence.
Get-ChildItem -LiteralPath 'D:\Codex\outputs\playwright' -File -Filter 'wenmai*' | ForEach-Object { Add-Target $_.FullName }
Get-ChildItem -LiteralPath $sourceRoot -File | Where-Object { $_.Extension -in @('.aux','.log','.out','.toc','.xdv','.fls','.fdb_latexmk','.synctex','.gz') } | ForEach-Object { Add-Target $_.FullName }
$duplicatePdf = Join-Path $sourceRoot '纹脉华章_应用方案_简洁版.pdf'
if ((Test-Path -LiteralPath $duplicatePdf) -and ((Get-FileHash -LiteralPath $duplicatePdf).Hash -eq $beforeHashes[$pdf])) { Add-Target $duplicatePdf }
Get-ChildItem -LiteralPath (Join-Path $revision 'final') -File -Filter 'figure_06.*' | ForEach-Object { Add-Target $_.FullName }
# Retain self-contained editable SVG/PPTX and the helpers needed by the current HD figures.
$keepSources = @('redraw.py','figure02.py','figure04_text_hd.py','figure07_text_hd.py','hd_common.py',
    'figure_01_value_loop_ocr.json','figure_02_pain_solution_ocr.json',
    'figure_03_ScientificIllustrator.pptx','figure_03_SI_reconstruction_spec.json','review_report.py','check_official.py')
Get-ChildItem -LiteralPath (Join-Path $revision 'sources') -Force | Where-Object { $_.Name -notin $keepSources } | ForEach-Object { Add-Target $_.FullName }
Get-ChildItem -LiteralPath (Join-Path $revision 'reviews') -File | Where-Object { $_.Extension -in @('.png','.jpg') -or $_.Name -in @('figure_05.md','figure_06.md') } | ForEach-Object { Add-Target $_.FullName }
Get-ChildItem -LiteralPath (Join-Path $reportRoot '02_正文') -File | ForEach-Object { Add-Target $_.FullName }
foreach ($dir in @('backend\__pycache__','backend\providers\__pycache__','backend\services\__pycache__')) { Add-Target (Join-Path $root $dir) }
# Resolve and verify every destructive target before the first deletion.
$allowExternal = @('D:\Codex\backups\wenmai-huazhang','D:\Codex\backups\figure_01_reconstruction_spec_STALE_20260930.md','D:\Codex\temp\wenmai_application_review','D:\Codex\temp\wenmai-qwen-migration')
$uniqueTargets = @($targets | Sort-Object -Unique)
foreach ($path in $uniqueTargets) {
    $inside = $path.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase)
    $browserFile = [IO.Path]::GetDirectoryName($path) -eq 'D:\Codex\outputs\playwright' -and [IO.Path]::GetFileName($path).StartsWith('wenmai',[StringComparison]::OrdinalIgnoreCase)
    if (!$inside -and $path -notin $allowExternal -and !$browserFile) { throw "Target outside cleanup scope: $path" }
    foreach ($keep in $protected) {
        if ($keep -eq $path -or $keep.StartsWith($path+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Current artifact would be removed: $keep" }
    }
    $item = Get-Item -LiteralPath $path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Refusing reparse-point target: $path" }
    if ($item.PSIsContainer) {
        $links = Get-ChildItem -LiteralPath $path -Force -Recurse | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
        if ($links) { throw "Refusing directory containing reparse points: $path" }
    }
}
$deleted = @(); $errors = @(); $totalFiles = 0; $totalBytes = 0L
foreach ($path in $uniqueTargets) {
    $item = Get-Item -LiteralPath $path -Force
    $files = if ($item.PSIsContainer) { @(Get-ChildItem -LiteralPath $path -File -Force -Recurse) } else { @($item) }
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    try {
        Remove-Item -LiteralPath $path -Recurse -Force
        $deleted += @{path=$path;files=$files.Count;bytes=$bytes}
        $totalFiles += $files.Count; $totalBytes += $bytes
    } catch { $errors += @{path=$path;reason=$_.Exception.Message} }
}
$checks = @()
foreach ($path in $protected) {
    $ok = (Test-Path -LiteralPath $path) -and ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -eq $beforeHashes[$path])
    $checks += @{path=$path;unchanged=$ok}
    if (!$ok) { throw "Protected artifact verification failed: $path" }
}
$record=@{date='2026-09-30';deleted_files=$totalFiles;freed_bytes=$totalBytes;deleted=$deleted;errors=$errors;protected_artifacts=$checks}
$previousRecord = Join-Path $root 'logs\project_cleanup_20260930.json'
if (Test-Path -LiteralPath $previousRecord) {
    $previous = Get-Content -LiteralPath $previousRecord -Raw -Encoding UTF8 | ConvertFrom-Json
    $record.deleted_files += $previous.deleted_files
    $record.freed_bytes += $previous.freed_bytes
    $record.deleted = @($previous.deleted) + $deleted
    if ($previous.final_validation) { $record.final_validation = $previous.final_validation }
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $root 'logs\project_cleanup_20260930.json') -Encoding UTF8
@{deleted_files=$record.deleted_files;freed_MB=[math]::Round($record.freed_bytes/1MB,1);errors=$errors;protected_unchanged=$checks.Count} | ConvertTo-Json -Depth 4
