# 生成结果自动沉淀为真实案例

> 目标：在创作台每次生成成功之后，结果自动落盘成与现有五件**同构**的案例，
> 在展厅里以同一套样式呈现（参考图 / 成图对照 / 文化卡 / 文创入口）。
> 实现：`backend/case_store.py`、`backend/app.py`、`frontend/src/services/caseService.ts`、`frontend/src/pages/Gallery.tsx`
> 日期：2026-10-20

---

## 1. 先说清楚「和现在一样」到什么程度

| 能力 | 内置五件 | 自动保存的新案例 |
|---|---|---|
| 参考图 / 成图左右对照 | ✅ | 有上传参考图时 ✅，否则显示单图 |
| 文化卡（1080×1440） | ✅ | ✅ Pillow 按同一版式绘制 |
| 文创预览与下载 | ✅ | ✅ |
| 展开文化卡 | ✅ | ✅ |
| 画中有话（热点） | ✅ 人工标注 | ❌ **不做自动推断**，卡片标「热点待标注」 |
| 一图一境（章节） | ✅ 人工撰写 | ❌ 同上 |
| 画境漫游（分层） | 仅宋画 | ❌ 需手工做分层素材 |

**为什么热点不自动生成**：原始生成结果没有任何坐标信息，热点必须逐个裁切复核
（这一点在 S0 审计里已经确认过）。自动猜坐标会让用户点开一个指错位置的作品，
比没有这个入口更糟。所以运行期案例**明确不显示**三个互动按钮。

`metadata.json` 里的 `experienceId` 就是留给将来的开关：
填上某个体验 id，展厅立刻会给它挂上互动入口，不需要改代码。

---

## 2. 保存了什么

每次成功生成，在 `docs/examples/` 下新建一个目录（**绝不覆盖已有目录**）：

```
docs/examples/<styleId>-<YYYYMMDD-HHMMSS>-<rid4>/
    generated.png      成图（PNG，重新编码）
    reference.png      参考图（仅当本次有上传图）
    culture_card.png   文化卡 1080×1440
    metadata.json      与现有五件同构的字段
```

`metadata.json` 的关键字段：

| 字段 | 值 |
|---|---|
| `caseId` | 目录名，全局唯一 |
| `caseOrigin` | `runtime`（内置五件是 `curated`） |
| `experienceId` | 空字符串 = 暂无互动解读 |
| `styleId` / `styleName` | 与风格库一致 |
| `provider` / `model` | 实际出图的服务与模型 |
| `analysisSource` | `qwen3_vl` 或 `template_fallback` |
| `generatedSha256` / `generatedBytes` | **现算**，不是抄的 |
| `cultureCardExport` | `pillow_png` 或 `image_only_fallback` |
| `visionAnalysis` | 有 VL 解读就用真的；没有则用文化卡构造，并标 `template_fallback` |
| `generationHistory` | 本次生成的一条记录 |

**不伪造**：sha256、字节数、图片尺寸都是保存时计算；`visionAnalysis` 缺失时
构造的结构会在 `analysisSource` 里写明「模板兜底」，界面上也照实显示
「模板说明 · 未执行看图分析」。

---

## 3. 什么会被保存，什么不会

```python
REAL_PROVIDERS = {"dashscope_qwen_image", "instantstyle"}   # 真实出图才保存
```

| 情况 | 保存？ |
|---|---|
| Qwen Image / InstantStyle 出图成功 | ✅ |
| mock / fast_demo 演示图 | ❌ 默认不保存（防止假图混进展厅） |
| 生成失败 / 没有 localPath | ❌ |
| 保存过程抛异常 | ❌ 但**出图结果照常返回**，错误写进响应的 `autoSave.error` |

三个开关（`backend/.env` 或进程环境变量）：

| 变量 | 默认 | 作用 |
|---|---|---|
| `AUTO_SAVE_CASES` | `true` | 总开关 |
| `AUTO_SAVE_DEMO` | `false` | 是否也保存 mock/fast_demo（仅本机验证用） |
| `AUTO_SAVE_MAX_CASES` | `200` | 运行期案例上限，超出后删最旧 |

清理**只删 `caseOrigin=runtime`** 的目录，内置五件永不参与。

---

## 4. 接口

```
GET    /cases              列出全部案例（内置 + 运行期），含可直接使用的图片地址
DELETE /cases/{caseId}     删除运行期案例；内置案例返回 400
```

`/generate` 的响应新增两个字段：

```json
{
  "savedCase": { "caseId": "...", "artworkTitle": "...", "images": { "generated": "...", "reference": "", "cultureCard": "..." } },
  "autoSave":  { "enabled": true, "saved": true, "error": null }
}
```

`/examples/<caseId>/<file>` 的静态挂载本来就存在，所以新案例的图片可以直接访问。

---

## 5. 前端怎么呈现

展厅的数据来源从「只有编译期打包」变成两路合并：

```
savedCases（import.meta.glob + 5 份 metadata，离线可看）
        +
fetchRuntimeCases()  →  GET /cases  只取 caseOrigin=runtime
        ↓
mergeCases()：运行期在前、按 caseId 去重、同 id 时内置优先
```

- 后端不可达时**抛错**，展厅退回五件 + 一句「没有连上本地后端」的提示，
  不白屏、不假装有数据。
- 创作台在结果区显示「已自动存入文化作品展厅 · 查看《标题》」，
  点击跳到 `/gallery#case-<caseId>`，展厅会把它滚到视口中间。

---

## 6. 实测证据

用 MockProvider 造图 + monkeypatch `service.generate`，让请求走**真实的 `/generate` 接线**
（保存逻辑是真实代码），不联网、不产生费用：

```
autoSave: {'enabled': True, 'saved': True, 'error': None}
case dir: qinghua-20261020-191438-veri
files:    ['culture_card.png', 'generated.png', 'metadata.json']
caseOrigin: runtime | experienceId: ''
generated: 55725 bytes | sha256: bb0320994aa94d8f…
card export: pillow_png | card bytes: 188864
visionAnalysis keys: 11 个（title/observed_subjects/…/style_alignment）
listed total: 6 | runtime: 1
protected: ['bianxiu','zhuxianzhen','jianzhi','qinghua','songhua']
delete_case('zhuxianzhen') → False（内置案例受保护）
```

前端（真实浏览器）：

| 检查 | 结果 |
|---|---|
| 展厅卡片数（含 1 个运行期案例） | 6，运行期排第一 |
| 运行期卡片的按钮 | 只有「在创作台再生成一件 / 文创预览与下载 / 展开文化卡」 |
| 内置五件的按钮 | 互动三件套 + 文创 + 文化卡，与原样一致 |
| 展开文化卡 | 面板 560px 内滚动，卡片自身变高，**同排其他卡片高度不变**（641 未变） |
| 390×844 | 单列 358px，无横向滚动，运行期徽标与按钮正常 |
| 文创预览与下载 | 跳到 `/products`，localStorage 里是运行期案例的图 |
| 创作台提示 | 「已自动存入文化作品展厅 · 查看《秋日兰草与青花缠枝》」 |
| `/gallery#case-<id>` | 目标卡滚到 top=96，在视口内 |
| 后端关闭 | 5 件 + 离线提示，无报错 |

`tsc --noEmit` 退出码 0；`node --test` **39 个用例全过**（新增 7 个 `case-service.test.ts`）。

截图：`docs/interactive_v2/screens/gallery-autosave-runtime.png`、`gallery-autosave-mobile.png`

---

## 7. 局限（必须知道）

1. **新案例只在本地后端运行时可见**。静态部署（GitHub Pages）没有 `/cases`，
   展厅就只有内置五件——这不是 bug，是编译期打包与运行时数据的边界。
2. 热点、章节、分层素材**不会自动生成**，需要人工标注后把 `experienceId` 填进 metadata。
3. 自动保存的图会持续占磁盘（每件约 0.3–1.5 MB），默认上限 200 件。
4. 文化卡依赖系统字体（`msyh.ttc` 等）；换机器没有中文字体时退化为
   `image_only_fallback`（直接复制成图，metadata 会写清楚）。
5. 运行期案例的 `theme` 用用户输入的主题，可能与画面内容不完全对应——这是输入，不是解读。