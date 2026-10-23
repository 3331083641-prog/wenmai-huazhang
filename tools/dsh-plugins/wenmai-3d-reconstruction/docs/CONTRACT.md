# wenmai-3d-reconstruction — 内部开发契约（v1）

> 这是插件包内部唯一的接口契约。宿主 DSH 版本：**0.2.1-rc.2**（`@deepseek-ai/dsh-tools` 同版本）。
> 任何模块改动如果改变这里的名字/参数/返回字段，必须先改本文件并通知 Lead。

## 0. 环境事实（实测）

| 项 | 值 |
|---|---|
| DSH 版本 | 0.2.1-rc.2（GUI：`D:\deepseek\DeepSeek Harness.exe`，CLI：`D:\deepseek\resources\runtime\cli\bin\dsh.cmd`） |
| Node | `ELECTRON_RUN_AS_NODE=1` + `D:\deepseek\DeepSeek Harness.exe`（Electron 内置 Node 22） |
| TypeScript | `D:\wenmai-huazhang\frontend\node_modules\typescript\lib\tsc.js`（5.8.3） |
| Blender | `D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe`（5.2.2 LTS，Python 3.13.13，numpy 2.3.4，引擎 `BLENDER_EEVEE`） |
| 项目根（唯一授权目录） | `D:\wenmai-huazhang` |
| 十张参考图 | `assets/gallery3d/references/raw/*.png`（1448×1086） |
| 现有 v5 场景 | `assets/gallery3d/blender/wenmai_gallery_v5.blend` |
| 现有布局契约 | `assets/gallery3d/exports/gallery_layout.json`（schema 2，15 个画框） |

**禁止**：访问项目根之外的文件（Blender 可执行文件除外）、调用付费 API、下载模型、同步 GitHub、修改 DSH 安装目录。

## 1. 坐标系与尺寸契约（沿用 v5，不允许另起一套）

- Blender：单位米，Z 向上，**正面朝 +Y**（街道在前场 +Y 侧；`gallery_layout.json` 的 +Z 在 Three.js 里对应 Blender −Y）。
- 建筑中心 **y = −0.55**（即朝 +Y 方向前置 0.55 m，让前场更宽）。**这条以出货的 v5 blend、`gallery_layout.json` 与全部 `CAM_*` 为准**（2026-10-22 校正；此前写的“正面 −Y / 中心 +0.55”是方向反了）。
- 生成器接受 `hallY` / `frontSign` 参数以翻转朝向，默认值必须复刻上表，不要自行改符号。
- 底座：**16.0 × 16.0 m**（x ∈ [−8, 8]，y ∈ [−8, 8]），顶部平台面 **z = 0.0**；
  须弥座在 z ∈ [−0.65, 0]；底部木托架可到 z = −0.95。
- 楼层：一层地面 **z = 0.25**，二层楼板 **z = 3.60**，墙顶 **z = 6.55**。
- 檐口 **z = 6.15**（腰檐/主檐下皮），主屋脊 **z = 11.30**（这是 v5 现状，允许在 `wm_generate_roof` 参数里改，但默认值必须一致）。
- 重檐时上层主檐默认 **z ≈ 7.95**（v5 实测；可用 `mainEaveZ` 覆盖）。
- 建筑外皮：**8.4 (X) × 7.5 (Y)**，中心 y = **−0.55**。
- 一层净高 3.35，二层净高 2.95。
- 前场街道进深 ≥ 2.6 m；左右留 ≥ 1.5 m。

### 命名契约（Three.js 依赖，必须保留）

```
BASE_*   台基/铺装/台阶        WALL_*   墙体、勒脚
COLUMN_* 柱                    BEAM_*   梁、檩、椽、天花
FLOOR_01/FLOOR_02 楼板         STAIR_*  楼梯
RAIL_*   栏杆/挂落             ROOF_*   屋架、屋面基层
TILE_*   瓦垄/瓦当/屋脊        DOOR_* / WIND_*  门窗
LANTERN_* 灯笼                 PROP_*   街景道具（树、竹、灯、幡）
GALWALL_* 展墙                 SHOWCASE_* 展柜
FRAME_F1_001..007 / FRAME_F2_001..008  15 个画框锚点 empty（**禁止删除/改名/重建**）
CAM_*    相机锚点（导出 GLB 时保留，网页会剥掉）
```

每个由插件生成的物体写自定义属性：
`obj["wm_part"] = "roof"|"timber"|"interior"|"diorama"`，
`obj["wm_component"] = "roof_hipped"|...`，
`obj["wm_params"] = json 字符串`。
这样 `wm_generate_*` 只替换自己那一部分，**不重建整个场景**。

## 2. Job 协议（TypeScript → Blender）

Node 侧写 job JSON：

```json
{
  "task": "generate_roof",
  "jobId": "20261022-001234-generate_roof-ab12",
  "params": { "...": "见各 task" },
  "context": {
    "projectRoot": "D:\\wenmai-huazhang",
    "workDir": "D:\\wenmai-huazhang\\outputs\\wenmai-3d\\jobs\\<jobId>",
    "resultPath": "D:\\wenmai-huazhang\\outputs\\wenmai-3d\\jobs\\<jobId>\\result.json",
    "sceneDir": "D:\\wenmai-huazhang\\outputs\\wenmai-3d\\scene",
    "rendersDir": "D:\\wenmai-huazhang\\outputs\\wenmai-3d\\renders",
    "reportsDir": "D:\\wenmai-huazhang\\outputs\\wenmai-3d\\reports",
    "referencesDir": "D:\\wenmai-huazhang\\assets\\gallery3d\\references\\raw",
    "blenderExe": "D:\\Codex\\...\\blender.exe",
    "baseBlend": "…\\wenmai_gallery_v5.blend" | null,
    "outBlend": "…\\wenmai_gallery_v5_wm.blend"
  }
}
```

调用方式：

```
blender.exe -b [<baseBlend>] -noaudio --python <plugin>\python\wm_job.py -- <job.json>
```

`wm_job.py` 读取 job，`from wm_<module> import <fn>`，`result = fn(params, context)`，
把 `result` 写成 UTF-8 JSON 到 `context.resultPath`（**必须**成功也写、失败也写），
再 `sys.exit(0)`；异常时写 `{"ok": false, "error": {"message","traceback"}}` 并 `sys.exit(1)`。
Blender 的 stdout 只用于日志，Node 不解析。

统一返回结构（python 侧构造，字段缺失由 Node 补）：

```json
{
  "ok": true,
  "task": "generate_roof",
  "artifacts": [{"kind":"blend","path":"...","bytes":123}],
  "objects": [{"name":"ROOF_Main","part":"roof","verts":1234,"faces":567}],
  "metrics": {"walls":123,"faces":4567,"height":9.6,"spanX":14.1,"spanY":13.2},
  "checks": [{"id":"roof_has_eave","status":"pass|warn|fail","detail":"..."}],
  "warnings": ["..."],
  "notes": "human readable summary"
}
```

## 3. Python 模块分工

| 文件 | 负责人 | 由 `wm_job.py` 调用的函数 |
|---|---|---|
| `wm_job.py` | Lead | `main()` 调度器 |
| `wm_common.py` | Lead | 工具函数（只读使用，勿改） |
| `wm_mesh.py` | generator | 几何/材质辅助（可自由实现） |
| `wm_roof.py` | generator | `generate_roof(params, ctx)` |
| `wm_timber.py` | generator | `generate_timber(params, ctx)` |
| `wm_interior.py` | generator | `generate_interior(params, ctx)` |
| `wm_diorama.py` | generator | `generate_diorama(params, ctx)` |
| `wm_export.py` | generator | `export_glb(params, ctx)` |
| `wm_image.py` | vision | 图像 I/O（numpy，PNG 读写用 Blender 或纯 numpy+zlib） |
| `wm_analysis.py` | vision | `analyze_references(params, ctx)` |
| `wm_camera.py` | vision | `match_camera(params, ctx)`, `validate_multiview(params, ctx)` |
| `wm_capture.py` | vision | `capture_views(params, ctx)` |
| `wm_compare.py` | vision | `compare_reference(params, ctx)`, `propose_geometry_changes(params, ctx)` |
| `wm_inspect.py` | vision | `inspect_scene(params, ctx)`, `check_art_frames(params, ctx)`, `check_export(params, ctx)`, `performance_report(params, ctx)` |

`wm_common.py` 提供（generator/vision 直接 import）：
`load_job`, `finish(result)`, `ensure_dirs`, `open_scene(path_or_none)`, `reset_scene`,
`get_collection`, `mark_part`, `delete_part`, `save_blend`, `export_glb_scene`,
`material`, `bm_to_object`, `box`, `cylinder`, `scene_bounds`, `object_inventory`,
`check`, `now_id`, `safe_float`.

## 4. 工具参数契约（模型可见；raw JSON Schema，参数名即字段名）

所有路径参数都相对 `projectRoot` 或绝对路径，Node 侧校验必须落在项目根内。
带 `?` 的参数可省略，省略时使用括号里的默认值/回退；**只有 `?` 之外的参数才在 schema 里标 `required`**。

> 实现与本节如有出入，以本节更新为准（2026-10-22 校正）：
> - `blend` / `glb` 均为**可选**：省略时依次回退到 `outputs/wenmai-3d/scene/wenmai_scene.blend(.glb)`、v5 工程模型。
> - `wm_generate_interior` 用 `stairWidth` + `stairRisers` 描述楼梯（不再有 `stair` 对象）。
> - `wm_capture_views` 只有 `BLENDER_EEVEE` 一种引擎，故不再暴露 `engine`。
> - `wm_generate_diff_report` 输出目录参数名是 `outDir`（不是 `outPath`）。
> - `wm_propose_geometry_changes` 不需要 `parameterCatalog`（插件内置参数目录）。
> - `wm_performance_report` 的预算用 `triangleBudget` + `sizeBudgetMb`，不是 `budget` 对象。
> - `wm_export_glb` 的清单（bytes/meshes/triangles/materials/**textures 为数量**/animations）统一放在 `metrics` 里；
>   `artifacts[]` 只列 GLB/复制目标路径。
> - `wm_compare_reference` 的 `metrics.silhouetteIoU` 在“轮廓比较不适用”（室内/拼贴参考图）时为 **null**，
>   同时保留 `silhouetteIoUUnconditional` 作为不做适用性判断的原始值；`silhouetteApplicable` 明确说明原因。
> - `wm_validate_multiview` 的总体 `status` 允许 `not_checked`：当没有可用相机（未跑 `wm_match_camera`）时，
>   不谎报 pass/warn/fail。
> - `legacyReplace`（生成器参数，默认开）允许一次替换掉**未打 `wm_part` 标签的旧 v5 物体**：按
>   `wm_mesh.LEGACY_PREFIXES` 的前缀集（roof: `ROOF_/TILE_` + 檐上 `INT_ATTIC*/INT_ROOF_BOARD*/INT_BEAM_SEC*/INT_RAFTER*`；
>   interior: `INT_/RAIL2_/PLAQUE_`）。被替换清单必须出现在结果的 `metrics.legacyReplaced` 里，并在 `warnings` 中说明；
>   传 `legacyReplace:false` 可关闭。

### A. 重建（vision）

**`wm_analyze_references`**
```
images?: string[]            // 默认 references/raw/*.png
outDir?: string
```
→ `{ok, images:[{path,width,height,palette:[..],foregroundBox:{x,y,w,h},bands:{...},metrics}], measurementsPath, notes}`

**`wm_build_scene_spec`**
```
observations: object         // 模型视觉读图结果（组件、比例、置信度、矛盾）
measurementsPath?: string
outPath?: string
```
→ `{ok, specPath, spec:{...}, contradictions:[...], unknowns:[...], validation:{...}}`

**`wm_match_camera`**
```
image: string
correspondences: [{point3d:[x,y,z], pixel:[u,v]}]
imageSize?: [w,h]
init?: {yaw?, pitch?, distance?, lens?}
outPath?: string
```
→ `{ok, camera:{position,target,lens,sensor,fov,roll}, reprojectionError:{rmsPx,maxPx}, perPoint:[...], cameraPath}`

**`wm_validate_multiview`**
```
specPath?: string
views?: [{image, cameraPath?}]
```
→ `{ok, perView:[{image, reprojectionRmsPx, componentOffsetsPx:[..]}], contradictions:[..], status:'pass'|'warn'|'fail'}`

### B. 生成（generator）

**`wm_generate_roof`**
```
baseBlend?: string
outBlend?: string
style?: 'hip'|'xieshan'|'gable'|'double-eave'   // 默认 'hip'
footprintX?: number=8.4   footprintY?: number=7.5
eaveZ?: number=6.15        ridgeZ?: number=11.3
overhang?: number=1.55     cornerLift?: number=0.55
slopePower?: number=1.75   ridgeHalf?: number=1.35
tileRows?: number=28       tileCover?: number=1.35   // 每垄宽
tileSegments?: number=26   // 沿坡向分段
tileThickness?: number=0.045
ridgeOrnament?: boolean=true
detail?: 'low'|'medium'|'high'
```
→ `{ok, artifacts, objects, metrics:{tileCount, ridgeLen, eaveSpanX, eaveSpanY, height}, checks}`

**`wm_generate_timber`**：`baseBlend?, outBlend?, baysX=3, baysY=3, columnRadius=0.16, f1H=3.35, f2H=2.95, dougongLevels=2, rafterSpacing=0.32, detail`

**`wm_generate_interior`**：`baseBlend?, outBlend?, voidX=5.4, voidY=4.6, corridorWidth=1.9, railingHeight=1.05, stair:{x,y,width,risers}, displayWalls:boolean=true, ceilingStyle:'coffered'|'beams', lanterns:boolean=true, detail`
（**15 个 FRAME 锚点必须原样保留**；若 base 中不存在则按 `gallery_layout.json` 重建同名 empty 并标记 `wm_part='interior'`，数量必须 15）

**`wm_generate_diorama`**：`baseBlend?, outBlend?, baseSize=16, plinthHeight=0.65, frieze=true, medallion=true, paving=true, props:{trees,bamboo,planters,lanterns,stoneLamps,banners}, detail`

**`wm_export_glb`**：`blend: string, out?: string, copyTo?: string, draco?: false, yUp?: true`
→ `{ok, glbPath, bytes, triangles, materials, meshes, textures:[{name,width,height}], copiedTo?, checks}`

### C. 视觉对照（vision）

**`wm_capture_views`**：`blend, views?: string[]('front34','front','left','right','back','top','base_low','floor1','floor2','ceiling','eave','corner'), camerasPath?, width=1200, height=900, samples=48, engine?: 'BLENDER_EEVEE'`
→ `{ok, shots:[{view,path,width,height,camera}], camerasPath, metrics}`

**`wm_compare_reference`**：`reference, render, outDir?, align?: 'auto'|'none', cameraPath?`
→ `{ok, sideBySide, overlay, contour, metrics:{silhouetteIoU, centroidOffset, bandEdgeErrors, regionColorDelta, roughness}, regions:[{name,refBox,renderBox,delta}], checks}`

**`wm_generate_diff_report`**：`comparisons: object[]|string[], outPath?, title?`
→ `{ok, reportPath, topDifferences:[{rank,region,severity,evidence}], markdown}`

**`wm_propose_geometry_changes`**：`reportPath|comparisonPath, specPath?, parameterCatalog?: object`
→ `{ok, changes:[{priority,component,object,reason,parameter,from,to,expectedEffect}], parameterCatalog, reportPath}`

### D. 审查（vision，只读）

**`wm_inspect_scene`**：`blend, checks?: string[]`
→ `{ok, summary:{objects,meshes,triangles,materials,images}, checks:[{id,status:'pass'|'warn'|'fail'|'manual'|'not_checked',detail,objects?}], bounds, warnings}`

**`wm_check_art_frames`**：`blend, expected=15, layoutPath?`
→ `{ok, found:number, frames:[{id,position,rotation,wallId,status}], missing:[], duplicated:[], checks}`

**`wm_check_export`**：`glb, profile?: 'web'|'general'`
→ `{ok, bytes, meshes, triangles, materials, textures, animations, checks:[...], warnings}`

**`wm_performance_report`**：`blend?, glb?, budget?: {mb?: 16, triangles?: 350000}`
→ `{ok, reportPath, budget:{used, limit, status}, hotspots:[...], recommendations:[...]}`

## 5. 验证要求（每个 task 都必须给出可核实证据）

- 生成类任务：必须真实调用 Blender（不能只写脚本），落盘 `.blend` 并在 result 里列出 objects/metrics/checks。
- 渲染类任务：必须真实渲染 PNG 并返回绝对路径、尺寸；不得复用旧图冒充。
- 对照类任务：必须输出 side-by-side、overlay、contour 三张图 + 数值指标；禁止编造“还原度 98%”。
- 审查类任务：`status` 必须区分 `pass` / `warn` / `fail` / `manual` / `not_checked`；未检查项禁止写成 pass。

## 6. 失败与取消

- Node 侧 `exec.signal` 触发时立即杀掉 Blender 进程树，返回 `ABORTED`。
- Blender 默认超时 **30 分钟（1_800_000 ms）**，由插件配置 `timeoutMs` 控制；超时 `TOOL_TIMEOUT`。
- Blender 退出码非 0 且 result 缺失 → 结构化错误（含 stderr 尾部 40 行，写入 reports 日志）。

## 7. 只改自己那一部分

`wm_generate_*` 收到 `baseBlend` 时：
1. 打开 baseBlend；
2. 删除所有 `obj.get("wm_part") == <本模块 part>` 的物体；
   **另外**（`legacyReplace` 默认开）按 `LEGACY_PREFIXES` 删除属于同一建筑部位的旧 v5 未打标签物体——
   这些物体存在于出货模型里，没有标签就无法被第 2 步看见，不删就会叠在旧模型上面；
3. 生成新物体并打标记；被删清单写进 `metrics.legacyReplaced` 与 `warnings`；
4. 保存到 `outBlend`（默认 `<sceneDir>/wenmai_scene.blend`，永不覆盖 baseBlend，除非显式 `overwrite=true`）。
