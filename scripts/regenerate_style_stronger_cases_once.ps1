param(
  [string]$ApiBase = 'http://127.0.0.1:8001'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$caseRoot = Join-Path $projectRoot 'docs\examples'
$mapping = @(
  @{
    Style='songhua'; Name='宋画青绿山水'; Subject='一只梅花鹿，清晰保留鹿角、鹿首、四肢和背部白色斑点'; Title='青山鹿影'
    Theme='《青山鹿影》。让梅花鹿成为画面明确的唯一动物主体，融入宋代青绿山水长卷。以石青、石绿、孔雀石与赭石的传统矿物颜料分层设色，轮廓用细劲墨线勾勒，山体采用重彩青绿、层峦叠嶂、溪谷云气和克制留白；鹿身以工笔线描与平涂设色表达，不要野生动物摄影质感。远近山峰、松石和水岸构成完整山水空间，但不得遮挡鹿的四肢、鹿角与斑点。'
    Negative='仙鹤，鹤，其他鸟类，其他大型动物，人物，现代建筑，摄影写实皮毛，水彩照片感，文字，乱码，水印，模糊，畸形鹿角，裁切主体'
  },
  @{
    Style='zhuxianzhen'; Name='朱仙镇木版年画'; Subject='一只狸花猫，清晰保留猫的面部、虎斑纹、四肢和上扬长尾'; Title='瑞猫迎春'
    Theme='《瑞猫迎春》。让狸花猫成为画面唯一动物主体，转化为鲜明的朱仙镇木版年画。采用朱砂红、明黄、松石绿、墨黑的高对比大色块，粗黑刀刻式轮廓、平面化形体、清楚可见的木版套色错版肌理和传统年画边饰；猫的虎斑纹转译为有节奏的版画线刻，四周可用祥云、牡丹与海水纹围合，形成饱满、对称、民俗装饰性构图。必须一眼看出是套色木版年画而非数码厚涂或写实插画。'
    Negative='仙鹤，鹤，其他鸟类，其他动物，人物，门神人物，摄影写实毛发，油画厚涂，柔焦渐变，文字，乱码，水印，模糊，畸形猫，多条尾巴，裁切主体'
  },
  @{
    Style='bianxiu'; Name='汴绣纹样'; Subject='一条金鱼，清晰保留鱼身、鱼眼、鱼鳞和飘逸长尾鳍'; Title='锦鳞入绣'
    Theme='《锦鳞入绣》。以金鱼作为画面唯一动物主体，创作成可一眼识别为传统汴绣的绣品画。让全画主要形面由真实丝线针脚构成：鱼鳞使用层层叠叠的盘金与鳞片针、鱼身用顺势长短针塑造圆润体积，尾鳍以细丝线分股、渐变排针表现飘逸透光；明确呈现绸缎底布、丝线方向、针脚起伏和绣线高光。辅以少量水波和水草刺绣纹样，保持金鱼完整居中。不要生成照片、普通水彩或仅有细纹理的平面插画。'
    Negative='仙鹤，鸟类，其他动物，牡丹主角，人物，花瓶，摄影写实鱼鳞，普通水彩画，平滑数码渐变，印刷平面图案，文字，乱码，水印，模糊，畸形鱼鳍，裁切主体'
  }
)

$health = Invoke-RestMethod -Uri "$ApiBase/health" -TimeoutSec 10
$imageStatus = $health.providers.dashscope_qwen_image
if ($health.provider -ne 'dashscope_qwen_image' -or -not $imageStatus.available -or -not $imageStatus.hasApiKey -or $health.model -ne 'qwen-image-3.0') {
  throw '健康检查未确认 DashScope Qwen Image 3.0 可用；没有提交任何重生成请求。'
}
if ($health.allowMockFallback) { throw 'Mock 回退已启用；没有提交任何重生成请求。' }

$outcomes = [System.Collections.Generic.List[object]]::new()
foreach ($case in $mapping) {
  $folder = Join-Path $caseRoot $case.Style
  $referencePath = Join-Path $folder 'reference.png'
  $generatedPath = Join-Path $folder 'generated.png'
  $metadataPath = Join-Path $folder 'metadata.json'
  if (-not (Test-Path -LiteralPath $referencePath -PathType Leaf)) { throw "缺少参考图：$($case.Style)" }
  if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) { throw "缺少先前案例记录：$($case.Style)" }
  $oldMetadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
  $history = @()
  if ($oldMetadata.generationHistory) { $history = @($oldMetadata.generationHistory) }
  $history += [PSCustomObject]@{
    generation = 'initial'
    generatedAt = $oldMetadata.generatedAt
    model = $oldMetadata.model
    styleStrength = $oldMetadata.styleStrength
    referenceImageUsed = $oldMetadata.referenceImageUsed
    modelInputImageCount = $oldMetadata.modelInputImageCount
    generatedSha256 = $oldMetadata.generatedSha256
    analysisSource = $oldMetadata.analysisSource
  }
  $referenceBytes = [System.IO.File]::ReadAllBytes($referencePath)
  $referenceSha = (Get-FileHash -LiteralPath $referencePath -Algorithm SHA256).Hash.ToLowerInvariant()
  $dataUrl = 'data:image/png;base64,' + [Convert]::ToBase64String($referenceBytes)
  $payload = @{
    theme = $case.Theme
    style = $case.Style
    styleName = $case.Name
    outputType = 'poster'
    styleStrength = 1.0
    compositionMode = 'object'
    subjectLock = $case.Subject
    negativePrompt = $case.Negative
    uploadedImage = $dataUrl
    generationProvider = 'dashscope_qwen_image'
  }

  $newMetadata = [ordered]@{
    styleId = $case.Style
    styleName = $case.Name
    referenceSubject = $case.Subject
    artworkTitle = $case.Title
    theme = $case.Theme
    referenceSource = '用户提供的 ChatGPT 生成主体参考图（原始白底图）'
    sourceFilename = $oldMetadata.sourceFilename
    referenceFilename = 'reference.png'
    referenceSha256 = $referenceSha
    provider = 'dashscope_qwen_image'
    model = 'qwen-image-3.0'
    styleStrength = 1.0
    compositionMode = 'object'
    outputType = 'poster'
    negativePrompt = $case.Negative
    inputImageCount = 1
    generatedAt = (Get-Date).ToString('o')
    generationAttempt = 'one approved style-strength retry'
    generationSucceeded = $false
    referenceImageUsed = $false
    modelInputImageCount = 0
    analysisSource = 'unavailable'
    visionProvider = $health.localVisionAnalysis.provider
    visionModel = $health.localVisionAnalysis.model
    cultureCardAnalysisSource = 'unavailable'
    generationHistory = @($history)
  }

  try {
    $response = Invoke-RestMethod -Method Post -Uri "$ApiBase/generate" -ContentType 'application/json' -Body (ConvertTo-Json -InputObject $payload -Depth 6 -Compress) -TimeoutSec 300
    if (-not $response.success -or $response.provider -ne 'dashscope_qwen_image' -or $response.model -ne 'qwen-image-3.0') { throw 'generation_response_not_confirmed' }
    $sourcePath = [string]$response.localPath
    if (-not $sourcePath -or -not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw 'generated_file_missing' }
    Copy-Item -LiteralPath $sourcePath -Destination $generatedPath -Force
    $debug = $response.debug
    $modelInputCount = if ($null -ne $debug.modelInputImageCount) { [int]$debug.modelInputImageCount } else { 0 }
    $newMetadata.generationSucceeded = $response.referenceImageUsed -eq $true -and $modelInputCount -gt 0
    $newMetadata.referenceImageUsed = $response.referenceImageUsed -eq $true
    $newMetadata.modelInputImageCount = $modelInputCount
    $newMetadata.outputImageCount = if ($null -ne $debug.outputImageCount) { [int]$debug.outputImageCount } else { 1 }
    $newMetadata.generatedSha256 = (Get-FileHash -LiteralPath $generatedPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $newMetadata.generatedBytes = (Get-Item -LiteralPath $generatedPath).Length
    $newMetadata.analysisSource = [string]$response.analysisSource
    $newMetadata.cultureCardAnalysisSource = if ($response.analysisSource -eq 'qwen3_vl' -and $response.visionAnalysis) { 'qwen3_vl_on_generated_image' } else { 'unavailable' }
    if ($response.visionAnalysis) { $newMetadata.visionAnalysis = $response.visionAnalysis }
    if (-not $newMetadata.generationSucceeded) { throw 'reference_image_usage_not_confirmed' }
    [PSCustomObject]$newMetadata | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $metadataPath -Encoding utf8
    $outcomes.Add([PSCustomObject]@{
      Style = $case.Style
      Success = $newMetadata.generationSucceeded
      ReferenceConfirmed = $newMetadata.referenceImageUsed
      ModelInputImageCount = $newMetadata.modelInputImageCount
      AnalysisSource = $newMetadata.analysisSource
      OutputBytes = $newMetadata.generatedBytes
      Title = $case.Title
    })
    Write-Output ($outcomes[-1] | ConvertTo-Json -Compress)
  } catch {
    $newMetadata.failureType = $_.Exception.GetType().Name
    $newMetadata.failureStage = 'generation_or_analysis'
    [PSCustomObject]$newMetadata | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $metadataPath -Encoding utf8
    $outcomes.Add([PSCustomObject]@{ Style=$case.Style; Success=$false; FailureType=$newMetadata.failureType; Note='没有自动重试' })
    Write-Output ($outcomes[-1] | ConvertTo-Json -Compress)
  }
}

$outcomes | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $caseRoot 'regeneration_summary.json') -Encoding utf8
