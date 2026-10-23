# 验收证据 · wenmai-3d-reconstruction（DSH 插件）

> 本文只记录**真实执行过**的命令、时间戳、退出码、计数和产物路径。
> 未执行的项一律写 `NOT RUN`；工具自己报出的 `fail` / `warn` 原样列出，不折算成通过。
> 所有测试产物在 `D:\wenmai-huazhang\outputs\wenmai-3d\tests\`（下文简称 `outputs\tests`）。
> 撰写人：qa-harness（测试与验收负责人）。

## 0. 环境事实（实测）

| 项 | 值 |
|---|---|
| 插件目录 | `D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction` |
| DSH 版本 | `dsh --version` → **0.2.1-rc.2**（`ELECTRON_RUN_AS_NODE=1`） |
| GUI | `D:\deepseek\DeepSeek Harness.exe` |
| CLI | `D:\deepseek\resources\runtime\cli\bin\dsh.cmd` |
| Node（harness） | v24.15.0（`node --version`） |
| 项目根（唯一授权目录） | `D:\wenmai-huazhang` |
| 十张参考图 | `assets\gallery3d\references\raw\*.png`（1448×1086，实测 10 张） |
| Blender | `D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe` |

## 1. 结论速览

| 检查 | 命令 | 结果 | 退出码 | 证据 |
|---|---|---|---|---|
| 单元（纯函数） | `node tests/run-unit.mjs` | **108 pass / 0 fail / 0 warn / 0 not ready** | 0 | `outputs\tests\unit-20261022-014401.json` |
| 注册（17 工具 + schema） | `node tests/run-registration.mjs --strict-contract` | **171 pass / 0 fail / 0 warn** | 0 | `tools\...\tests\registered-tools.json`、`registration-report.md` |
| 端到端（18 步，真实 Blender） | `node tests/run-e2e.mjs` | **18 pass / 0 fail / 0 blocked / 0 not ready / 0 skipped** | 0 | `outputs\tests\e2e-20261022-014356.{json,md}` |
| 过滤器 | `node tests/run-e2e.mjs --only=wm_build_scene_spec` | 1 pass / 17 skipped | 0 | `outputs\tests\e2e-20261022-014220.json` |
| 过滤器 | `node tests/run-e2e.mjs --skip=wm_analyze_references,wm_capture_views` | 13 pass / 3 blocked（依赖被跳过）/ 2 skipped | 0 | `outputs\tests\e2e-20261022-014226.json` |
| 隔离 profile 的 bundle 机制 | `powershell -File scripts\verify-bundle.ps1 -DshHome outputs\wenmai-3d\tests\dsh-home` | **PASS（11/11 检查，含反向对照）** | 0 | `outputs\tests\bundle-verify-20261022-012629.{json,md}`、`dump-config-wmtest-*.yml` |
| 前端回归基线（只读） | `npm run lint` / `npm test` / `node node_modules/vite/bin/vite.js build --outDir .tmp-qa-dist` | lint 0；**44/44 测试通过**；build 成功（2852 模块，13.68 s） | 0 / 0 / 0 | `outputs\tests\frontend-baseline.log`、`frontend-baseline-build.log` |

**总判定：工具层验收通过（17/17 工具注册 + 执行 + 结果 ok + 37/37 产物落盘校验）。**
但本文件第 6、7 节列出的 7 条工具自报 `fail`/`warn` 与 4 条契约漂移**尚未关闭**，它们不是“通过”。

## 2. 工具×结果矩阵（来自 `e2e-20261022-014356.json`）

| # | 工具 | 已注册 | 已执行 | 结果 ok | 产物校验 | 判定 |
|---|---|---|---|---|---|---|
| 1 | `wm_analyze_references` | 是 | 是 | 是 | 12/12 | PASS |
| 2 | `wm_build_scene_spec` | 是 | 是 | 是 | 2/2 | PASS |
| 3 | `wm_match_camera` | 是 | 是 | 是 | 1/1 | PASS |
| 4 | `wm_validate_multiview` | 是 | 是 | 是 | 1/1 | PASS（工具状态 `not_checked`，见 §6） |
| 5 | `wm_generate_roof` | 是 | 是 | 是 | 1/1 | PASS |
| 6 | `wm_generate_timber` | 是 | 是 | 是 | 1/1 | PASS |
| 7 | `wm_generate_interior` | 是 | 是 | 是 | 1/1 | PASS（§7 越界删除告警，见 §7） |
| 8 | `wm_generate_diorama` | 是 | 是 | 是 | 1/1 | PASS |
| 9 | `wm_export_glb` | 是 | 是（2 次） | 是 | 2/2 | PASS（返回结构漂移告警，见 §7） |
| 10 | `wm_capture_views` | 是 | 是 | 是 | 4/4 | PASS |
| 11 | `wm_compare_reference` | 是 | 是 | 是 | 5/5 | PASS（IoU 字段名漂移告警） |
| 12 | `wm_generate_diff_report` | 是 | 是 | 是 | 2/2 | PASS |
| 13 | `wm_propose_geometry_changes` | 是 | 是 | 是 | 2/2 | PASS |
| 14 | `wm_inspect_scene` | 是 | 是 | 是 | 0/0（只读） | PASS（内部 2 项 fail，见 §6） |
| 15 | `wm_check_art_frames` | 是 | 是 | 是 | 0/0（只读） | PASS（内部 1 项 fail，见 §6） |
| 16 | `wm_check_export` | 是 | 是 | 是 | 1/1 | PASS |
| 17 | `wm_performance_report` | 是 | 是 | 是 | 1/1 | PASS |

- 产物校验总数：**37/37 通过**（存在、`size>0`、PNG/JPEG 头可解析出正尺寸、路径在项目根内）。
- 单位换算的 `WM_PROBE`（harness 自带 Blender 探针）另外验证了 `.blend` 内部的真实组成，见 §5。

## 3. 端到端依赖链与关键指标（`node tests/run-e2e.mjs`，2026-10-22T01:43:56 → 01:44:53，57.7 s）

| 步 | 工具 | 耗时 | 关键指标（工具返回） |
|---|---|---|---|
| 1 | `wm_analyze_references` | 19.6 s | 10 张图全部量出；`bandSourceDetected=10`；检查 8 pass / 1 warn / 1 not_checked |
| 2 | `wm_build_scene_spec` | 0.0 s | spec 15,806 B；`measurements_linked=pass` |
| 3 | `wm_generate_roof` | 1.9 s | `tileCount=362`、`courseCount=112`、`wadangCount=112`、`triangles=56,252`、objects=12、`height=5.75` |
| 4 | `wm_export_glb`（腰檐阶段） | 4.6 s | 6,638,868 B、meshes 1,163、triangles 132,036、materials 72 |
| 5 | `wm_capture_views` | 5.8 s | 3 张 1200×900 PNG（EEVEE，共 4.39 s） |
| 6 | `wm_compare_reference` | 5.1 s | side-by-side 2900×1086、overlay/contour 1448×1086、`silhouetteIoUUnconditional=0.5443`、居中偏移 2 维 |
| 7 | `wm_generate_diff_report` | 0.0 s | JSON 9,432 B + Markdown 4,901 B |
| 8 | `wm_propose_geometry_changes` | 0.9 s | changes=1（参数目录内置） |
| 9 | `wm_generate_timber` | 1.3 s | columns=16、rafters=37、purlins=9、bracketLevels=2 |
| 10 | `wm_generate_interior` | 1.6 s | `frameAnchors=15`、`adopted=15`、`created=0` |
| 11 | `wm_generate_diorama` | 1.2 s | baseSize=16、plinthHeight=0.65、steps=4、objects=13 |
| 12 | `wm_export_glb`（最终） | 3.1 s | 6,824,312 B、meshes 551、triangles 146,690、materials 72 |
| 13 | `wm_inspect_scene` | 1.6 s | summary：objects 602 / meshes 551 / materials 72 / empties 27 / cameras 13 / lights 11 / images 0 |
| 14 | `wm_check_art_frames` | 1.1 s | found 15/15、missing 0、`maxPositionErrorM=0.0`、buried 15 |
| 15 | `wm_check_export` | 0.9 s | bytes 与磁盘一致、6.508 MB、meshes 551、triangles 146,690、animations 0 |
| 16 | `wm_performance_report` | 1.1 s | triangles 146,690、meshes 551、materials 72 |
| 17 | `wm_match_camera` | 0.9 s | 14 点、**rmsPx=0.000322**、maxPx=0.000578、lens≈35.0、fov 54.43 |
| 18 | `wm_validate_multiview` | 0.9 s | views=1、contradictions=0、status=`not_checked` |

### 3.1 关键产物（全部真实落盘）

| 产物 | 大小 | 尺寸 |
|---|---|---|
| `outputs\tests\analysis\measurements.json` | 166,531 B | — |
| `outputs\tests\analysis\contact_sheet.png` | 2,102,972 B | 1848×661 |
| `outputs\tests\specs\scene_spec.json` | 15,806 B | — |
| `outputs\tests\scene\step1_roof.blend` | 1,640,017 B | — |
| `outputs\tests\renders\capture\*.png`（3 张） | 1,028,779–1,128,370 B | 1200×900 ×3 |
| `outputs\tests\comparisons\side_by_side*.png` | 4,482,188 B | 2900×1086 |
| `outputs\tests\comparisons\overlay*.png` / `contour*.png` | 2,518,460 / 24,509 B | 1448×1086 |
| `outputs\tests\scene\step2_timber.blend` / `step3_interior.blend` / `step4_diorama.blend` | 1,757,335 / 1,579,268 / 1,801,675 B | — |
| `outputs\tests\scene\roof.glb` / `gallery_final.glb` | 6,638,868 / 6,824,312 B | — |
| `outputs\tests\specs\camera_fixture.json` | 4,463 B | — |
| `outputs\tests\ewe2e-raw\<stamp>\*.json` | 每步原始返回 | — |

> 逐条产物清单（37 条，含 label/bytes/width/height/inside-root/ok）见 `e2e-20261022-014356.json` 的 `steps[].artifacts` 与 `.md` 的产物表。

## 4. 隔离 profile 的 bundle 机制验证（离线可复现）

命令（**未触碰 `web`**；用独立 `DSH_HOME` 保证零污染）：

```powershell
powershell -File scripts\verify-bundle.ps1 -DshHome D:\wenmai-huazhang\outputs\wenmai-3d\tests\dsh-home
```

时间 2026-10-22T01:26:29+08:00，退出码 **0**，11/11 检查 pass：

1. `install-profile.ps1` exit 0；依赖 spec `link:D:/wenmai-huazhang/tools/dsh-plugins/wenmai-3d-reconstruction`，`node_modules` 链接存在；
2. profile manifest 的 `dsh.profile.bundles` 含 `wenmai-3d-reconstruction`（before `[]` → after `[@deepseek-ai/dsh-base, wenmai-3d-reconstruction]`）；
3. `dsh --profile wmtest --dump-config` exit 0，369 行，无错误行；
4. 组合出的 YAML 中插件行**恰好出现 1 次**：

```yaml
# == wenmai-3d-reconstruction
- id: wenmai-3d-reconstruction
  name: wenmai-3d-reconstruction
  config:
    projectRoot: D:\wenmai-huazhang
    blenderExe: D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe
    timeoutMs: 1800000
    allowProjectWrites: true
```

5. **反向对照**：`uninstall-profile.ps1`（exit 0）后再 `--dump-config`（exit 0）→ 插件行**消失**，证明该行确实来自 bundle patch，而不是 profile 里的残留编辑；
6. 卸载会清掉 pnpm 遗留的 `node_modules` 链接（仅删除 reparse point，不触碰插件源码）。

原始证据：`outputs\tests\bundle-verify-20261022-012629.json` / `.md`、`dump-config-wmtest-20261022-012629.yml`（安装后）、`dump-config-wmtest-after-uninstall-20261022-012629.yml`。

### 4.1 真实宿主挂载（live mount）

`outputs\wenmai-3d\logs\activation-log.jsonl`（append-only，实测 4 行）前两行为真实 GUI 宿主进程：

| 行 | 时间 (UTC) | pid | ppid | execPath | tools |
|---|---|---|---|---|---|
| 1 | 2026-10-21T17:30:27.558Z | 43784 | 5076 | `D:\deepseek\DeepSeek Harness.exe` | 17 |
| 2 | 2026-10-21T17:34:33.902Z | 43784 | 5076 | `D:\deepseek\DeepSeek Harness.exe` | 17 |

第 3、4 行是 harness 自身（`node.exe` + `tests/run-*.mjs`），不是宿主挂载，不算作 live 证据。

**诚实说明**：`logs\activation.json`（单文件“最近一次挂载”）在任何一次挂载后都会被覆盖，因此它当前记录的是 harness 运行；durable 证据只有上面的 `activation-log.jsonl`。为避免误清，harness 在每次挂载前会把既有 `activation.json` 另存为 `outputs\tests\activation-preserved-*.json`。

**桌面 profile 现状（保持 Lead 原样）**：`link:` 依赖 + `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 中的 `insert` 行；**故意不写入 bundles**，两条激活路径互斥（同时存在会重复挂载）。`dsh --profile desktop --dump-config` 在 CLI 下会被宿主拒绝（`profile "desktop" is managed exclusively by the Electron application`），所以桌面行只能在宿主内证明。

## 5. Harness 自带 Blender 探针（不依赖工具自述）

`tests/lib/probe-blend.py` / `probe-diff.py` 直接打开 `.blend` 统计真实组成，`run-e2e.mjs` 在 timber / interior / diorama 三步后调用：

| 阶段 | objects | meshes | 各部分计数 | FRAME 锚点 |
|---|---|---|---|---|
| `step1_roof.blend` | 1160 meshes | — | roof 12（ROOF_ 7 / TILE_ 4）、untagged 1148 | 15 |
| `step2_timber.blend` | — | — | roof 12、timber 4、untagged 1148 | 15 |
| `step3_interior.blend` | — | — | interior 73、roof 12、timber 4、untagged **449** | 15（15 个 ID 全部命中） |
| `step4_diorama.blend`（最终） | 602 objects | **551** | diorama 13、interior 73、roof 12、timber 4、untagged 449 | 15 |

- 最终 `.blend` 实测 146,690 三角面、72 个材质；最终 GLB 6,824,312 B 与 `wm_check_export` 报告一致。
- 上述“untagged 由 1148 → 449”即 §7 所列的越界删除告警来源。

## 6. 工具自报的 `fail` / `warn`（未关闭，原样记录）

以下来自 `e2e-20261022-014356` 第 13、14 步的工具返回值，**不是** harness 的判定：

| 来源 | 状态 | 检查 id | 内容（截断） |
|---|---|---|---|
| `wm_inspect_scene` | **fail** | `flipped_normals` | 16,420 个封闭网格采样面中 2,798 个（17.04%）绕序内向 |
| `wm_inspect_scene` | **fail** | `art_frames_placement` | 15/15 画框锚点位于墙体内，0 个在墙外表面之前 |
| `wm_inspect_scene` | warn | `bounds_vs_plinth` | Y 方向 −8.00..9.43 超出 ±8.0 |
| `wm_inspect_scene` | warn | `floating_tiles` | 20 个瓦件对 49 个屋面，3 个距离 > 0.35 m |
| `wm_inspect_scene` | warn | `stair_continuity` | 2 段楼梯 z 0.24→6.27，最大相邻缺口 −3.405 m，二层楼板 z=3.60 未在 0.2 m 内接上 |
| `wm_inspect_scene` | warn | `group_intersections` | 40 组测试中 3 组 BVH 三角面真实相交 |
| `wm_check_art_frames` | **fail** | `frames_not_buried` | 15 个锚点全部埋在 `GALWALL_*_Panel` 板内（`outwardClear=true`、`frontBlockedBy=[]`） |

同一步中 `wm_check_art_frames` 的 7 项 pass 包括：15/15 存在、ID 齐全、无重名、仍是可编辑 EMPTY、位置与 `gallery_layout.json` 偏差 0.0 m（RMS 0.0）、轴映射最佳拟合 RMS 0.0。
`wm_inspect_scene` 另有 `manual`（Three.js 运行时只能在浏览器验证）与 `not_checked`（本任务不做视觉保真度声明）各 1 项。

## 7. 契约漂移与待裁决项（Lead 已裁决一部分）

| # | 项 | 实测 | 状态 |
|---|---|---|---|
| 1 | §6 默认超时 | 代码 1_800_000 ms = 30 min | **已裁决**：Lead 已把 §6 改为 30 分钟，harness 与合同一致（`run-unit` 断言两者同时为 1_800_000） |
| 2 | §4 参数名 11 处（`blend`/`glb` 可选、`stair`→`stairWidth`+`stairRisers`、`engine` 移除、`outPath`→`outDir`、`parameterCatalog` 移除、`budget`→`triangleBudget`+`sizeBudgetMb`） | 与 §4 校正块一致 | **已裁决**，`--strict-contract` 171/171 通过 |
| 3 | `wm_export_glb` 返回结构 | `bytes/meshes/triangles/materials` 嵌在 `metrics` 下；`textures` 是数字不是数组 | **待裁决**（`--strict-contract` 不覆盖返回结构） |
| 4 | `wm_compare_reference` IoU 字段 | `silhouetteIoU=null`，`silhouetteIoUUnconditional=0.5443` | **待裁决** |
| 5 | `wm_validate_multiview.status` | 返回 `not_checked`，§4 只列 `pass\|warn\|fail` | **待裁决**（§5 的检查词汇已含 `not_checked`） |
| 6 | §7“只改自己那一部分” | `wm_generate_interior` 删除 **702 个无 `wm_part` 的旧 v5 物体**：`INT_` 594、`RAIL2_` 102、`PLAQUE_` 6 | **待裁决**（有意的 v5 内饰替换？还是越界删除？） |

> 第 3–6 项在运行中被记为 **warning**（不使端到端失败），因为它们是契约/设计选择，需要合同所有者拍板。一旦裁决，harness 可将对应项收紧为 fail。

## 8. 未覆盖 / 未运行（NOT RUN）

| 项 | 原因 |
|---|---|
| GLB 在 Three.js 中真实加载、着色器编译、交互 | 只能在浏览器断言；`wm_inspect_scene` 自己标为 `manual`，harness 未运行浏览器验证 |
| 与**真实**参考图的像素级相机标定 | 十张参考图是风格化插画，没有可信的真实像素同名点；`tests/fixtures/camera-correspondences.json` 是**合成但精确**的针孔相机基准（14 点，rms ≈ 0.0003 px 说明解算正确），不冒充从照片量测 |
| 视觉保真度评分（“还原度 x%”） | 插件与 harness 都不产生该数字；仅有几何/色彩测量指标（IoU、居中偏移、色差等） |
| 画框内作品是否可读、材质观感、灯光效果 | 需要人/视觉审阅（`wm_check_art_frames` 的 `artwork_content` 标为 `manual`） |
| 前端回归在模型替换后的对比 | 本文只记录替换**前**基线（§1 最后一行），对比由 Lead 执行 |
| `desktop` profile 的组合树 | CLI 被宿主拒绝，无法从命令行 dump；只能凭 `activation-log.jsonl` 的宿主行 |

## 9. 如何复现

```powershell
cd D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction

# 1) 纯函数单元（无需 Blender）：108 项
node tests/run-unit.mjs

# 2) 注册与 schema（需要已构建的 lib/）：171 项，--strict-contract 按合同字面核对
node tests/run-registration.mjs --strict-contract

# 3) 端到端（真实 Blender，约 1 分钟）：18 步
node tests/run-e2e.mjs
node tests/run-e2e.mjs --only=wm_generate_roof
node tests/run-e2e.mjs --skip=wm_capture_views
node tests/run-e2e.mjs --list

# 4) 隔离 profile 的 bundle 机制证明（不碰 web/desktop）
powershell -File scripts\verify-bundle.ps1 -DshHome D:\wenmai-huazhang\outputs\wenmai-3d\tests\dsh-home

# 5) 安装 / 卸载（默认 wmtest；web 需显式 -AllowLive；desktop 建议 -SkipBundleAppend）
powershell -File scripts\install-profile.ps1 -Profile wmtest
powershell -File scripts\uninstall-profile.ps1 -Profile wmtest -Purge
powershell -File scripts\install-profile.ps1 -Profile desktop -SkipBundleAppend   # 仅备份 + 依赖，不动 bundles
```

退出码约定：harness 脚本 `0` 全过、`1` 有失败、`2` 无可验证（`lib/` 未构建等）；PowerShell 脚本 `0` 通过、`1` 失败、`2` NOT READY、`3` 前置条件不满足。

> Node harness 只需 Node ≥22（实测 v24.15.0）。PowerShell 脚本已按 **Windows PowerShell 5.1**（本机 `$PSVersionTable.PSVersion = 5.1.26100.9711`）验证，无需 pwsh 7；profile 的 `package.json` 一律以**无 BOM** UTF-8 写回，保证 `JSON.parse` 可读。

## 10. 证据索引（`D:\wenmai-huazhang\outputs\wenmai-3d\tests\`）

| 文件 | 内容 |
|---|---|
| `e2e-20261022-014356.json` / `.md` | 本次端到端全量证据（18 步、37 产物、警告清单、每步 args/指标/断言） |
| `e2e-console-last.log` | 端到端控制台原文 |
| `e2e-20261022-014220.*` / `e2e-20261022-014226.*` | `--only` / `--skip` 过滤器运行的证据 |
| `unit-20261022-014401.json` | 单元检查明细（含 NOT READY 项为空） |
| `bundle-verify-20261022-012629.json` / `.md` | 隔离 profile 的 11 项检查与插件行摘录 |
| `dump-config-wmtest-*.yml` | 组合后的依赖树（安装后 / 卸载后） |
| `activation-log.jsonl`、`activation-preserved-*.json` | 宿主挂载历史与被 harness 保护的旧记录 |
| `frontend-baseline.log`、`frontend-baseline-build.log` | 前端回归基线（lint / 44 测试 / vite build） |
| `e2e-raw\<stamp>\*.json` | 每一步的原始工具返回（含失败详情） |
| `install-logs\*.log` | `dsh plugin add/remove` 的 pnpm 原文 |
