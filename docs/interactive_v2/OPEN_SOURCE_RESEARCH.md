# 开源仓库调研 · 交互式文化体验 v2

> 调研分支：`feat/interactive-v2`　调研时间：2026-10-20　调研员：research-scout
> 所有星数/许可证/体积均为**本次实测**（GitHub REST API + npm registry + 实读 README），非记忆值。
> 本文只做调研，不含代码改动。

---

## 0. 结论摘要（TL;DR）

| 结论 | 内容 |
|---|---|
| **新增依赖** | **无。** 现有 React 19 + `motion` 12 + `react-router-dom` 7 + Tailwind 4 足以覆盖 P0/P1 |
| 唯一"值得未来买票"的 | `three` + `@react-three/fiber`（仅 S4 球体，且不阻塞 S1–S3） |
| 明确不用 | GSAP（许可证非开源、与 motion 重复）、Depth Anything V2（需 PyTorch + 权重） |
| 明确不用（改自实现） | `react-compare-slider`（不是体积问题，是 pointer 交互耦合问题） |
| 只借鉴思路、不复制代码 | `lunaark/yuelu-museum`、`cynthiachiu/3D-Art-Gallery` |
| 许可证红线 | **`3D-Art-Gallery` README 自称 MIT，但仓库里没有 LICENSE 文件** → 视为无授权 |

---

## 1. 逐仓库核验表

数据来源：[GitHub REST API `get a repository`](https://docs.github.com/en/rest/repos/repos#get-a-repository)（`stargazers_count` / `license.spdx_id` / `pushed_at`）+ npm registry `/latest`。

| 仓库 | 星数 | 许可证（实测） | 最近推送 | 语言 | npm 包 unpacked |
|---|---:|---|---|---|---:|
| [pmndrs/react-three-fiber](https://github.com/pmndrs/react-three-fiber) | 33,095 | **MIT**（API `spdx_id=MIT`） | 2026-10-17 | TypeScript | 2,343 KB |
| [mrdoob/three.js](https://github.com/mrdoob/three.js) | 116,648 | **MIT** | 2026-10-20 | JavaScript | 19,964 KB |
| [nerdyman/react-compare-slider](https://github.com/nerdyman/react-compare-slider) | 382 | **MIT** | 2026-09-30 | TypeScript | 151 KB |
| [greensock/GSAP](https://github.com/greensock/GSAP) | 29,512 | **非开源**：仓库无 LICENSE 文件，许可证为 Webflow "Standard No Charge License" | 2026-04-13 | JavaScript | 6,111 KB |
| [motiondivision/motion](https://github.com/motiondivision/motion) | 34,373 | **MIT**（README 明文 "Motion is MIT licensed."） | 2026-10-20 | TypeScript | 857 KB |
| [DepthAnything/Depth-Anything-V2](https://github.com/DepthAnything/Depth-Anything-V2) | 8,999 | **仓库 Apache-2.0；模型分 license**（见 §5） | 2026-03-24 | Python | — |
| [lunaark/yuelu-museum](https://github.com/lunaark/yuelu-museum) | 6 | **MIT** | 2026-05-24 | TypeScript | — |
| [cynthiachiu/3D-Art-Gallery](https://github.com/cynthiachiu/3D-Art-Gallery) | 42 | **未核验 / 声明不完整**（README 称 MIT，但无 LICENSE 文件） | 2022-05-07 | JavaScript | — |

> 星数会漂移，本表是 2026-10-20 快照。许可证一栏以**实际读到的文本**为准，不以"大家都说它是 MIT"为准。

---

## 2. three.js 与 react-three-fiber

### 2.1 three.js

- **用途**：WebGL / WebGPU 通用 3D 库，`SVG` 与 `CSS3D` 渲染器作为 addon 提供（README 原文）。
- **许可证**：MIT（API 实测 + 仓库有 `LICENSE`，最近一次改动是 2026-01-03 "Update copyright year"）。
- **可借鉴能力**：`SphereGeometry` 的 UV 映射、`PerspectiveCamera` / `OrthographicCamera`、`Raycaster` 拾取、`TextureLoader`。
- **体积**：npm 包 unpacked **19,964 KB**。⚠️ 这是**含 `examples/`、`docs/` 的整包体积，不是打进 bundle 的体积**；
  实际 bundle 只含 tree-shake 后的子集，**本报告未实测 gzip 后体积**（不编数字）。
- **建议**：**仅在 S4 立项时引入**，且必须与 S1–S3 解耦（见 `S4_TINY_PLANET_RESEARCH.md`）。

### 2.2 react-three-fiber（r3f）

- **用途**：Three.js 的 React renderer，用 JSX 声明场景。
- **许可证**：MIT。
- **React 19 兼容性 —— 这是关键的一条**：
  - README 原文明写：**"`@react-three/fiber@8` pairs with `react@18`, `@react-three/fiber@9` pairs with `react@19`."**
  - npm `@react-three/fiber@9.8.2` 的 `peerDependencies`：`"react": ">=19 <19.4"`、`"three": ">=0.156"`。
  - 本项目实测 `react@19.2.5` → **落在 `>=19 <19.4` 区间内，可装**。
  - ⚠️ 但 **React 19.4 一旦发布，r3f 9 会被 peer 卡住**，升级 React 前必须先看 r3f 版本。这是长期风险，写进 §9。
- **依赖树成本**：r3f 自带 13 个运行时依赖（`zustand`、`scheduler`、`its-fine`、`react-use-measure`、`suspend-react` 等），不是"加一个包"，是"加一层"。
- **建议**：**仅参考 + 未来 S4 可选**。若 S4 只做一个球 + 五个热点，**原生 three.js 更省**（见 S4 §4）。
- **SSR 风险**：`Canvas` 依赖 `window`/`document`，SSR 下必须动态导入。本项目是 Vite SPA，**当前无 SSR**，风险为 0；但若将来上静态预渲染需注意。

---

## 3. react-compare-slider：是否值得新增依赖？

### 3.1 事实核对

| 项 | 实测值 |
|---|---|
| 星数 / 许可证 | 382 / **MIT** |
| 版本 | `4.0.0`（仓库最后一次 `chore: release v4.0.0` 在 2026-03-20） |
| `peerDependencies` | `react >=16.8`、`react-dom >=16.8` → **不挡 React 19** |
| `dependencies` | **空**（零运行时依赖） |
| `sideEffects` | `false`（可 tree-shake） |
| unpacked | 151 KB |
| README 声称 | 响应式、支持横竖屏、**开箱即用的屏幕阅读器与键盘支持**、`prefers-reduced-motion` 下自动关过渡、零依赖 |

结论：**这是一个小而体面的包，质量没有硬伤。** 所以"不引入"的理由**不能是体积**。

### 3.2 推荐结论

> **推荐：不引入，用原生 pointer 事件 + `clip-path` 自实现。**
> 但若 P1 排期吃紧，允许把它作为 fallback，并**锁定 `4.0.0` 精确版本**（不用 `^`）。

### 3.3 理由（按权重排序）

1. **交互耦合，不是功能缺失。**
   我们的对比滑杆要活在**已经有一层热点（pointer 点击）**的画面上。
   两层 pointer 语义叠在一起时，`onlyHandleDraggable` 只能"缓解"，不能"表达我们的意图"
   （例如：在滑杆左侧拖动应移动滑杆，还是应拖动视差层？）。自实现时这个判定由我们写，一行 `if` 就定了。
2. **复用度低。**
   我们真正需要的不是"两图对比"，而是"**在一张有热点的图上，用一条可变的分割线露出另一张图**"。
   包提供的是前者，后者仍要自己写 `clip-path` 与热点坐标对齐——即**包只省了 20 行，却多了一层 API 心智**。
3. **`clip` 选项暗示了复杂度。**
   v4 的 `clip: all | itemOne | itemTwo` 是为了适配"被裁剪层上还要放内容"的场景；
   一旦我们要在裁剪层内放热点，就得同时理解包的裁剪模型和我们的坐标模型。自实现只有一个坐标模型。
4. **自实现成本可控且可测。**
   `clip-path: inset(0 calc(100% - var(--pos)) 0 0)` + `pointerdown/move/up` + `setPointerCapture`，
   约 60–80 行，含键盘（←/→ 改 `--pos`）与 `prefers-reduced-motion`。
5. **可访问性我们自己更清楚。**
   包的 a11y 是"通用最优"；我们的场景需要"滑杆 + 热点 + 说明文字"三者焦点顺序统一编排，包帮不上。

### 3.4 什么时候应该改用这个包

- 需要**竖屏对比**、**自定义 handle 插画**、**iframe 内嵌事件绑定**（`browsingContext`）等边缘场景；
- 或者团队里没人愿意写 80 行 pointer 逻辑。
- 此时引入是**合理工程决策**，不是错误——只是本次不划算。

---

## 4. motion（已在依赖中）：怎么做滚动章节与共享布局动画

### 4.1 现状

| 项 | 值 | 证据 |
|---|---|---|
| `package.json` 声明 | `"motion": "^12.23.24"` | [`frontend/package.json`](../../frontend/package.json) |
| 实际安装 | **12.38.0** | `frontend/node_modules/motion/package.json` |
| 最新版 | 14.4.0 | npm registry |
| 许可证 | MIT | README |
| `peerDependencies` | `react: ^18.0.0 || ^19.0.0` | npm registry |
| 内部依赖 | `framer-motion@14.4.0`（v14 起把 framer-motion 收编为内部依赖） | npm registry |

> ⚠️ **不要顺手 `npm update motion`**。v12 → v14 跨两个大版本，本项目锁定 `^12` 是有意的；
> 升级需要单独一轮回归（`useScroll` 的 offset 语义、`layout` 动画的测量时机都变过）。

### 4.2 滚动章节（scroll narrative）推荐写法

用 **`useScroll` + `useTransform`**（滚动位置 → 数值），**不要**用 `whileInView` 做"章节推进"。
区别：前者是**连续映射**（读者滚到哪，画面到哪），后者是**离散触发**（进视口就播一次）。

```tsx
// 示意，非最终实现
const ref = useRef<HTMLDivElement>(null)
const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] })
const scale   = useTransform(scrollYProgress, [0, 0.33, 0.66, 1], [1, 1.35, 1.1, 1])
const opacity = useTransform(scrollYProgress, [0, 0.1, 0.9, 1], [0, 1, 1, 0])
```

要点：
- `offset: ['start start', 'end end']` 让进度严格绑定该章节容器，**不劫持全局滚动**；
- 章节容器用 `height: 300vh`，内容 `position: sticky; top: 0`——滚动是原生的，动画只是跟读；
- `prefers-reduced-motion`：用 `useReducedMotion()` 返回 `true` 时**直接把 `scale` 换成常量 1**，不要"缩短动画时长"。

### 4.3 共享布局动画（shared layout）

从 `/gallery` 卡片点进 `/experience/:id`，用 **`layoutId`** 做"卡片 → 故事页大图"的连续变形：

```tsx
// 列表页
<motion.img layoutId={`work-${work.styleId}`} src={work.imageUrl} />
// 详情页
<motion.img layoutId={`work-${work.styleId}`} src={work.imageUrl} />
```

要点：
- 两个路由必须**同时在动画期间挂载**（`AnimatePresence` + `mode="popLayout"` 或 `wait`），否则无法接力；
- 图片用同一 `src` 与同一 `objectFit`，否则会看到"跳裁切"；
- `layoutId` 只对**同一棵 React 树**有效；`react-router` 切换路由会卸载，需把 `AnimatePresence` 提到路由外层（`MainLayout`）。

### 4.4 信息层（热点弹层）推荐写法

- 桌面：`AnimatePresence` + 侧栏 `initial={{x: 24, opacity: 0}}`；
- 移动：底部抽屉 `initial={{y: '100%'}}`，并加 `drag="y"` + `dragConstraints`，下滑关闭；
- **必须有**：`Esc` 关闭、遮罩点击关闭、关闭后焦点回到触发的热点按钮；
- `layout` 动画期间不要同时跑 `useScroll` 的变换，会掉帧。

---

## 5. Depth Anything V2 Small

### 5.1 事实

| 项 | 实测/原文 |
|---|---|
| 仓库星数 | 8,999（NeurIPS 2024） |
| 仓库许可证 | Apache-2.0 |
| **模型许可证（关键）** | README 原文：**"Depth-Anything-V2-Small model is under the Apache-2.0 license. Depth-Anything-V2-Base/Large/Giant models are under the CC-BY-NC-4.0 license."** |
| Small 参数量 | **24.8 M**（README 表格） |
| 推理依赖 | `torch`（README 代码 `import torch`）、`cv2`、`numpy`；`DEVICE = cuda / mps / cpu` |
| 权重体积 | **未核验**。本机访问 `huggingface.co` 的 API 与 HEAD 请求**均超时**，拿不到 `Content-Length`。按 24.8M 参数 × 4 字节（fp32）**估算约 99 MB**，此为估算值 |
| 输入尺寸 | 默认 `518`（`--input-size` 可调） |

> **不要**把 Base/Large 的 CC-BY-NC-4.0 说成"也是 Apache-2.0"。**只有 Small 是 Apache-2.0。**
> 对参赛/商用项目，这个区别是硬约束；Small 是唯一可放心商用的档位。

### 5.2 结论：不引入

理由（按权重）：

1. **重量级运行时。** 要 PyTorch + 权重下载，与"`npm run dev` 一条命令起站、可离线展演"的现状冲突。
2. **权重拿不到。** 本机 `huggingface.co` 不可达（本次两次探测均超时），连体积都无法确认，更谈不上离线打包。
3. **收益不匹配。** 深度图是为了做"像素级 2.5D 位移"。但我们的作品是**平面纹样类图像**（木版年画、青花、剪纸、刺绣、松花石），
   深度信息本来就弱——强行做深度视差，会产生"整张图在飘"的廉价感，反而不如**人工分层**准确。
4. **法律与合规。** 权重来源、训练数据、NC 条款解释，都是比赛答辩上说不清的负担。

### 5.3 替代方案（纯前端，零依赖）

| 方案 | 做法 | 效果 | 成本 |
|---|---|---|---|
| **人工分层**（推荐） | 在 Figma/PS 里把作品拆成"背景 / 主体 / 前景"2–3 层 PNG（带透明通道），逐层 `translate3d` | 最接近 B 视频的"照片→交互页"观感，且可控 | 每件作品 20–30 分钟人工 |
| **径向渐变遮罩** | 一张图 + `radial-gradient` 遮罩模拟"中心清晰、边缘后退" | 适合做"镜头推进"时的景深暗示 | 纯 CSS，0 成本 |
| **模糊分层** | 同一张图复制两层，一层 `blur(6px)` 放大 1.05 倍，指针移动时两层错位 | 伪景深，代价极小 | 纯 CSS |
| **不做** | 只做热点 + 热点处 `scale` 放大 | 最稳 | 0 |

> 推荐组合：**热点（P0）+ 人工分层视差（P1）+ 径向渐变遮罩（P1）**。深度模型在这个组合里没有位置。

---

## 6. 数字展厅仓库：只借信息架构，不复制代码

### 6.1 lunaark/yuelu-museum（华夏文物数字展厅）

- **事实**：MIT，TypeScript，6 星，创建于 2026-05-24（很新）。README：React + Vite + Three.js（`@react-three/fiber` / `drei`），
  收录 8 件文物（商代至明清），每件有"可交互 3D 模型 + 分部件细节解说 + 文物故事 + '你可能好奇'问答"。
- **可以借的（信息架构）**：

  | 它的做法 | 我们能借什么 |
  |---|---|
  | 8 件文物按**年代排序**成一条线 | 我们的 5 件作品按**工艺类型**排序（年画→刺绣→剪纸→青花→松花石），也可做一条"工艺谱系" |
  | **分部件解说**（点模型某部位出解释） | 直接对应我们的"点击热点看文化解释"——它验证了这个 IA 是成立的 |
  | **文物故事**（叙事段落） | 对应我们的"独立互动故事页" |
  | **"你可能好奇"问答** | 低成本高感知：3–4 个 Q&A 折叠块，内容可直接取自 `metadata.json` 的 `culture_interpretation` 与 `visual_features` |

- **不能借的**：
  - **代码**：它是 three.js/r3f 技术栈，我们是纯 DOM，抄不动；
  - **素材**：README 明写"所有 3D 模型来自 Sketchfab，遵循各自的 CC 协议"——**它的模型不是 MIT**，
    即便代码是 MIT，模型也**不可复制**。这一点必须写进交付说明。
  - **体量**：仓库 163 MB（API `size`），基本是模型资产，不是代码。
- **建议**：**仅参考 IA**。不 clone、不引入。

### 6.2 cynthiachiu/3D-Art-Gallery

- **事实**：42 星，**2022-05-07 最后推送**（已停更 3 年+），JavaScript，React-Three-Fiber + drei + postprocessing，
  功能为"3D 渲染画作 + 移动聚光灯 + 平滑横向滚动 + 鼠标交互 + 阴影 + 后期噪点"。
- **⚠️ 许可证重大问题**：
  - README 的 License 段落写：**"This project is under license from MIT. For more details, see the LICENSE file."**
  - **但仓库文件列表里没有 `LICENSE` 文件**（只有 `public/`、`src/`、`README.md`、`demo.gif`、`package.json`、`package-lock.json`）。
  - GitHub REST API 的 `license` 字段为 **`null`**。
  - → **结论：许可证"未核验"。README 的自我声明 ≠ 有效的开源授权。不得引用其代码。**
- **可以借的（仅思路）**：
  - "**聚光灯跟随当前作品**" → 我们可以用 CSS `radial-gradient` 做一束跟随指针的光，制造"打光看纹样"的暗示（P2）；
  - "横向滚动浏览作品墙" → 与我们的 `/gallery` 布局同构，可参考其节奏而非实现。
- **不能借的**：
  - 代码（许可证不明）；
  - 后期噪点/Bloom（与"不堆特效"冲突）；
  - 其技术栈（2022 年的 CRA + 老版 r3f，React 版本不兼容 React 19）。
- **建议**：**仅参考思路**，且明确写"该仓库无 LICENSE 文件，不可复制代码"。

---

## 7. GSAP：为什么不用

- **事实**：29,512 星；**仓库根目录没有 `LICENSE` 文件**。实读文件列表为 `dist/`、`esm/`、`src/`、`types/`、`.gitignore`、`README.md`、`SECURITY.md`、`package.json`，不含 `LICENSE`；GitHub API 的 `license` 字段为 **`null`**。README 的 License 段落只给了外链 `https://gsap.com/standard-license`。
- **真实许可证**：Webflow 的 **Standard "No Charge" GSAP License**（`gsap.com/standard-license`，生效 2025-04-30）。实读要点：
  - 允许商业使用、允许 AI 生成 GSAP 代码（FAQ 明确）；
  - **禁止** "Prohibited Uses"：把 GSAP 用于"让用户无需写代码即可搭建动画的可视化工具"（即与 Webflow 的可视化建站能力竞争）；
  - 不得移除版权/品牌标识；Webflow 可随时终止授权。
- **npm 的 `license` 字段**实测为：`Standard 'no charge' license: https://gsap.com/standard-license.` —— 与 MIT 无关。
- **结论：不用。** 三条理由：
  1. **许可证不是 OSI 开源**，比赛材料里写"使用开源库"会被追问；走法务确认不值得；
  2. **功能重叠**：项目已有 `motion@12`（`useScroll` / `layoutId` / `AnimatePresence` 全覆盖 P0/P1 需求），
     引入 GSAP = 维护两套动画时间线 + 两套 DOM 写入，**必然打架**（GSAP 直接改 `style`，motion 用 `transform` 合成，两者会互相覆盖）；
  3. **体积**：unpacked 6,111 KB，是 `motion` 的 7 倍，换不来本项目需要的任何独有能力。
- **唯一值得"偷师"的**：`ScrollTrigger` 的**pin + scrub** 思路（章节钉住、进度跟读）——这个我们已用 `useScroll` + `position: sticky` 实现，**不需要装它**。

---

## 8. 依赖决策表

### 8.1 最终决策

| 仓库/包 | 决策 | 理由一句话 |
|---|---|---|
| `three` | **不引入**（S4 立项前） | 仅球体需要；S4 不得影响 S1–S3 |
| `@react-three/fiber` | **不引入**；将来若上 S4，优先考虑原生 three | 多 13 个传递依赖；且 peer 卡 `react <19.4` |
| `@react-three/drei` | **不引入** | 1,713 KB，本次用不到其 helpers |
| `react-compare-slider` | **不引入**，自实现 `clip-path` 滑杆 | 与热点 pointer 语义耦合；包本身无质量问题 |
| `gsap` | **不引入** | 非开源许可；与 motion 功能重叠且会互相覆盖 |
| `motion` | **已在依赖中**，继续用（锁 `^12`，不升级） | 覆盖滚动章节、共享布局、弹层、手势 |
| Depth Anything V2 | **不引入** | 需 PyTorch + 权重；HF 本机不可达；收益不匹配平面纹样 |
| `yuelu-museum` | **仅参考 IA**，零代码引入 | 技术栈不同；其 3D 模型为 Sketchfab 各自 CC，不可复制 |
| `3D-Art-Gallery` | **仅参考思路**，零代码引入 | **无 LICENSE 文件，授权未核验** |

### 8.2 一句话结论

> **新增依赖 = 无。**
> 本轮所有 P0/P1 需求在 `react@19.2.5 + motion@12.38.0 + react-router-dom@7` 内可完成。
> 唯一未来选项是 S4 的 `three`（或 r3f），且必须独立立项、独立验收。

---

## 9. 使用风险汇总

| 风险 | 影响 | 缓解 |
|---|---|---|
| `motion` v12 → v14 大版本漂移 | `useScroll` offset 语义变化会导致章节错位 | 锁 `^12.23.24`；**不执行** `npm update motion` |
| r3f 9 的 peer 上限 `react <19.4` | 将来升 React 会装不上 | 升 React 前先查 r3f peer；或直接用原生 three |
| `three` 包 unpacked 19.9 MB | 若误 `import * as THREE` 全量引入，bundle 膨胀 | 只 import 需要的符号；构建后看 gzip 体积 |
| SSR | r3f/Canvas 依赖 `window` | 当前 Vite SPA 无 SSR；若改预渲染需 `React.lazy` + `dynamic import` |
| GSAP 许可证 | 比赛材料合规风险 | 不引入 |
| `3D-Art-Gallery` 无 LICENSE | 复制代码 = 侵权风险 | 只读思路，零代码引入 |
| `yuelu-museum` 模型资产 | 其 README 明示模型各自 CC | 只借 IA，不碰素材 |
| 抖音参考视频不可访问 | "照视频还原"无从谈起 | 见 `VIDEO_REFERENCE_ANALYSIS.md` §1 |

---

## 附录：本次核验的可复现命令

```powershell
# 星数 / 许可证 / 活跃度
Invoke-RestMethod "https://api.github.com/repos/pmndrs/react-three-fiber" |
  Select-Object stargazers_count, pushed_at, @{n='lic';e={$_.license.spdx_id}}

# 体积 / peerDeps（判断 React 19 兼容性）
Invoke-RestMethod "https://registry.npmjs.org/react-compare-slider/latest" |
  Select-Object version, license, @{n='unpackedKB';e={[math]::Round($_.dist.unpackedSize/1KB)}}
```

四条 npm 实测值：`three@0.186.1` 19,964 KB / `@react-three/fiber@9.8.2` 2,343 KB /
`react-compare-slider@4.0.0` 151 KB / `motion@14.4.0` 857 KB / `gsap@3.15.0` 6,111 KB。

---

*本文件为调研报告，未修改任何代码，未安装任何依赖。*