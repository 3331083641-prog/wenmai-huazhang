# S0 · 现状审计（动手前）

> 审计时间：2026-10-20 17:20–17:35　分支：`feat/interactive-v2`
> 审计对象：`D:\wenmai-huazhang` 当时的工作区状态
> 目的：在不动手改任何代码之前，先弄清「已经有什么、缺什么、哪些能复用、哪些是坑」。

---

## 1. 当时的事实基线

### 1.1 技术栈（未变）

| 层 | 版本 |
|---|---|
| React / React DOM | 19.0 |
| TypeScript | 5.8.2 |
| Vite | 6.2 |
| Tailwind CSS | 4.1（CSS-first，`@theme` 定义 token） |
| react-router-dom | 7.14 |
| motion（`motion/react`） | 12.23 |
| lucide-react | 0.546 |
| zod | 4.6 |
| 后端 | FastAPI + uvicorn，`backend/app.py` |

Node v24.15.0 / npm 11.12.1。

### 1.2 路由（动手前）

`frontend/src/App.tsx`，33 行，全部包在 `MainLayout` 里：

```
/            /styles      /products    /scenarios
/about       /creator     /gallery
```

`HashRouter`（当 `VITE_STATIC_SHOWCASE === 'true'`）与 `BrowserRouter` 二选一。
**没有任何 `/experience`、`/story`、`/wander` 路由。**

### 1.3 后端端点（未改动）

```
GET  /health
POST /analyze-image
POST /generate
```

`/health` 返回当前 provider、风格参考图就绪状态、视觉分析 provider
（当时为本地 `qwen3-vl:4b-instruct-q4_K_M`）。

### 1.4 可复用的真实资产

| 资产 | 规格 | 说明 |
|---|---|---|
| `docs/examples/<styleId>/reference.png` | 1024×1024 | 用户上传的参考图 |
| `docs/examples/<styleId>/generated.png` | 1024×1024 | Qwen Image 3.0 真实生成结果 |
| `docs/examples/<styleId>/culture_card.png` | 1080×1440 | 已导出的文化卡（3:4） |
| `docs/examples/<styleId>/metadata.json` | — | 标题、风格强度、生成时间、文化说明 |

五件案例：

| styleId | 作品 | 风格强度 | 生成时间 |
|---|---|---|---|
| `zhuxianzhen` | 瑞猫迎春 | 1.00 | 2026-10-08 |
| `bianxiu` | 绣兔牡丹 | 1.00 | 2026-10-08 |
| `songhua` | 云鹤临水楼 | 0.65 | 2026-09-30 |
| `qinghua` | 青花蝶韵 | 0.65 | 2026-10-08 |
| `jianzhi` | 剪影灵狐 | 0.65 | 2026-10-08 |

`frontend/src/data/savedCases.ts`（23 行）通过
`import.meta.glob('../../../docs/examples/*/*.png', { eager: true, query: '?url' })`
把六类图片地址注入，因此**构建产物自带图片，不依赖后端**。

### 1.5 设计 token（沿用）

```css
--color-primary: #9E241B;   --color-primary-dark: #7A1712;
--color-gold:    #D2A14A;   --color-paper: #F8EEDC;
--color-ink:     #3F2B1F;   --color-border-red: #B8422E;
```

已有类：`.chinese-border`、`.chinese-plaque`、`.btn-chinese`、`.bg-rice-paper`、
噪点纹理 body、Noto Serif SC / Noto Sans SC。
→ **新页面直接吃这些 token，不另起一套视觉**。

---

## 2. 缺口清单

| 缺口 | 严重度 | 说明 |
|---|---|---|
| **没有热点坐标** | 阻断 | `metadata.json` 里**没有 bbox / 关键点 / 分割掩码**，任何互动都要先造坐标 |
| 没有互动数据结构 | 阻断 | 无 `Experience` 概念，`savedCases` 只是展示用 |
| 没有文化来源库 | 高 | 文化解读只存在于 `visionAnalysis` 的自由文本里，不可点开、不可核对 |
| 没有分层素材 | 中 | 若做视差必须先造图 |
| 没有测试 | 中 | 仓库当时无任何前端单测 |
| 没有 `@types/react` | 低 | 类型宽松，但不影响运行 |
| `npx` 不可用 | 低 | PowerShell 执行策略拦截 `.ps1` 签名 |

### 关键判断：坐标必须自己造，且必须可审计

既然没有真值，就有两种坏做法和一种好做法：

- ❌ 让视觉模型直接给框 → 实测误差 0.1–0.2 归一化，等于乱标；
- ❌ 按「大概位置」手写 → 看起来像真的，但经不起放大检查；
- ✅ **候选格 + 人工定坐标 + 裁切复核**：模型只做十选一（判断中心落在哪个格子），
  坐标由工程换算，再用同一模型对「裁好的小图」做二次确认，最后用 IoU 查重叠。

这套流程的产物必须**在数据里留下痕迹**：`locationStatus: verified | approximate | unverified`
与 `provenance.hotspotMethod`，让后来的人知道每个框是怎么来的。

---

## 3. 复用与不动清单

### 3.1 直接复用

- `savedCases.ts` / `loadSavedCase()`：互动数据反向读取它取图片地址；
- `/products` 文创预览：仍然靠 `wenmai_latest_result`，不改；
- Tailwind token 与既有字体；
- `motion` 已在依赖里，`AnimatePresence` / `useReducedMotion` 直接用。

### 3.2 绝对不动

- `backend/**`（本轮零改动，`git status` 可证）；
- `frontend/src/pages/AICreator.tsx`（677 行，生成工作台）；
- `frontend/src/pages/ProductStudio.tsx`（576 行）；
- `frontend/src/data/savedCases.ts`；
- 五件真实案例的图片（**不重新生成**，不产生任何付费调用）。

### 3.3 需要改动但要保住能力的

`frontend/src/pages/Gallery.tsx`（原 20 行）将被改写为展厅。
**约束**：参考图 / 成图 / 文化卡 / 「文创预览与下载」/「查看保存的工作台记录」
五个既有入口一个都不能少，只是排布与层级重排。

---

## 4. 风险与对策

| 风险 | 对策 |
|---|---|
| 换分辨率后热点漂移 | 用 `object-fit: contain` 的真实绘制区做基准，ResizeObserver 重算 |
| 热点坐标经不起放大检查 | 逐点裁切复核，未通过一律降级 `approximate`，界面显示位置状态 |
| 为了「炫」加自动运镜，用户失去控制 | 硬性规定：画面永不自动移动；所有镜头变化由用户动作或滚动位置触发 |
| 文案吹大（馆藏、排名、非遗身份） | 来源库 + 测试断言禁止词；非非遗品类不称非遗 |
| 把 2.5D 说成三维重建 | 文案与文档统一口径「图像分层 + 羽化遮罩，非三维重建」 |
| 新依赖带来许可/体积问题 | 已调研：本轮零新增依赖 |
| 改坏既有页面 | 只改 `Gallery`/`Home`/`App`/`index.css`，其余只读 |

---

## 5. 审计结论

1. **可以做**，且不需要新依赖、不需要新模型、不需要后端配合；
2. **最难的不是 UI，是坐标与来源**——这两件事决定了它是「真互动」还是「假互动」；
3. 优先级判断：S1（单图逐处探索）收益最大，因为它把「看不懂的生成图」变成「能读的画」；
4. S3 必须控制成本，先做一件验证可行性，不追求全覆盖；
5. 本轮**不做**任何远端同步、不改项目路径、不碰其他项目。