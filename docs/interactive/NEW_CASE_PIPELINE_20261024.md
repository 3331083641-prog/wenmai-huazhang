# 新图入库流水线：一张图进去，三种互动出来

这份文档说明「每次生成的新图都会自动进入真实案例，并且自动带上互动画境、一图一境、画境漫游」这套流程：它由哪些步骤组成、每步产出什么、什么算达标、哪些地方必须人工复核。

一句话概括：**图 + 风格 = 案例目录（图、元数据、三折叙事、4–6 处热点）+ 画境资产（深度网格 / 遮罩 / 抠像 / 清单）**，前端用 `import.meta.glob` 自动收进作品卡，不需要改代码。

---

## 一、三条入口，同一套流程

| 入口 | 谁触发 | 命令 / 路径 | 是否自动 |
| --- | --- | --- | --- |
| 创作台出图 | 用户点「生成」 | `POST /generate` → `case_store.save_case()` → 后台线程 `interactive_jobs.start_interactive_build()` | 全自动（`AUTO_BUILD_INTERACTIVE=true` 默认开） |
| 已有成图导入 | 命令行 | `python scripts/interactive/ingest_case.py --image <png> --slug <名字> --style-id <风格>` | 手动触发，其余全自动 |
| 旧案例重做互动 | 命令行 | `python scripts/interactive/ingest_case.py --refresh <案例目录名>` | 手动触发 |

三条入口最后都落到同一个目录结构与同一份 `experience.json`，所以前端只有一条读取路径。

---

## 二、流程与产物

```
新图 (png)
  │
  ├─ 1 落盘          docs/examples/<slug>/generated.png（统一转 PNG，记录 1024×1024 之类的真实尺寸）
  │                  docs/examples/<slug>/metadata.json（sha256 / 风格 / 标题 / 来源）
  │
  ├─ 2 深度          Depth Anything V2 Small（GPU）→ 归一化 gamma 0.72 → 3px 平滑
  │                  缓存 scripts/interactive/_probe/<slug>-depth.npy（重跑不重复推理）
  │
  ├─ 3 热点          深度显著性 + 色彩密度打分（48×48 网格）→ 按深度分带取点
  │                  远景 / 中景各强制一处，其余按分数补 → 4–6 处，半径 0.09
  │                  命名：本地 Qwen3-VL 只允许从该风格词表里选词，词表外回退「画面<方位>局部」
  │
  ├─ 4 叙事          三折（每折 2 个热点）→ 镜头倍率由焦点离画面中心的距离算出（1.15–1.85）
  │                  文案来自该风格知识包；来源编号沿用已核验的 SRC-*
  │
  ├─ 5 experience.json   → docs/examples/<slug>/experience.json（前端自动加载）
  │
  ├─ 6 画境资产      build_painting_world.py --config <临时配置>
  │                  → frontend/public/interactive/<slug>/world/
  │                    art.webp / depth-rg.png / masks.png / backdrop.webp /
  │                    cutout-subject.webp / depth-preview.png / world.json
  │
  └─ 7 回写          metadata.json 写入 experienceId + interactive{status,world,hotspots}
                     docs/examples/<slug>/ingest-report.json（机器可读报告）
```

前端装配：

- `frontend/src/data/autoExperiences.ts` — `import.meta.glob('../../../docs/examples/*/experience.json')` 读清单，**图只认同一目录下的 `generated.png`**（绝不借用同风格精选案例的图，那正是「标题写瑞猫、图里是童子」的错位来源）。
- `frontend/src/data/savedCases.ts` — 同理收 `docs/examples/*/metadata.json`（排除五件精选），所以后端没起、离线打开也能看到新案例。
- `frontend/src/data/experiences/index.ts` — 把自动案例并进 `experiences`；`experienceId` 一旦写回 metadata，展厅卡片 `resolveExperience()` 就能命中，三个按钮同时出现。

---

## 三、达标线（每次入库都要过）

| 项 | 门槛 | 怎么查 |
| --- | --- | --- |
| 深度区分度 | 近景（>0.8）占比 ≤ 40%，远景（<0.35）> 0 | 报告 `depth.nearShare / farShare` |
| 深度不塌缩 | 中段 0.4–0.6 的像素占比 < 60%（说明不是一片灰） | 报告 `depth.percentiles` |
| 遮罩覆盖率 | 云雾、植被各 2%–45%；水面同理，但**画面里没有可读成水面的青色时允许接近 0** | 报告 `masks.coverage` |
| 抠像 | `alpha_coverage` 在 0.05–0.85 之间，且 bbox 不贴满整幅（< 65% 边长） | 报告 `cutouts` |
| 热点 | 4–6 处，两两间距 ≥ 0.17，深度夹在 [0.14, 0.88] | `world.json` / 报告 `hotspots` |
| 热点状态 | `locationStatus: approximate`、`reviewStatus: pending`（自动结果必须自曝） | `experience.json` |
| 叙事 | 固定三折，`frame.scale` 1.15–1.85，`focusHotspotIds` 必须都存在 | `data-integrity` 测试 |
| 来源 | 每个 `sourceIds` 都能在 `culture_knowledge/sources.json` 里解析 | `data-integrity` 测试 |
| 文件 | 画境 7 个文件齐全非空，`world.json` 热点数与前端一致 | `data-integrity`「五个真实案例都必须有画境漫游」用例 |
| 文案纪律 | 不虚构馆藏、不排名、非非遗品类不自称非遗、不把传统工艺写成工业化生产 | 既有文案纪律用例 |

自动化只保证**结构与数值**达标；画面是否好看、热点是否点在有意思的地方，仍然要人看一眼（见第六节）。

---

## 四、五件作品的实测数字（本轮）

| 作品 | 热点 | 抠像 | 深度 p10/p50/p90 | 近景占比 | 画境体积 |
| --- | --- | --- | --- | --- | --- |
| 云鹤临水楼 | 6 | 松枝坡石 α0.640 | 0.000 / 0.389 / 0.855 | 14.1% | 1.23 MB |
| 瑞猫迎春 | 6 | 猫身与虎斑 α0.729 | 0.314 / 0.527 / 0.887 | 22.2% | 1.68 MB |
| 绣兔牡丹 | 5 | 白兔与绣线 α0.682 | 0.060 / 0.545 / 0.878 | 19.9% | 1.37 MB |
| 青花蝶韵 | 4 | 青花蝶 α0.677 | 0.136 / 0.683 / 0.827 | 14.0% | 1.11 MB |
| 剪影灵狐 | 4 | 狐狸剪影 α0.715 | 0.180 / 0.467 / 0.845 | 16.5% | 1.40 MB |

镜头：`fov 34°`，`distance_fill 1.6354`，`dolly 0.62–1.55`，`yaw ±18°`，`pitch ±12°`，入场从 `1.74×distance_fill` 推进到 `1.55`（整幅画铺满视口），滚轮再往里推到 `0.62`。

五件作品在浏览器里逐件进入并截图核对：`screens/v4-01…v4-05-wander-*.png`，用本地 Qwen3-VL 粗看四张新截图，结论都是「能看到完整作品、主体清晰、无撕裂/重影/错位/大片空白」。VLM 的判断只作粗筛，不作为「好看」的证明。

---

## 五、跑一遍

```powershell
cd D:\wenmai-huazhang

# 1) 从一张新图生成整套互动（不含画境）
D:\wenmai-huazhang\backend\venv\Scripts\python.exe -X utf8 scripts\interactive\ingest_case.py `
  --image D:\out\new.png --slug zx-1021-a --style-id zhuxianzhen --title "瑞猫迎春·新作"

# 2) 跳过后端，单独重做某案例的互动
D:\wenmai-huazhang\backend\venv\Scripts\python.exe -X utf8 scripts\interactive\ingest_case.py --refresh <案例目录名>

# 3) 只重算画境（改过热点坐标、调过 gamma 之后）
D:\wenmai-huazhang\backend\venv\Scripts\python.exe -X utf8 scripts\interactive\build_painting_world.py --style <slug> --force-depth

# 4) 热点坐标改了之后重新导出构建配置（TS 是唯一事实来源）
D:\Node\node-v24.15.0-win-x64\node.exe scripts\interactive\export_artwork_configs.mjs
D:\Node\node-v24.15.0-win-x64\node.exe scripts\interactive\export_artwork_configs.mjs --check

# 5) 前端校验
cd frontend
D:\Node\node-v24.15.0-win-x64\node.exe .\node_modules\typescript\bin\tsc --noEmit -p tsconfig.json
D:\Node\node-v24.15.0-win-x64\node.exe --test tests\data-integrity.test.ts
```

相关环境变量：

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `AUTO_SAVE_CASES` | `true` | 出图成功后自动落盘为案例 |
| `AUTO_SAVE_DEMO` | `false` | 演示/占位图是否也落盘 |
| `AUTO_SAVE_MAX_CASES` | `200` | 案例上限（超出按时间清理最旧的运行期案例） |
| `AUTO_BUILD_INTERACTIVE` | `true` | 落盘后是否自动生成三折 + 热点 + 画境 |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | 本地视觉模型地址（热点命名用） |
| `QWEN_VL_MODEL` | `qwen3-vl:4b-instruct-q4_K_M` | 热点命名模型 |

任务状态：`GET /interactive-jobs`（后台线程跑完把 `experienceId` 写回 metadata）。

---

## 六、必须人工看一眼的地方

自动流程只做「结构正确 + 数值在范围内」，下面四件事机器判不了，出图后请人工过一遍：

1. **热点是否点在东西上**：确认每个点落在主体/纹样上，而不是空白纸底。落空了就改 TS/配置里的坐标再重跑第 3 步。
2. **自动标题是否读得通**：4b 视觉模型给的词经常偏保守（同一幅里可能出现两个「蝶翼」），读起来别扭就手工改成更准确的说法。
3. **文化解读是否贴这张图**：流程沿用的是该风格知识包的通用解读 + 来源编号，不针对这一张的具体内容；要作为正式内容发布，必须逐条核对。
4. **画境观感**：进入后整幅画是否清楚、推近看是否有明显的拉伸条纹。截图放在 `docs/painting_world/screens/`。

人工复核完之后，把这件案例的 `hotspots[].locationStatus` 从 `approximate` 改成 `verified`、`reviewStatus` 改成 `confirmed`，前端就不再显示「待复核」。

---

## 七、已知限制（不粉饰）

1. **自动热点是估计值**，没有逐点裁切复核；正式对外前必须人工确认（上面第六节）。
2. **剪影灵狐的水面遮罩只有 0.29%**：这张剪纸整体偏暖红，几乎找不到青色像素，水面微动层等于关闭。云雾（10.4%）与植被（28.4%）两层仍在工作，观感不受影响，但「水面在动」这件事在它身上不成立。
3. **绣兔牡丹的深度与画面亮度关联弱**（源图极亮、低饱和），深度结构是从纹理起伏里估出来的，主体是否前凸建议人眼确认一次（`frontend/public/interactive/bianxiu/world/depth-preview.png`）。
4. **开发服务器要重启一次**：`docs/examples/` 在 Vite root 之外，新增案例目录不会被 dev server 的 watcher 发现（编译期 glob 已缓存）。`npm run build` 会重新扫描，生产包不受影响。
5. **深度是单图估计**：只能给前后关系，不能绕视到物体背后，也不是三维重建。所有文案都按这个口径写，不要在别处升级成「3D 场景」。
6. **8 张/百张规模**：目前五个画境每个约 1.1–1.7 MB，`AUTO_SAVE_MAX_CASES=200` 时展厅会很长；真要长期跑，需要给自动案例加分页或按时间折叠。

---

## 八、文件索引

| 文件 | 作用 |
| --- | --- |
| `scripts/interactive/ingest_case.py` | 流水线主脚本：落盘 → 深度 → 热点 → 叙事 → experience.json → 画境 → 回写 |
| `scripts/interactive/build_painting_world.py` | 画境构建器（读配置；`--style/--all/--config`） |
| `scripts/interactive/artworks/<slug>.json` | 每件作品的构建配置（热点几何从 TS 导出） |
| `scripts/interactive/export_artwork_configs.mjs` | 把 `frontend/src/data/experiences/*.ts` 的热点几何导出成配置（`--check` 校验一致性） |
| `scripts/interactive/_probe/world-build-report.json` | 五件作品的构建报告（深度分位、遮罩、抠像、异常） |
| `scripts/interactive/_probe/pipeline-selftest/` | 流水线自检产物（experience.json + ingest-report.json），由 `data-integrity` 测试校验 |
| `backend/interactive_jobs.py` | 出图后的后台任务（调流水线，不阻塞响应） |
| `frontend/src/data/autoExperiences.ts` | 自动案例清单加载器 |
| `frontend/src/data/savedCases.ts` | 自动案例的展厅卡片（离线可看） |
| `docs/examples/<slug>/` | 案例目录：图、metadata、experience.json、ingest-report.json |

---

## 九、端到端自检记录（2026-10-21 实跑）

用《青花蝶韵》的成图造了一个临时案例 `autocheck-demo`，走**后端那条路**（不是命令行），确认「出图 → 落盘 → 自动三互动 → 展厅出现卡片」整条链通：

| 步骤 | 实测结果 |
| --- | --- |
| `interactive_jobs.start_interactive_build('autocheck-demo')` | `{enabled: true, status: running}` |
| 后台任务终态 | `status: ready, exitCode: 0, elapsedSec: 20.6`（深度有缓存；首次约 69 s） |
| metadata 回写 | `experienceId: autocheck-demo`、`interactive.status: ready`、`hotspots: 5` |
| 风格继承 | `--refresh` 从既有 metadata 读到 `styleId: qinghua`、标题「自动入库自检·青花」，解说用的是 `SRC-QH-JINGDEZHEN-001`（没有退回默认的年画文案） |
| 展厅卡片 | 第 6 张卡出现，三个入口齐全：`/experience/autocheck-demo`、`/story/autocheck-demo`、`/wander/autocheck-demo` |
| 画境漫游 | `manifest.slug = autocheck-demo`，5 处热点，入场深度 1.55；截图 `docs/painting_world/screens/v4-07-auto-ingest-wander.png` |
| 一图一境 | 滚动换折生效：`transform` 变为 `translate(-46.1%, 9.4%) scale(1.27)` |
| 清理 | 临时案例与它的画境资产已删除，展厅回到 5 张卡（0 残留）；自检产物留在 `scripts/interactive/_probe/pipeline-selftest/` |

### 这一步抓到的真 bug（已修）

第一次跑完，展厅**整页白屏**。原因：流水线把 `visualAnalysis.dominantColors` 写成了空数组，而 schema 要求至少一项；dev 下校验失败会直接抛错。

修法两条：

1. 流水线新增 `dominant_palette()`，用中位切分量化取主色（青花那张得到 `#fcf9f4` / `#728bb9`）；
2. `data-integrity` 新增守卫用例「docs/examples 下每个自动入库清单都必须能通过 schema 校验」——以后任何一份自动清单不合格，都会在测试阶段被拦下，而不是等到用户打开页面白屏。

这类「空数组当占位」的写法在自动生成里最容易埋雷，写新字段时请照这个先例补一条守卫。

### 自动案例同样自带三种看法互切

新案例不需要额外配置：`/experience/<id>`、`/story/<id>`、`/wander/<id>` 三个页面都挂了同一个 `ExperienceModeSwitch`，它只看 `experienceId` 和「有没有画境资产」。只要流水线写出了 `world.json` 并把 `experienceId` 回写进 metadata，这三个入口就自动串起来，前端不用改代码。