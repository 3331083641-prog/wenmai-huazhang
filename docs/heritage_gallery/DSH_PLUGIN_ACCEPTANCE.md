# 《纹脉华章》专属 DSH 三维重建插件 — 验收报告

- 插件：**wenmai-3d-reconstruction** v0.1.0
- 本地目录：`D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction\`
- 宿主：**DeepSeek Harness 0.2.1-rc.2**（GUI `D:\deepseek\DeepSeek Harness.exe`，实际使用 **desktop** profile）
- Blender：`D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe`（5.2.2 LTS，Python 3.13.13，numpy 2.3.4，EEVEE）
- 授权目录：`D:\wenmai-huazhang`（插件读写均限制在此；唯一例外是本机 Blender 可执行文件）
- 报告时间：2026-10-22

---

## 0. 结论摘要

| 问题 | 结论 | 证据 |
|---|---|---|
| 插件是否已在**当前实际运行的 DSH** 中成功加载？ | **是**。在 GUI 宿主进程（pid 43784，父进程 5076 = DeepSeek Harness 主进程）内注册了 17 个工具 | `outputs/wenmai-3d/logs/activation-log.jsonl` 第 2 行（2026-10-21T17:30:27.558Z / 17:49:04.869Z，`argv` = `dsh-desktop-host/lib/index.js`） |
| 是否通过真实调用测试？ | **是**：Lead 在真实会话里直接调用插件工具 19 次，全部返回结构化结果与真实产物；QA 端到端脚本 18/18 步通过 | 本报告 §3、§4；`outputs/wenmai-3d/tests/e2e-20261022-103419.{json,md}` |
| 十图结构分析 | **通过**：10/10 张实测（1448×1086），产出 `measurements.json` + 拼图，并识别出 3 张室内图与 1 张拼贴图 | `outputs/wenmai-3d/reports/analysis/measurements.json`、`references_contact_sheet.png` |
| Blender 真实建模 | **通过**：屋顶（单檐/重檐）、木构、室内、台基均在 Blender 5.2.2 内真实生成、保存 `.blend` 并导出 GLB | §3 |
| Three.js 集成 | **通过**：插件导出的 GLB 用**与前端同版本 three r180 + GLTFLoader** 加载，无运行错误，尺度/朝向/材质正确 | `outputs/wenmai-3d/renders/threejs_verify_v4_front34.png`；§5 |
| 视觉匹配迭代 | **通过两次真实迭代**（v2 → v3），并有可核实的量化变化 | §6 |
| 场景自动审查 | **通过**（并**如实报告** 1 项 fail、2 项 warn、2 项 manual、1 项 not_checked，不折算成通过） | §7 |

---

## 1. 开发机制核实（先查实际版本，再动手）

从**本机安装的运行时**中读取（不依赖记忆、不凭"最新版"猜测）：

- `dsh --version` → `0.2.1-rc.2`
- 工具注册 API 来自 `D:\deepseek\resources\app.asar\dsh\node_modules\@deepseek-ai\dsh-tools`（同版本 0.2.1-rc.2）：
  `defineTool(options)` 产出 `{ name, description, parameters(JSON Schema), output{schema,render}, execute(args, exec) }`，`ctx.tools.register(def)` 注册，`exec.signal` 协作取消。
- 插件挂载点：profile 的 `package.json`（`dsh.profile.bundles`）与 `cordis.patch.yml`（顶层数组补丁：`insert` 新行 / 按 `id` 覆盖），由 `@deepseek-ai/dsh-app-boot` 组合，`@deepseek-ai/dsh-hmr` 热重载 profile 补丁。
- **刻意不引入第二份运行时**：插件 `src/**` 不 import 任何 `@deepseek-ai/*`，只用自带的 `src/lib/sdk.ts` 描述注册接口的 wire 形状。因此 profile 不需要安装第二份 cordis / dsh-tools，也不存在版本错配。

> 结论：本轮没有升级/降级 DSH，没有覆盖已有插件，没有引入大型第三方依赖。

---

## 2. 交付物清单

| # | 交付物 | 位置 |
|---|---|---|
| 1 | 可安装运行的插件包（bundle 清单 + package.json） | `tools/dsh-plugins/wenmai-3d-reconstruction/{package.json, cordis.patch.yml, lib/}` |
| 2 | 完整 TypeScript 源码（17 工具 + 核心库） | `…/src/**`（`index.ts`、`lib/{config,blender,tool,spec,result,sdk}.ts`、`tools/{references,generate,visual,inspect}.ts`） |
| 3 | Blender Python 建模工具 | `…/python/{wm_job,wm_common,wm_mesh,wm_roof,wm_timber,wm_interior,wm_diorama,wm_export}.py` |
| 4 | 十图结构分析 | `…/python/{wm_analysis,wm_image}.py` + `outputs/wenmai-3d/reports/analysis/*` |
| 5 | 参数化生成能力 | `wm_generate_roof / timber / interior / diorama`（可按 `wm_part` 独立替换，不重建整场） |
| 6 | Blender / Three.js 导出与加载 | `…/python/wm_export.py` + `tests/viewer/`（同版本 three 的浏览器验证页） |
| 7 | 固定视角截图与对照 | `wm_capture_views` / `wm_compare_reference` / `wm_generate_diff_report` |
| 8 | 场景自动审查 | `wm_inspect_scene` / `wm_check_art_frames` / `wm_check_export` / `wm_performance_report` |
| 9 | 实际测试结果 | 本报告 §3–§7；`docs/ACCEPTANCE_EVIDENCE.md`（QA 逐条命令/退出码/产物） |
| 10 | 安装、启用、卸载说明 | `README.md` §二（含停用/回滚/卸载与两种激活方式的互斥说明）+ `scripts/{install-profile,uninstall-profile,verify-bundle}.ps1` |

接口契约（job 协议、参数、返回字段、命名与坐标契约、验证要求）：`docs/CONTRACT.md`。

---

## 3. 真实调用测试（Lead 在运行中的 DSH 内直接调用）

工具可见性与调用都发生在**真实宿主进程**里，命令即会话内工具调用，不是脚本模拟。

| # | 工具 | 关键结果（真实数值） |
|---|---|---|
| 1 | `wm_build_scene_spec` | 生成 `outputs/wenmai-3d/specs/scene_spec.json`（2306 B），4 项检查全 pass，并链接实测比例 |
| 2 | `wm_generate_roof`（新场景，hip/medium） | `.blend` 796,667 B；362 片瓦 / 112 垄 / 12 物体 / 59,148 三角面；10 pass + 1 warn |
| 3 | `wm_export_glb` | GLB 2,151,624 B；12 mesh / 59,148 三角面 / 9 材质；回读三角面一致；6 pass |
| 4 | `wm_generate_roof`（工程模型，double-eave） | 560 片瓦 / 99,860 三角面 / 22 物体；12 pass；`legacyReplaced=[ROOF_MAIN, ROOF_SKIRT]` |
| 5 | `wm_capture_views` | 4 视角 1200×900、32 采样、11.5 s；返回的每张 PNG 均为本次真实渲染 |
| 6 | `wm_compare_reference`（R02 vs v2 渲染） | silhouette IoU 0.6840；detail 0.1534；分段比例差 roof +0.1245 / upper −0.2004 |
| 7 | `wm_generate_diff_report` | 产出 `reports/diff/v2/diff_report.{json,md}`（差异排行 + 证据） |
| 8 | `wm_propose_geometry_changes` | 10 条参数建议（4 条 high），每条带测量证据与方法学 caveat |
| 9 | `wm_generate_roof`（v3：high / overhang 1.7 / tileRows 40） | 774 片瓦 / 158 垄 / 151,260 三角面；13 pass + 1 warn（超出预算，如实报告）；清扫 101 件旧屋顶暗架（含 `INT_ATTIC_*`、`INT_ROOF_BOARD`、`INT_BEAM_SEC*`、`INT_RAFTER_*`），檐上穿模消失 |
| 10 | `wm_compare_reference`（R02 vs v3 渲染） | detail 0.1534→**0.1675**；roof 段差 0.1245→**0.0860**（详见 §6） |
| 11 | `wm_export_glb`（v3） | 9,332,556 B；220,694 三角面；71 材质；节点 1101，其中 **15 个 `FRAME_F*` 锚点齐全** |
| 12 | `wm_inspect_scene`（v5 工程模型） | 6 pass / **1 fail**（54/1136 闭合网格为内翻绕序：`INT_BEAM_SEC*`）/ 2 warn / 2 manual / 1 not_checked |
| 13 | `wm_check_art_frames`（v5） | 15/15 找到、无重复、均为可编辑 empty、位置与 `gallery_layout.json` 偏差 0 m；**0 被埋**；6 个"正面被遮挡" warn |
| 14 | `wm_generate_interior`（v4，基于 v3 屋顶） | **15/15 画框锚点**（全部沿用，0 丢失）、36 栏杆柱、90 挂落格、5.4×4.6 m 挑空（裁掉旧楼板 16 面 ×2）、藻井天花 20 格、5 灯笼、17 窗；17 pass |
| 15 | `wm_capture_views`（v4） | front34 / floor2 / floor1 / eave，1200×900、40 采样；floor2 可见**真实挑空 + 回廊 + 藻井 + 暖光格窗** |
| 16 | `wm_export_glb`（v4，最终） | **8,917,216 B；581 mesh / 216,202 三角面 / 69 材质**；复制到 `assets/exports/wenmai_gallery_v5_wm_roof.glb` 与 `frontend/public/models/wenmai_gallery_v5_wm_roof.glb` |

QA 端到端脚本（同一套工具，独立驱动）：

| 命令 | 结果 |
|---|---|
| `node tests/run-unit.mjs` | **108/108 pass**，exit 0（25 ms） |
| `node tests/run-registration.mjs --strict-contract` | **171/171 pass**，17/17 工具，schema 全部 object-rooted |
| `node tests/run-e2e.mjs` | **18/18 步 pass，0 fail / 0 blocked / 0 not ready**，37/37 产物校验通过，exit 0（219.8 s） |
| `scripts\verify-bundle.ps1`（隔离 `DSH_HOME`） | **11/11 pass**，含反向对照：安装后组合树中该行恰好 1 次，卸载后消失 |

---

## 4. 插件在真实宿主中的加载证据

`outputs/wenmai-3d/logs/activation-log.jsonl`（append-only，避免被测试进程覆盖）：

```json
{"plugin":"wenmai-3d-reconstruction","at":"2026-10-21T17:49:04.869Z","pid":43784,"ppid":5076,
 "execPath":"D:\\deepseek\\DeepSeek Harness.exe",
 "argv":["D:\\deepseek\\DeepSeek Harness.exe",
         "D:\\deepseek\\resources\\app.asar\\dsh\\node_modules\\@deepseek-ai\\dsh-desktop-host\\lib\\index.js",
         "D:\\deepseek\\resources\\app.asar\\dsh"],
 "nodeVersion":"v24.21.0","tools":[17 个 wm_* 工具], "projectRoot":"D:\\wenmai-huazhang", ...}
```

`pid 43784 / ppid 5076` = 正在运行的 GUI 宿主；`argv` 第一段是 `dsh-desktop-host`，说明是宿主进程内的真实挂载，不是测试脚本伪造。

安装状态（当前）：

- 依赖：`用户提供的原始资产 / 本机工具配置` → **`link:` 指向源码目录**（改 `lib/`、`python/` 立即生效）
- 激活：`profiles\desktop\cordis.patch.yml` 末尾一条 `insert` 行（id/name = `wenmai-3d-reconstruction`）
- **没有**同时写进 `dsh.profile.bundles`（两种方式互斥，避免重启后同 id 重复注册）
- 回滚：删除该 insert 行即可停用；`dsh plugin --profile desktop remove wenmai-3d-reconstruction` 卸载依赖；QA 的 `install-profile.ps1` 会在改动前把 `package.json` / `cordis.patch.yml` / `pnpm-lock.yaml` 备份到 `.backup\<时间戳>\`

---

## 5. Three.js 集成验证（真实浏览器）

因为项目前端正被另一条工作流并发修改，插件**没有改动前端源码**，而是自带一个与前端**同版本 three（r180）+ GLTFLoader** 的独立验证页（`tests/viewer/`，`node serve.mjs`，import map 指向前端 `node_modules/three`）。

| 检查 | 结果 |
|---|---|
| 加载 | `window.__VIEWER__.ready = true`，`error = null`（页面同时显示"无 Three.js 运行错误"） |
| 几何 | 690 mesh / **216,202 三角面** / 69 材质 |
| 尺度 | 包围盒 **15.98 × 12.68 × 15.98 m**（台基 16 m、脊高 12.28 m、底座 −0.4 m）——单位与朝向正确 |
| 命名 | 屋顶对象 20 个（`ROOF_*` / `TILE_*`），GLB 节点中含**全部 15 个 `FRAME_F1_00x` / `FRAME_F2_00x`** 锚点 |
| 截图 | `outputs/wenmai-3d/renders/threejs_verify_v4_front34.png`（v3 版另存 `threejs_verify_front34.png`） |

集成方式（留给前端负责人一行切换，插件不越权改源码）：

```ts
// frontend/src/features/heritage-gallery/scene/GalleryModel.tsx
export const MODEL_URL = '/models/wenmai_gallery_v5_wm_roof.glb?v=wmroof1';
```

GLB 已就位：`frontend/public/models/wenmai_gallery_v5_wm_roof.glb`（8.92 MB，低于 16 MB 预算），原 `wenmai_gallery_v5.glb` 未被覆盖，可随时切回。

---

## 6. 视觉匹配：两次真实迭代（参考图 → 相机 → 渲染 → 差异 → 改参 → 再渲染）

流程全部由插件工具完成，参考图 `R02`（`attachment-34905d3a…png`，正面偏右 3/4 外观）。

| 指标（R02 vs 同一 CAM_Front34 渲染） | 迭代 v2 | 迭代 v3 | 变化 |
|---|---|---|---|
| 细节能量比 detailEnergyRatio | 0.1534 | **0.1675** | +9.2%（更接近参考图的细节密度） |
| 檐口段比例差 roof band Δ | +0.1245 | **+0.0860** | 屋顶占比更接近参考 |
| 上层段 Δ upper | −0.2004 | **−0.1486** | 改善 |
| 下层段 Δ lower | +0.1492 | +0.1360 | 略改善 |
| 台基段 Δ plinth | +0.0439 | −0.0440 | 绝对差变小 |
| 地面段 Δ ground | −0.1172 | **−0.0294** | 改善 |
| 轮廓 IoU | 0.6840 | 0.6801 | 基本持平（在噪声内，**不作为提升宣称**） |

v3 的改动来自 v2 差异报告给出的建议：`overhang 1.35 → 1.70`、`tileRows 30 → 40`、`detail medium → high`。
**明确不宣称还原度百分比**：渲染是几何着色，参考图是手绘插画，色彩与细节差里含光照/后期成分；`wm_propose_geometry_changes` 对每条建议都附了 caveat（例如分段名是"位置标签"而非实测檐口）。

产物：
- 对照图 `outputs/wenmai-3d/reports/comparisons/v{2,3}/compare/{side_by_side,overlay,contour,overlay_alpha}_*.png`
- 差异报告 `reports/diff/v2/diff_report.md`
- 参数建议 `reports/changes/v2/proposals_R02.{json,md}`（10 条，4 条 high，含证据与预期效果）

---

## 7. 场景自动审查（如实报告，不折算）

对出货 `wenmai_gallery_v5.blend` 的审计（只读）：

| 检查 | 状态 | 说明 |
|---|---|---|
| 模型是否超出底座 | pass | 包围盒 −7.99…7.99 / −0.4…12.3，在 16 m 底座内 |
| 法线（有符号体积） | **fail** | 1136 个闭合网格中 **54 个内翻**（全部是 v5 旧 `INT_BEAM_SEC*` 天花梁，各 ≈ −0.081 m³）——不是插件生成的部件 |
| 屋面漏洞 | warn | 228 个边界环 / 19 个屋面网格；其中 188 个严格位于自身包围盒内 5% 以上；标注为"线索而非漏洞计数"，另设 `roof_puncture_visual: manual` |
| 浮空瓦片 | pass | 16 片瓦对 39 个屋面，0 片超出 0.35 m（精确 BVH 三角相交判定） |
| 楼梯连通 | pass | 58 段，z 0.24→3.61，最大缺口 −0.006 m，接到 3.60 楼板 |
| 构件穿插 | pass | 40 组测试 0 对相交 |
| 15 个画框 | pass + warn | 15/15、无重复、均为可编辑 empty、位置偏差 0 m、**0 被埋**；6 个"正面被几何遮挡" warn；`FRAME_F1_007`（入口）无墙板可测 → manual |
| Three.js 运行期错误 | manual | Blender 无法判定，必须浏览器验证（已由 §5 完成） |
| 贴图分辨率 | not_checked | 当前模型 0 贴图 |

> 说明：QA 报告里另有 7 项工具自报 fail/warn，属于上表范围（如 v5 旧梁内翻、画框遮挡、`INT_CAISSON` 等在 roof 清扫时被删除的旧构件），全部**保留不折算**。

---

## 8. 用插件优化现有展馆：屋顶 + 二层回廊

按要求，插件验收通过后先做这两处，并确认视觉效果确有提升。

| 部位 | 改动 | 证据 | 判断 |
|---|---|---|---|
| 屋顶 | 用 `wm_generate_roof {style:'double-eave', overhang:1.7, tileRows:40, detail:'high'}` 在**工程模型副本**上重生成：774 片瓦 / 158 垄 / 瓦当 316 / 正脊 37.1 m；清扫 ROOF_MAIN/ROOF_SKIRT + 101 件旧屋顶暗架（檐上穿模消失）；其余构件（室内、木构、画框、相机、铺装）零改动 | `renders/roof_v3_high/wm_front34.png`、`reports/iso_v5_roof.json`（前缀差全 0） | **提升**：瓦垄/瓦当/重檐/脊饰成为真实几何，占比更接近参考（§6） |
| 二层回廊 | 用 `wm_generate_interior {detail:'high'}`：真实挑空（裁旧楼板 16 面 ×2）、36 栏杆柱、90 挂落格、藻井天花 20 格、暖光格窗 17、灯笼 5；**15/15 画框锚点沿用** | `renders/integration_v4/wm_floor2.png`（可见挑空、回廊、藻井、暖光格窗）、`wm_front34.png`（二层格窗透暖光） | **提升**：由"平板 + 栏杆"变为"开敞挑空 + 回廊 + 藻井 + 暖光格窗"；仍待精修：挑空近景一侧楼板切口偏大 |
| 最终整合模型 | `assets/exports/wenmai_gallery_v5_wm_roof.glb` + `frontend/public/models/wenmai_gallery_v5_wm_roof.glb`（8.92 MB / 216k 三角面 / 69 材质），Three.js 同版本加载无错误 | §5 | 可切换；**未改前端源码**（该文件正被并发工作流编辑，避免互相覆盖） |

---

## 9. 未完成 / 已知限制（不掩饰）

1. **参考图上的真实相机对应点仍需人工**：六张外观参考图是插画，没有可自动拾取的 3D 地标；`wm_match_camera` 的求解精度用 v5 自身的 12 组对应点验证（RMS 0.000275 px，焦距 41.9998 vs 真值 42.0），但"从参考图反求相机"仍需要人工点选像素。
2. **分段比例是位置标签**：`roof/upper/lower/plinth/ground` 由先验分位 + 行梯度吸附得到，不是实测檐口/楼层线；因此只用于"改一版再看"的方向，不作为几何事实。
3. **室内近景挑空切口偏大**（v4 `floor2` 视角可见），需要再裁 0.3–0.5 m；本轮未改。
4. **v5 旧构件的固有缺陷**：54 个旧天花梁内翻绕序、6 个画框正面被遮挡——属于出货模型既有问题，插件如实报出，未擅自改动原工程。
5. **细节能量仍低于参考图**（0.1675 vs 参考 0.16 归一化口径的对比值），差距含插画的线条与光照；挂落目前是程序化格条而非雕刻浮雕。
6. **前端集成未落地为源码改动**：并发工作流正在改 `GalleryModel.tsx`/`HeritageScene.tsx`，本插件只交付 GLB 与一行切换说明，避免冲突。

---

## 10. 复现命令

```powershell
# 1) 构建 TypeScript
$env:ELECTRON_RUN_AS_NODE=1
$node = "D:\deepseek\DeepSeek Harness.exe"
$tsc  = "D:\wenmai-huazhang\frontend\node_modules\typescript\lib\tsc.js"
& $node $tsc -p "D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction\tsconfig.json"

# 2) 三套测试
$root = "D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction"
& $node "$root\tests\run-unit.mjs"
& $node "$root\tests\run-registration.mjs" --strict-contract
& $node "$root\tests\run-e2e.mjs"

# 3) bundle 机制（隔离 DSH_HOME，不动现网 profile）
powershell -File "$root\scripts\verify-bundle.ps1" -DshHome "D:\wenmai-huazhang\outputs\wenmai-3d\tests\dsh-home"

# 4) 浏览器验证页（同版本 three）
& $node "$root\tests\viewer\serve.mjs"     # http://127.0.0.1:5199/
```

单条 Blender 任务也可以脱离宿主复现（job 协议见 `docs/CONTRACT.md` §2）：

```powershell
& "D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe" -b -noaudio `
  --python "…\wenmai-3d-reconstruction\python\wm_job.py" -- "<job.json>"
```
