# 最终验收报告 · 纹脉华章 2.0「一卷五境」

> 本地分支：**`feat/interactive-v2`**（仅本地，未推送）
> 验收时间：2026-10-20 18:50　验收人：本项目 Lead
> **未执行任何 GitHub 远程同步操作**：没有 `git push`、没有 PR、没有 GitHub Pages / Release 更新、
> 没有远程仓库同步，也没有改动项目路径。

---

## 1. 交付范围

| 阶段 | 交付 | 状态 |
|---|---|---|
| S0 | 现状审计 `S0_AUDIT.md` | 完成 |
| S1 | 「画中有话」`/experience/:id`，5 件作品 / 25 处线索 | 完成 |
| S2 | 「一图一境」`/story/:id`，5 件作品 / 15 折 | 完成 |
| S3 | 「画境漫游」`/wander/:id`，1 件作品 / 3 层视差 | 部分完成（按计划） |
| S4 | 「纹脉星球」调研 `S4_TINY_PLANET_RESEARCH.md` | 仅调研，未实现 |
| 贯穿 | 展厅改写、首页入口、文化知识库、运行时校验、单测、实机验收 | 完成 |

文档 9 篇（含本篇）、截图 6 张、单元测试 3 个文件 32 个用例。

---

## 2. 验证矩阵（逐项实测，非声明）

### 2.1 构建与类型

```
node node_modules\typescript\bin\tsc --noEmit   → exit 0
node --test "tests/*.test.ts"                   → tests 32 / pass 32 / fail 0
```

### 2.2 后端（只读检查）

```
GET http://127.0.0.1:8000/health → status=ok
  字段：provider, generationProvider, model, allowMockFallback, providers,
        styleRefsReady, styleRefsMissing, outputsDir, styleRefsDir,
        visionProvider, localVisionAnalysis, message
```

**偏离说明（重要）**：仓库 `AGENTS.md` §10 要求验证顺序为
`/health → /generate → npm run dev → 浏览器`。本轮**没有调用 `/generate`**，
原因：`/generate` 会触发 Qwen Image 付费出图，而本轮的硬约束是「不产生付费 AI 调用」。
替代证据：

1. 本轮互动体验（S0–S3）**没有改动任何后端代码**，既有链路未被触碰；
   （后续追加的「生成结果自动沉淀」功能改了 `backend/`，见 §8，与互动体验无关）
2. 三张互动路由**完全不请求**后端（实测资源清单里 `:8000` 请求数为 **0**）；
3. 五件作品使用仓库内已有的真实生成图，无需重新生成；
4. 停止后端进程后，互动页仍完整可用（见 2.5）。

### 2.3 路由与页面

| 路由 | 结果 |
|---|---|
| `/` | 「进入画里，再看一遍」三卡入口存在，三张卡图片 `naturalWidth` = 1254 / 1536 / 1536 |
| `/gallery` | 5 张作品卡；每卡 3 个互动 CTA；`文创预览与下载`、`展开文化卡`、`id=case-*` 全部保留 |
| `/experience/{zhuxianzhen,bianxiu,songhua,qinghua,jianzhi}` | 5/5 打开，热点 6/5/6/4/4 |
| `/story/{同上}` | 5/5 打开，各 3 折 |
| `/wander/songhua-yunhe` | 3 层 WebP 全部加载（1024×1024） |
| `/experience/not-exist` `/story/not-exist` `/wander/not-exist` | 友好兜底文案 + 返回展厅 |
| `/wander/zhuxianzhen-ruimao`（无分层） | 「这一卷还没有可漫游的分层素材」 |

客户端路由（`pushState` + `popstate`）连续切换 **14 次**：`console.error` / `error` / `unhandledrejection` 计数 **0**，
`#root` 始终有内容，无 `vite-error-overlay`。

### 2.4 交互实测

**S1**

- 点击第 1 处 → 面板标题「猫的脸部」，出现「画面观察」「文化解读」两段 + 2 条来源链接 + 故事深链；
- `aria-live` 播报「第 1 处线索：…」；
- `→` 切下一处、`←` 上一处、`4` 直达第 4 处、`Escape` 收起；
- `+` 缩放 → `scale(1.5)`、工具栏读数 `150%`；`0` 复位 → `translate(0%, 0%) scale(1)`；
- 双击定点放大 + 放大后拖动平移，边界夹紧；
- 键盘 `Tab` 能进入 6 个圆点（`tabIndex=0`，`role=button`，有 `:focus-visible` 双环）。

**S2**

- 滚动到第 3 折：镜头 `translate(10.8%, 13.5%) scale(1.35)` → `translate(-8.75%, -8.75%) scale(1.75)`；
- 进度点第 3 个变主题色 `rgb(66, 108, 98)`，前两个为 15% 墨色；
- 390×844 下粘性画面 253×253、`top=64`，标签随折变化。

**S3**

- 指针移动：`rotateX(0deg) rotateY(0deg)` → `rotateX(2.1deg) rotateY(3.5deg)`；
- 三层变换：`translateZ(-32.2px) scale(1.023)` / `(+4.6px, 0.996714)` / `(+46px, 0.967143)`；
- 关闭视差后与原始 `generated.png` 逐像素比对：`mean 5.79`、`p95 25`，
  衔接带（0.53–0.60）为 6.1/7.8，**无重影、无接缝**（修正前同测法为 127–145）。

### 2.5 离线与降级

- 页面资源来源：`127.0.0.1:5173` 77 个、字体 CDN 55 个、**`:8000` 0 个**；
- 杀掉后端进程后重新加载 `/experience/zhuxianzhen-ruimao`：6 个热点、解读文案、来源、故事深链全部正常；
- 恢复后端后 `/health` 再次 `status=ok`。

### 2.6 响应式（4 尺寸 × 4 页面 = 16 组）

| 尺寸 | 横向滚动 | 报错 | 关键指标 |
|---|---|---|---|
| 1366×768 | 无 | 无 | 展厅 5 卡；画面 438px 且首屏完整；故事 3 折；漫游 3 层 |
| 1440×900 | 无 | 无 | 画面 570px；其余同上 |
| 1920×1080 | 无 | 无 | 画面 720px（封顶）；其余同上 |
| 390×844 | 无 | 无 | 展厅卡 358px；画面 336px；故事粘性画面生效；漫游 358px |

**无小于 10px 的文字**（唯一 10px 的是「1024×1024」尺寸标注，属辅助信息）。

### 2.7 数据完整性

- 11 条来源全部被引用，**无孤立来源**；
- 25 处热点几何全部在 0–1；
- 每件作品 4–6 处热点、3 折章节，`index` 连续；
- 禁用词断言通过（御窑孤品 / 四大年画之首 / 博物院珍藏 / 故宫珍藏 / 国家一级文物 / 唯一传世 / 世界第一）；
- 非非遗品类（宋画、青花瓷）未自称非遗；
- 未出现「激光切割 / 数码印花 / 机器刺绣 / 印刷仿制」；
- 分层素材均为 `.webp`，`depth` 与 `mask` 字段合法。

---

## 3. 本轮改动清单

### 3.1 修改（6 个）

| 文件 | 改动 |
|---|---|
| `frontend/src/App.tsx` | 注册 `/experience/:id`、`/story/:id`、`/wander/:id` |
| `frontend/src/pages/Gallery.tsx` | 改写为「文化作品展厅」，新增参考/成图对照与 3 个互动入口，保留全部既有能力 |
| `frontend/src/pages/Home.tsx` | 新增「进入画里，再看一遍」三卡入口 |
| `frontend/src/index.css` | 新增 `.hotspot-chip:focus-visible`、`.exp-eyebrow`、`prefers-reduced-motion` 块 |
| `frontend/package.json` | 新增 `zod` 依赖、`test` 脚本（`node --test`） |
| `frontend/package-lock.json` | 随依赖变动 |

### 3.2 新增（按目录）

| 目录 / 文件 | 数量 | 内容 |
|---|---|---|
| `frontend/src/pages/{Experience,Story,Wander}.tsx` | 3 | 三条路由页面（30 / 397 / 334 行） |
| `frontend/src/features/culture-experience/**` | 12 | 类型、Zod schema、几何工具、Viewer、热点层、知识面板、工具栏、对照滑块、来源胶囊、错误边界、contain 钩子、资源前缀 |
| `frontend/src/data/experiences/**` | 6 | 5 件作品数据 + 注册表 |
| `frontend/tests/**` | 3 | 32 个用例：几何 13 / schema 10 / 数据完整性 9 |
| `frontend/public/interactive/songhua/*.webp` | 3 | 分层素材（89 / 177 / 164 KB） |
| `culture_knowledge/**` | 7 | `sources.json`（11 条）+ 5 件作品要点 + README |
| `docs/interactive_v2/**` | 9 篇文档 + 6 张截图 | 见下 |
| `scripts/interactive/{look.py,make_layers.py}` | 2 | 本机视觉复核脚本；分层生成脚本 |

### 3.3 未改动（明确保证）

`frontend/src/pages/ProductStudio.tsx`、`docs/examples/**` 中五件真实案例的图片与 metadata（未重新生成、未覆盖）。

> `frontend/src/pages/AICreator.tsx`、`frontend/src/data/savedCases.ts` 与 `backend/` 在后续的
> 「生成结果自动沉淀」中做了**增量修改**（不改既有行为），见 §8。

---

## 4. 与约束的逐条对照

| 约束 | 执行情况 |
|---|---|
| 不破坏 `/creator` `/gallery` `/products` 与既有生成 API | 互动部分零后端改动；自动保存为纯增量（失败不影响出图）；Gallery 保留全部入口；`/products` 动线不变 |
| 不 `git push` / 不 `--force` / 不发 PR / 不动 Pages、Release | **全程未执行** |
| 不做远程同步、不改项目路径、不碰其他项目 | 遵守 |
| 不产生付费 AI 调用 | 未调用 `/generate`、未调用任何付费出图；视觉复核用本机 Ollama |
| 不下载大模型 | 未下载任何权重（Depth Anything V2 曾尝试获取元数据，未落盘权重） |
| 不覆盖未提交的工作 | 只新增文件与定向编辑；未 `reset --hard`、未 `clean` |
| 不伪造互动 | 所有热点都有真实坐标与裁切复核记录，2 处标注 `approximate` |
| 不虚构馆藏 / 文物 / NIHC 关系 | 来源库仅收可点开的机构页面；禁用词有测试断言 |
| 不宣称看过无法访问的视频 | `VIDEO_REFERENCE_ANALYSIS.md` 明确记录 0 帧可用画面 |
| 实机跑起来并点击验证 | 前后端真实启动，浏览器实测（见 §2） |
| 1366/1440/1920 + 移动端 | 16 组测量全部通过 |
| 检查 console error、路由刷新、键盘可用性 | 14 次切换 0 报错；直连 URL 刷新正常；键盘逐项实测 |
| 无模型时的静态案例可用性 | 停后端实测通过 |

---

## 5. 未完成 / 已知问题

1. **S3 仅 1 件作品**有分层素材，其余 4 件明确提示「暂未开放」。
2. **S4 纹脉星球**只有调研，无代码。
3. 2 处热点为 `approximate`（瑞猫迎春顶部题名横带、绣兔牡丹针脚与织物），界面已标注。
4. 移动端热点圆点 32px，低于 44px 推荐触摸目标。
5. 没有可视化标点编辑器，坐标靠脚本 + 手写数据文件。
6. 故事页无阅读进度持久化；JSON 导出无对应导入器。
7. 未安装 `@types/react`，组件内事件类型用最小结构类型描述。
8. `/generate` 本轮未实机调用（约束冲突，见 §2.2）。

---

## 6. 复现步骤

```bash
cd D:\wenmai-huazhang\backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000

cd D:\wenmai-huazhang\frontend
node node_modules\typescript\bin\tsc --noEmit
node --test "tests/*.test.ts"
node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173
```

浏览器访问：

```
http://127.0.0.1:5173/gallery
http://127.0.0.1:5173/experience/zhuxianzhen-ruimao
http://127.0.0.1:5173/story/songhua-yunhe
http://127.0.0.1:5173/wander/songhua-yunhe
```

> 说明：本机 `npx` 被 PowerShell 执行策略拦截，因此一律用 `node node_modules/...` 直接调用。

---

## 7. 证据文件

| 文件 | 内容 |
|---|---|
| `docs/interactive_v2/screens/gallery-1280.png` | 改写后的展厅（真实页面） |
| `docs/interactive_v2/screens/exp-zxz-default.png` | 互动页默认态 |
| `docs/interactive_v2/screens/exp-zxz-selected.png` | 选中第 1 处线索后的面板 |
| `docs/interactive_v2/screens/story-songhua-ch3.png` | 故事页第 3 折镜头 |
| `docs/interactive_v2/screens/story-mobile-390.png` | 390×844 窄屏粘性画面 |
| `docs/interactive_v2/screens/wander-songhua.png` | 2.5D 分层视差 |
| `docs/interactive_v2/screens/gallery-autosave-runtime.png` | 自动保存的新案例在展厅中的呈现（1280） |
| `docs/interactive_v2/screens/gallery-autosave-mobile.png` | 同一页面 390×844 |

---

## 8. 追加：生成结果自动沉淀为真实案例（2026-10-20 晚）

**需求**：以后每次在创作台生成成功，图片自动保存到真实案例，并按现有五件的样式呈现。

**改动**（纯增量，`/creator` 的既有生成与下载行为不变）：

| 文件 | 改动 |
|---|---|
| `backend/case_store.py`（新增） | 落盘案例、Pillow 绘制 1080×1440 文化卡、列清单、清理 |
| `backend/app.py` | `/generate` 成功后自动保存；新增 `GET /cases`、`DELETE /cases/{id}` |
| `frontend/src/services/caseService.ts`（新增） | 拉取运行期案例、字段归一化、与内置案例合并 |
| `frontend/src/services/generationService.ts` | 透传 `savedCase` / `autoSave` 回执 |
| `frontend/src/data/savedCases.ts` | 改为 `GalleryCase` 结构，加 `caseId` / `caseOrigin` |
| `frontend/src/pages/Gallery.tsx` | 两路数据合并；运行期案例单独呈现；文化卡面板限高；hash 定位 |
| `frontend/src/pages/AICreator.tsx` | 结果区提示「已自动存入展厅」+ 跳转链接 |
| `frontend/tests/case-service.test.ts`（新增） | 7 个用例（归一化、合并、降级） |

**验收**（详见 `CASE_AUTOSAVE.md`）：

- 保存链路：`autoSave: {enabled: true, saved: true}`，新目录含 `generated.png` / `culture_card.png` / `metadata.json`，sha256 与字节数现算；
- 安全性：`delete_case('zhuxianzhen') → False`，内置五件不可删；mock 图默认不保存；
- 展厅：6 张卡（运行期第一），运行期卡片**不显示**互动入口，标「自动保存 · 热点待标注」；
- 稳定性：展开文化卡后同排其他卡片高度不变（641 → 641）；390×844 单列无横向滚动；
- 降级：后端关闭时仍有 5 件 + 「没有连上本地后端」提示，无报错；
- `tsc --noEmit` 退出码 0，`node --test` **39 个用例通过**。

**仍然没做**：不自动生成热点/章节/分层；新案例只在本地后端运行时可见（静态部署看不到）。

所有截图来自真实运行页面（`127.0.0.1:5173`），未使用设计稿或合成图。