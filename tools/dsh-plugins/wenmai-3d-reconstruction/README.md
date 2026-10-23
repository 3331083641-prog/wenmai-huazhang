# wenmai-3d-reconstruction

《纹脉华章》展馆专属的 DeepSeek Harness 三维重建插件：**十张参考图 → 结构化建筑规格 → Blender 参数化建模 → 真实渲染 → 参考图对照 → 参数修正 → 场景审查**。

- 宿主版本：**DSH 0.2.1-rc.2**（本次开发与验证所用版本；插件不依赖 `@deepseek-ai/dsh-tools` 运行时，只用插件的注册接口）
- Blender：`D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe`（5.2.2 LTS）
- 授权目录：`D:\wenmai-huazhang`（读/写都限制在该目录内；唯一例外是本机 Blender 可执行文件）

> 本包的核心原则：**不编造证据**。数值指标来自真实像素/真实几何；无法自动判断的事项一律标 `manual` / `not_checked`，绝不写成 `pass`。

## 一、它提供什么

17 个工具，分四组：

| 组 | 工具 | 作用 |
|---|---|---|
| A 参考图重建 | `wm_analyze_references` | 不用视觉模型，纯 numpy 测量十图：尺寸、调色板、前景轮廓框、屋顶/上层/下层/台基分段比例、边缘密度、梯度方向（判断瓦垄平行 vs 放射）、对称性；输出 `measurements.json` + 拼图 |
| | `wm_build_scene_spec` | 把模型读图得到的结构化观察与实测比例合并成 `scene_spec.json`，校验包络、记录矛盾与未知，不臆造尺寸 |
| | `wm_match_camera` | 由 ≥6 组 3D↔像素对应点解算参考相机（DLT + 非线性优化），返回位置/朝向/焦距与逐点重投影误差 |
| | `wm_validate_multiview` | 把规格里的构件框投影回各参考视角，报告重投影 RMS、逐构件像素偏移与跨图矛盾 |
| B 参数化建模 | `wm_generate_roof` | 中式曲面屋顶：凹曲坡面、**沿坡面平行的瓦垄**（绝不放射）、瓦当/滴水、正脊+垂脊+鸱吻、椽头与斗拱带；只替换 `wm_part="roof"` 的物体 |
| | `wm_generate_timber` | 柱网、主次梁、檩、椽、斗拱块与节点 |
| | `wm_generate_interior` | 两层楼板、中央挑空、**二层开敞回廊（栏杆/棂格/挂落）**、真实楼梯、展墙、门窗、展柜、天花与灯笼；保留 15 个画框锚点 |
| | `wm_generate_diorama` | 16 m 雕花底座/须弥座、回纹带、团花、铺装、台阶、树/竹/花坛/灯笼/石灯/幡杆 |
| | `wm_export_glb` | 导出 Y-up GLB 并回读校验网格/三角面/材质/贴图/体积 |
| C 视觉对照 | `wm_capture_views` | 固定视角真实渲染（front34/front/left/right/back/top/base_low/floor1/floor2/ceiling/eave/corner） |
| | `wm_compare_reference` | 参考图 vs 渲染图：并排图、叠加图、轮廓图 + 轮廓 IoU、质心/尺度偏移、分段边缘误差、Lab 色差、细节比 |
| | `wm_generate_diff_report` | 把差异排成报告：差异最大的五个位置、证据、所属区域 |
| | `wm_propose_geometry_changes` | 把差异映射成生成器参数修改建议（`overhang`/`cornerLift`/`slopePower`/`railingHeight`…），带理由、证据、优先级、预期效果 |
| D 场景审查 | `wm_inspect_scene` | 屋架穿插、屋面漏洞、法线、浮空瓦片、楼梯连通、画框与墙/窗重叠、超出底座、贴图尺寸；`pass/warn/fail/manual/not_checked` 五态 |
| | `wm_check_art_frames` | 15 个画框锚点：id、位置对照 `gallery_layout.json`、重复、是否仍为可编辑 empty、是否被埋墙 |
| | `wm_check_export` | 不依赖外部库校验 GLB：容器头、JSON chunk、网格/材质/内嵌贴图尺寸/动画/体积 |
| | `wm_performance_report` | 三角面/材质/贴图预算、GLB 体积、热点与优化建议 |

## 二、安装（两种方式，任选其一）

前置：DSH 0.2.1-rc.2；本机 Blender；项目在 `D:\wenmai-huazhang`。
安装前请备份 profile 的 `package.json` / `cordis.patch.yml` / `pnpm-lock.yaml`（`scripts\install-profile.ps1` 会自动备份）。

### 方式 1：作为 bundle 安装（推荐，需重启 DSH 生效）

```powershell
$env:ELECTRON_RUN_AS_NODE=1
& "D:\deepseek\resources\runtime\cli\bin\dsh.cmd" plugin --profile desktop add "link:D:/wenmai-huazhang/tools/dsh-plugins/wenmai-3d-reconstruction"
```

`pnpm` 会把包名写进 profile 的 `dsh.profile.bundles`；本包 `package.json` 的 `dsh.bundle.patch` 指向 `cordis.patch.yml`，其中已 insert 好插件行（含 `projectRoot`/`blenderExe`/`timeoutMs`）。重启 DSH 后生效。

也可以从 Web 侧栏 **Plugins** 或 `plugin_manager` 工具安装本目录，效果相同。

### 方式 2：profile 内联激活（不重启，立即生效）

在 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 末尾加：

```yaml
- insert:
    - id: wenmai-3d-reconstruction
      name: wenmai-3d-reconstruction
      config:
        projectRoot: 'D:\wenmai-huazhang'
        blenderExe: 'D:\Codex\blender-5.2.2\blender-5.2.2-windows-x64\blender.exe'
        timeoutMs: 1800000
        allowProjectWrites: true
```

并确保依赖已装（同上一条 `dsh plugin ... add`，但**不要**把它同时留在 `dsh.profile.bundles` 里，否则重启后会出现同 id 两行）。

**二选一**，不要同时用两种：bundle 层与 profile 行都 insert 同一个 id 会重复注册。

### 验证安装

```powershell
Get-Content "$env:USERPROFILE\.dsh\profiles\desktop\cordis.patch.yml" | Select-String wenmai
Get-Content "D:\wenmai-huazhang\outputs\wenmai-3d\logs\activation.json"   # 插件在宿主进程内挂载时写入
```

`activation.json` 里 `pid/ppid/argv` 指向正在运行的 DSH 宿主进程 = 插件确实被真实宿主加载（而不是测试脚本）。

### 启用 / 停用 / 卸载

| 动作 | 做法 |
|---|---|
| 停用（保留文件） | bundle 方式：把 `cordis.patch.yml` 里对应行 `disabled: true`；内联方式：删除该 insert 行 |
| 启用 | 反向操作 |
| 卸载 | 先删除激活行/bundle 条目，再 `dsh plugin --profile desktop remove wenmai-3d-reconstruction` |
| 回滚 profile | 用 `scripts\install-profile.ps1` 产生的 `.backup\<时间戳>\` 覆盖回去 |

插件只读写 `D:\wenmai-huazhang` 与 Blender 可执行文件；移除插件不会改动项目里的模型、图片或前端代码。

## 三、目录结构

```
tools/dsh-plugins/wenmai-3d-reconstruction/
├─ src/                  TypeScript 源码（lib 工具核心 + tools 四组工具）
├─ lib/                  tsc 编译产物（宿主实际加载）
├─ python/               Blender 侧实现（wm_job.py 调度 + 各模块）
├─ cordis.patch.yml      bundle 补丁（insert 插件行）
├─ docs/CONTRACT.md      接口契约（job 协议、参数、返回字段、验证要求）
├─ docs/DSH_PLUGIN_ACCEPTANCE.md  验收报告（真实调用证据）
├─ scripts/              install/uninstall/verify-bundle
└─ tests/                单元、注册、端到端测试与 fixture
```

## 四、构建与测试

```powershell
$env:ELECTRON_RUN_AS_NODE=1
$node = "D:\deepseek\DeepSeek Harness.exe"
$tsc  = "D:\wenmai-huazhang\frontend\node_modules\typescript\lib\tsc.js"
& $node $tsc -p "D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction\tsconfig.json"
& $node "D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction\tests\run-unit.mjs"
& $node "D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction\tests\run-registration.mjs"
& $node "D:\wenmai-huazhang\tools\dsh-plugins\wenmai-3d-reconstruction\tests\run-e2e.mjs"
```

## 五、许可与来源

本插件为本项目自研（MIT）。几何算法参考了仓库内既有的 v5 构建脚本（`assets/gallery3d/scripts/v5/*`）与十张概念图，未引入第三方运行时依赖，未调用付费三维 API，未下载模型，未同步 GitHub。
