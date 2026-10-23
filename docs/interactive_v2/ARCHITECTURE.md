# 架构说明 · 纹脉华章 2.0「一卷五境」

> 分支：`feat/interactive-v2`（仅本地）　编写日期：2026-10-20
> 本文描述**已经落地并实机跑过**的结构，不是规划稿。未实现的部分明确标注为「未实现」。

---

## 1. 一句话架构

在既有「生成 → 文化卡 → 文创」链路上，**新增一层只读的「文化体验数据层」**，
用归一化坐标把「AI 生成的一张图」变成「可点、可读、可走」的互动作品；
前端完全离线可看，不新增任何依赖、不新增任何模型调用。

```
                        ┌──────────────────────────────┐
   docs/examples/*.png  │  savedCases.ts（既有，未改） │ 5 件真实案例
                        └───────────────┬──────────────┘
                                        │ 注入 artworkUrl / referenceUrl / cardUrl
   frontend/src/data/experiences/*.ts   ▼
   （手写草稿：热点 + 章节 + 分层） ─► experiences/index.ts ── Zod 校验 ──► CultureExperience[]
                                        │
        culture_knowledge/sources.json ─┘ resolveSources() 挂来源
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
      /experience/:id            /story/:id                /wander/:id
      「画中有话」               「一图一境」               「画境漫游」
      CultureExperienceViewer    Story.tsx                 Wander.tsx
```

---

## 2. 目录职责

### 2.1 数据层（本轮新增，纯数据 + 校验，不含 JSX）

| 路径 | 行数 | 职责 |
|---|---|---|
| `frontend/src/features/culture-experience/types.ts` | 145 | 全部类型定义：`CultureHotspot`、`CultureChapter`、`CultureLayer`、`CultureExperience` |
| `frontend/src/features/culture-experience/schema.ts` | 223 | Zod 4 运行时校验；`validateExperienceDraft` / `parseExperienceDraft` |
| `frontend/src/data/experiences/{zhuxianzhen,bianxiu,songhua,qinghua,jianzhi}.ts` | 133–176 | 五件作品的手写草稿：25 处热点、15 折章节、1 组分层素材 |
| `frontend/src/data/experiences/index.ts` | 69 | 校验 → 注入真实图片地址 → 导出 `experiences` / `getExperience` / `resolveSources` / `auditExperienceData` |
| `culture_knowledge/sources.json` | — | 11 条可点开的机构来源，带 `verification` 与 `verificationNote` |
| `culture_knowledge/<style>.json` | — | 每件作品的来源要点展开（给人看与给后续引用） |

**关键约定**：热点坐标**只存在于数据文件**，任何 TSX 里都不允许出现坐标常量。
这样坐标可以单独审、单独测、单独替换。

### 2.2 交互层（本轮新增，组件）

| 组件 | 行数 | 职责 |
|---|---|---|
| `components/CultureExperienceViewer.tsx` | 308 | 「画中有话」主体：缩放/拖拽/双击定点/键盘/粘性解读面板 |
| `components/HotspotLayer.tsx` | 137 | SVG 轮廓 + 编号圆点，`viewBox="0 0 1 1"`，`vector-effect: non-scaling-stroke` |
| `components/KnowledgePanel.tsx` | 183 | 画面观察 → 文化解读 → 位置状态 → 来源 → 下一处/在故事里看 |
| `components/ViewToolbar.tsx` | 68 | 缩放 −/百分比/+、复位、适配、位置框开关、读故事 |
| `components/ArtworkCompare.tsx` | 74 | 参考图/成图对照，`clip-path` + 透明 `input[type=range]`（无新依赖） |
| `components/SourceChips.tsx` | 36 | 来源胶囊，外链 + 「未核验」显式提示 |
| `components/ExperienceErrorBoundary.tsx` | 46 | 类组件兜底，出错时给回展厅的出口（不用白屏） |
| `hooks/useContainedImage.ts` | 34 | ResizeObserver 测量容器，算出 `object-fit: contain` 的真实绘制区域 |
| `utils/geometry.ts` | 137 | 纯函数：contain 框、矩形/圆/多边形换像素、命中测试、焦点位移 |
| `utils/assets.ts` | 7 | `BASE_URL` 前缀，兼容静态托管子路径 |

### 2.3 页面层

| 路由 | 文件 | 行数 | 说明 |
|---|---|---|---|
| `/experience/:id` | `pages/Experience.tsx` | 30 | 取数据 → ErrorBoundary 包裹 Viewer |
| `/story/:id` | `pages/Story.tsx` | 397 | 三幕式：卷首 → 滚动章节 + 粘性镜头 → 带走 |
| `/wander/:id` | `pages/Wander.tsx` | 334 | 2.5D 分层视差实验，仅 `songhua` 有素材 |
| `/gallery` | `pages/Gallery.tsx` | 172 | 改写为「文化作品展厅」，既有能力全部保留 + 互动入口 |
| `/` | `pages/Home.tsx` | 292 | 新增「进入画里，再看一遍」三卡入口（轻量，不抢首屏） |

---

## 3. 坐标系与几何（最容易出错的地方）

### 3.1 归一化坐标

所有热点坐标是 **0–1 归一化**，相对**图片本身**，不是相对容器：

- `rect`：`{x, y, width, height}`
- `circle`：`{cx, cy, r}`，**r 以画面短边为基准**（圆不会被拉成椭圆）
- `polygon`：`points: [number, number][]`

### 3.2 为什么必须先算 contain 框

画面容器是自适应的，图片用 `object-fit: contain`，所以**图片实际绘制区域小于容器**。
若把热点直接按容器百分比定位，一旦容器宽高比变化（换屏、侧栏折叠、手机横竖屏），
热点就会整体漂移。因此：

```
computeContainBox(container, image) → { x, y, width, height }  // 真实绘制区
hotspotBox(geometry, imageBox)     → 屏幕像素框
```

`useContainedImage` 用 `ResizeObserver` 监听容器，容器尺寸变化时重算，
热点层跟着重排。这是「换分辨率热点不跑偏」的唯一保证。

### 3.3 缩放约定

```
transform: translate((0.5 - fx) * s * 100%, (0.5 - fy) * s * 100%) scale(s)
transform-origin: center
```

`(fx, fy)` 是希望落在容器中心的归一化焦点。因为 origin 在中心，位移量必须是
`(0.5 - f) * s`，而不是 `0.5 - f * s`——后者是 origin 在左上角时的公式，
写错会导致「越放大越偏」。

位移上限 `±(s - 1) * 50%`，超出即夹紧（`clamp`），避免拖出黑边。

### 3.4 缩放时界面元素的反向缩放

热点编号圆点位于被缩放容器内部，会跟着 `s` 倍变大。因此圆点自身
`scale(1 / max(s, 1))` 抵消，保持 32px 可点面积；SVG 轮廓用
`vector-effect: non-scaling-stroke` 保持 1–1.6px 线宽。

---

## 4. 数据流与校验

```
draft (手写) ──► validateExperienceDraft ──► issues[] 为空才导出
                     │
                     ├─ shape 与 geometry 不一致 → 报错
                     ├─ confirmed 但 sourceIds 为空 → 报错（禁止无出处断言）
                     ├─ confirmed 却标 unverified → 报错（自相矛盾）
                     ├─ 章节 index 必须 1..n 连续
                     ├─ focusHotspotIds 必须存在
                     └─ mode=layered 必须 ≥2 层
```

校验在**模块加载时**执行一次（`index.ts` 顶层），所以数据写错会在开发阶段直接炸，
而不是等到用户点开才发现。生产构建里同一份代码也会跑，成本可忽略。

`auditExperienceData()` 额外输出一份可打印的审计摘要（热点数、已复核数、来源覆盖率），
供验收脚本和 `FINAL_ACCEPTANCE.md` 使用。

---

## 5. 与既有系统的关系

| 既有能力 | 是否改动 | 说明 |
|---|---|---|
| `/creator` 生成工作台 | 不改 | 组件与调用链原样保留 |
| `POST /generate` | 不改 | 后端零改动，互动页面**完全不调用** |
| `POST /analyze-image` | 不改 | 同上 |
| `/gallery` 案例浏览 | **改写但保留全部能力** | 参考图/成图/文化卡/文创预览/工作台记录入口都在，只是排布变了 |
| `/products` 文创预览 | 不改 | 通过 `loadSavedCase()` 写入 `wenmai_latest_result` 后进入 |
| `savedCases.ts` | 不改 | 互动数据反向读取它注入图片地址 |
| 静态托管（`VITE_STATIC_SHOWCASE`） | 兼容 | 新增页面全部用相对路径 + `publicUrl()` |

**依赖**：本轮新增依赖 = 无。`react-compare-slider` 评估后用原生实现替代；
GSAP 因许可问题未使用；three.js 未引入（S3 不是三维重建）。

---

## 6. 离线可用性（实测）

互动三条路由的资源全部来自本仓库：

```
页面资源统计（/experience/zhuxianzhen-ruimao）
127.0.0.1:5173 …… 77 个（含 HMR）
fonts.googleapis.com / fonts.gstatic.com …… 55 个（既有字体）
:8000 后端 ……… 0 个
```

停掉后端（`127.0.0.1:8000` 无监听）后重新加载 `/experience/zhuxianzhen-ruimao`：
6 个热点、解读文案、来源链接、故事深链全部正常。
这就是「无模型也能看的静态案例」的实测证据。

---

## 7. 已知限制（不粉饰）

1. **热点坐标是工程标注，不是文物测绘**：原始 `metadata.json` 没有 bbox，25 处坐标全部由本项目
   用「本地视觉模型给候选格 → 逐点裁切复核」得出，`provenance.hotspotMethod` 有记录，
   逐点复核通过的标 `verified`，未通过的降级 `approximate`。
2. **不是所有作品都能漫游**：只有《云鹤临水楼》有 3 层素材，其余 4 件 `/wander` 会明确显示「暂未开放」。
3. **S3 不是三维重建**：分层来自「区域分带 + 羽化遮罩」，没有深度模型、没有点云、没有 mesh。
   文档与界面文案都按这个口径写。
4. **S4 纹脉星球只有调研**，没有实现，也不阻塞 S1–S3。
5. **未安装 `@types/react`**：仓库既有的类型环境如此，因此组件内用最小结构类型描述鼠标/指针事件，
   而不是 `React.PointerEvent`。类型检查（`tsc --noEmit`）通过，但 React 相关类型是宽松的。
6. **热点圆点 32px**：移动端略低于 44px 的推荐触摸目标，但画面密集时放大圆点会遮住画，
   因此选择 32px + 命中区补足。

---

## 8. 验证入口

```bash
cd D:\wenmai-huazhang\frontend
node node_modules\typescript\bin\tsc --noEmit        # 类型检查
node --test "tests/*.test.ts"                        # 32 个单元/数据用例
node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173
```

`npx` 在本机被 PowerShell 执行策略拦住，所以一律用 `node node_modules/...` 直接调用。