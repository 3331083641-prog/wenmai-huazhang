param(
  [string]$ApiBase = 'http://127.0.0.1:8001'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Join-Path $projectRoot 'docs\examples'
$mapping = @(
  @{ Style='zhuxianzhen'; Name='朱仙镇木版年画'; Subject='一只狸花猫，保留猫的头脸、虎斑毛色、四肢与上扬环绕的长尾'; Title='瑞猫迎春'; File='ChatGPT 图像 2026年10月8日 08_48_43-1.png'; Negative='仙鹤，鹤，其他鸟类，其他动物，人物，门神人物，文字，水印，现代物品，模糊，畸形结构' },
  @{ Style='bianxiu'; Name='汴绣纹样'; Subject='一条金鱼，保留鱼身、清晰鱼鳞、眼睛和飘逸长尾鳍'; Title='锦鳞入绣'; File='ChatGPT 图像 2026年10月8日 08_48_45-2.png'; Negative='仙鹤，鸟类，其他动物，牡丹主角，人物，花瓶，文字，水印，现代物品，模糊，畸形结构' },
  @{ Style='songhua'; Name='宋画青绿山水'; Subject='一只梅花鹿，保留鹿角、鹿身、四肢与背部白色斑点'; Title='青山鹿影'; File='ChatGPT 图像 2026年10月8日 08_48_47-3.png'; Negative='仙鹤，鸟类，其他大型动物，人物，现代建筑，文字，水印，模糊，畸形结构' },
  @{ Style='qinghua'; Name='青花瓷纹样'; Subject='一只展开双翅的蝴蝶，保留对称翅形、触角和身体'; Title='青花蝶韵'; File='ChatGPT 图像 2026年10月8日 08_48_48-4.png'; Negative='仙鹤，鸟类，其他动物，花瓶，瓷器主体，人物，文字，水印，模糊，畸形结构' },
  @{ Style='jianzhi'; Name='中国剪纸'; Subject='一只赤狐，保留尖耳、狐狸面部、四肢和蓬松长尾轮廓'; Title='剪影灵狐'; File='ChatGPT 图像 2026年10月8日 08_48_50-5.png'; Negative='仙鹤，鸟类，其他动物，人物，写实照片，文字，水印，模糊，断裂剪纸结构' }
)

$health = Invoke-RestMethod -Uri "$ApiBase/health" -TimeoutSec 10
$imageStatus = $health.providers.dashscope_qwen_image
$visionStatus = $health.localVisionAnalysis
if ($health.provider -ne 'dashscope_qwen_image' -or -not $imageStatus.available -or -not $imageStatus.hasApiKey -or $health.model -ne 'qwen-image-3.0') {
  throw '健康检查未确认 DashScope Qwen Image 3.0 可用；没有提交任何生成请求。'
}
if ($health.allowMockFallback) {
  throw '检测到 Mock 回退已启用；没有提交任何生成请求。'
}

$results = [System.Collections.Generic.List[object]]::new()
foreach ($case in $mapping) {
  $folder = Join-Path $caseRoot $case.Style
  $referencePath = Join-Path $folder 'reference.png'
  if (-not (Test-Path -LiteralPath $referencePath -PathType Leaf)) {
    throw "缺少用户提供的参考图：$($case.Style)"
  }
  $referenceBytes = [System.IO.File]::ReadAllBytes($referencePath)
  $sha = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($referenceBytes)).ToLowerInvariant()
  $dataUrl = 'data:image/png;base64,' + [Convert]::ToBase64String($referenceBytes)
  $payload = @{
    theme = "$($case.Title)：$($case.Subject)。将该主体转化为$($case.Name)视觉作品，保持主体清晰完整，主体身份高于装饰题材。"
    style = $case.Style
    styleName = $case.Name
    outputType = 'poster'
    styleStrength = 0.65
    compositionMode = 'object'
    subjectLock = $case.Subject
    negativePrompt = $case.Negative
    uploadedImage = $dataUrl
    generationProvider = 'dashscope_qwen_image'
  }

  $resultRecord = [ordered]@{
    styleId = $case.Style
    styleName = $case.Name
    referenceSubject = $case.Subject
    artworkTitle = $case.Title
    referenceSource = '用户提供的 ChatGPT 生成主体参考图（原始白底图）'
    sourceFilename = $case.File
    referenceFilename = 'reference.png'
    referenceSha256 = $sha
    provider = 'dashscope_qwen_image'
    model = 'qwen-image-3.0'
    styleStrength = 0.65
    compositionMode = 'object'
    outputType = 'poster'
    negativePrompt = $case.Negative
    inputImageCount = 1
    generatedAt = (Get-Date).ToString('o')
    generationSucceeded = $false
    referenceImageUsed = $false
    modelInputImageCount = 0
    analysisSource = 'unavailable'
    visionProvider = $visionStatus.provider
    visionModel = $visionStatus.model
    cultureCardAnalysisSource = 'not_generated'
  }

  try {
    $response = Invoke-RestMethod -Method Post -Uri "$ApiBase/generate" -ContentType 'application/json' -Body (ConvertTo-Json -InputObject $payload -Depth 6 -Compress) -TimeoutSec 300
    if (-not $response.success -or $response.provider -ne 'dashscope_qwen_image' -or $response.model -ne 'qwen-image-3.0') {
      throw 'generation_response_not_confirmed'
    }
    $outputPath = [string]$response.localPath
    if (-not $outputPath -or -not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
      throw 'generated_file_missing'
    }
    $destination = Join-Path $folder 'generated.png'
    Copy-Item -LiteralPath $outputPath -Destination $destination -Force
    $debug = $response.debug
    $modelInputCount = 0
    if ($null -ne $debug.modelInputImageCount) { $modelInputCount = [int]$debug.modelInputImageCount }
    $resultRecord.generationSucceeded = $true
    $resultRecord.referenceImageUsed = ($response.referenceImageUsed -eq $true -and $modelInputCount -gt 0)
    $resultRecord.modelInputImageCount = $modelInputCount
    $resultRecord.outputImageCount = if ($null -ne $debug.outputImageCount) { [int]$debug.outputImageCount } else { 1 }
    $resultRecord.generatedSha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    $resultRecord.generatedBytes = (Get-Item -LiteralPath $destination).Length
    $resultRecord.analysisSource = [string]$response.analysisSource
    $resultRecord.cultureCardAnalysisSource = if ($response.analysisSource -eq 'qwen3_vl' -and $response.visionAnalysis) { 'qwen3_vl_on_generated_image' } else { 'unavailable' }
    if ($response.visionAnalysis) { $resultRecord.visionAnalysis = $response.visionAnalysis }
    if ($resultRecord.referenceImageUsed -ne $true) { $resultRecord.generationSucceeded = $false }
    $results.Add([PSCustomObject]$resultRecord)
    [PSCustomObject]$resultRecord | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $folder 'metadata.json') -Encoding utf8
    [PSCustomObject]@{
      Style = $case.Style
      GenerationSucceeded = $resultRecord.generationSucceeded
      ReferenceConfirmed = $resultRecord.referenceImageUsed
      ModelInputImageCount = $resultRecord.modelInputImageCount
      AnalysisSource = $resultRecord.analysisSource
      CultureCardTitle = if ($response.visionAnalysis) { $response.visionAnalysis.title } else { '未分析' }
      OutputBytes = $resultRecord.generatedBytes
    } | ConvertTo-Json -Compress
  } catch {
    $resultRecord.failureType = $_.Exception.GetType().Name
    $resultRecord.failureStage = 'generation_or_analysis'
    $results.Add([PSCustomObject]$resultRecord)
    [PSCustomObject]$resultRecord | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $folder 'metadata.json') -Encoding utf8
    [PSCustomObject]@{ Style=$case.Style; GenerationSucceeded=$false; FailureType=$resultRecord.failureType; Note='记录失败，不会自动重试。' } | ConvertTo-Json -Compress
  }
}

$results | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $caseRoot 'generation_summary.json') -Encoding utf8
