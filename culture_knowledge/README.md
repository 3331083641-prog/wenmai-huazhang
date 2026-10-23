# 文化知识包说明（culture_knowledge）

本目录为《纹脉华章》提供**文化事实底稿**，供前端热点文案、AI 提示词与「资料来源」展示引用。

它不是设计规范，也不是营销文案库。它的作用是：让写文案的人知道**哪些话有出处、哪些话只是解释、哪些话不能说**。

```
culture_knowledge/
├── sources.json        来源登记表（11 条，全部已实际抓取）
├── zhuxianzhen.json    朱仙镇木版年画
├── bianxiu.json        汴绣
├── songhua.json        宋画青绿山水
├── qinghua.json        青花瓷纹样
├── jianzhi.json        中国民间剪纸
└── README.md           本文件
```

`styleId` 与前端 `frontend/src/data/styleLibrary.ts` 中的五个 id 一一对应：`zhuxianzhen / bianxiu / songhua / qinghua / jianzhi`。**不要改名**：热点数据与样式库都按这五个字符串索引。

---

## 一、三类内容必须分开写

这是本目录最重要的纪律。任何一句话，先判断它属于哪一类，再决定写进哪个字段、能不能直接上线。

| 类别 | 定义 | 写在哪里 | 上线要求 |
| --- | --- | --- | --- |
| ① 可观察的图像细节 | 看作品本身就能指出来的形态：线条、设色、构图、材质痕迹 | `visualFeatures` | 可直接用，但必须是**描述**，不能夹带因果与寓意 |
| ② 有来源的文化知识 | 产地、年代、名录、工艺步骤、纹样名称与定义 | `typicalMotifs`、`craftFeatures`、`paletteNotes`、`heritageNote`、`regionEra`，并挂 `sourceIds` | 必须能追到 `sources.json` 里的某条 url；无来源则不写 |
| ③ 审美解释 / 推断 | 「显得庄重」「传达对美好生活的向往」「色彩体现民间审美」 | 只允许出现在 `paletteNotes` 中已标注「属工艺观察（解释）」的条目，或项目自身的策划文案里 | **必须显式标注为「解释」**，不得与①②混排成同一语气 |

判断口诀：

- 能指着画面说「这里有什么」→ ①
- 能翻到原文说「书上这么写」→ ②
- 只能说「我觉得它意味着」→ ③，且要标出来

反面例子：

> ❌「朱仙镇年画用朱红与明黄，象征驱邪纳福、五谷丰登。」
> —— 前半句是①（用色），后半句把③当②写，且来源未支持该作品的具体寓意。

> ✅「朱仙镇年画以矿物、植物颜料手工磨制，印后色彩明快鲜艳（来源：SRC-ZXZ-CRAFT-002）。红色在节庆语境中常与喜庆相连，这一层属解释，不作为史实。」

---

## 二、`sources.json` 字段说明

顶层结构：

```json
{ "version": "1.0.0", "updatedAt": "2026-10-20", "sources": [ ... ] }
```

| 字段 | 类型 | 含义 | 约束 |
| --- | --- | --- | --- |
| `id` | string | 来源唯一标识，形如 `SRC-<主题>-<细分>-<序号>` | **不可改名**。热点数据按 id 引用，改名即断链 |
| `title` | string | 页面标题，尽量保留原题 | 不加书名号以外的修饰 |
| `publisher` | string | 发布机构 | 写站点背后的机构，不写「网络」 |
| `url` | string | 实际访问过的地址 | 必须是抓取成功的那一条；禁止凭印象拼 URL |
| `sourceType` | enum | `official_portal` / `museum` / `academic` / `encyclopedia` / `craft_org` | 决定可信度档位，见第三节 |
| `retrievedAt` | string | 抓取日期 `YYYY-MM-DD` | 与顶层 `updatedAt` 同步维护 |
| `verification` | enum | `verified` / `unverified` | 只有**抓到正文并确认内容支撑**才可写 `verified` |
| `verificationNote` | string | 抓取情况说明 | 写清「抓到了什么」或「为何没抓到」，不要写「应该没问题」 |
| `supports` | string[] | 该来源具体支撑哪些事实 | 一条一句，可与知识包的字段对应；不得写入来源没有的内容 |

### `verification` 的判定标准

| 取值 | 判定条件 | 允许的用法 |
| --- | --- | --- |
| `verified` | 用 `web_fetch` 抓到 HTTP 200 且正文可读，且 `supports` 里每条都能在正文中找到对应表述 | 可作为事实依据 |
| `unverified` | 只确认域名存在、页面 403/404、需登录、正文为空、或仅抓到导航壳 | **不得**作为事实依据；引用时必须提示「来源待核」 |

`verificationNote` 要写成可复核的记录，例如：

- ✅「实际抓取到正文（HTTP 200），含项目编号、公布批次与项目简介。」
- ✅「页面返回 403，仅确认域名存在，未获取正文。」
- ❌「来源可靠。」（不可复核，等于没写）

### 本次登记情况（2026-10-20）

11 条来源**全部 `verified`**：均通过 `web_fetch` 拿到正文并逐条比对 `supports`。其中：

- `ihchina.cn`（中国非物质文化遗产网）3 条：朱仙镇年画、汴绣、剪纸
- `dpm.org.cn` / `minghuaji.dpm.org.cn` / `ggzl.dpm.org.cn` / `young.dpm.org.cn`（故宫博物院系列）7 条：千里江山图、明代御窑青花展、祥云彩画讲座、釉里红缠枝牡丹纹碗、青花折枝花卉纹大盘、海水江崖织绣、祥瑞图科普页
- `hct.henan.gov.cn`（河南省文化和旅游厅）1 条：朱仙镇年画套色工艺
- 另有 `ihchina.cn` 的《中国雕版印刷技艺》条目抓取成功，仅用于交叉核对雕版刷印原理，**未单独登记**，故不计入 11 条。
- 无 `encyclopedia` 类条目。中文维基百科虽在候选名单内，但本次所有主题均找到了机构一手页面，故未采用百科作为依据。

---

## 三、可信度分级

### 3.1 来源档位（`sourceType`）

| 档位 | 含义 | 引用强度 | 典型站点 |
| --- | --- | --- | --- |
| `official_portal` | 政府部门或官方非遗门户 | 高。名录、批次、编号、保护单位可直接引用 | ihchina.cn、hct.henan.gov.cn |
| `museum` | 博物馆藏品说明、展览说明、官方科普 | 高（器物与图像）；中（科普页的通俗解释） | dpm.org.cn、minghuaji.dpm.org.cn |
| `academic` | 论文、学术机构出版物 | 高，但需注意结论的限定条件 | 期刊、高校机构库 |
| `craft_org` | 行业组织、工坊、传承人机构 | 中。工艺细节可信，历史叙述需交叉验证 | 行业协会、合作社 |
| `encyclopedia` | 百科类（含维基、百度百科） | **低**。只能用于「通行表述」，不得作为定论 | zh.wikipedia.org |

使用 `encyclopedia` 时，`supports` 里必须写明「通行表述」四个字，且知识包正文要避免把它当作唯一依据。

### 3.2 表述强度三档

在文案里，来源档位要翻译成读者看得懂的措辞：

| 档位 | 适用情形 | 推荐措辞 | 禁用措辞 |
| --- | --- | --- | --- |
| 事实 | 有 `verified` 来源直接支持 | 「据中国非物质文化遗产网」「2006 年列入第一批国家级非遗名录」 | 「自古以来」「众所周知」 |
| 通行表述 | 仅百科/科普页支持，或多来源口径不一 | 「常见说法是」「通常认为」 | 「即为」「确系」 |
| 解释 | 审美判断、寓意引申 | 「可理解为」「在策展语境中读作」 | 「象征着」（当作定论时） |

### 3.3 一条来源不支撑全部相关说法

同一个主题的多个事实可能来自不同来源。典型陷阱：

- `SRC-MOTIF-MUDAN-001` 支撑「牡丹纹作为器物装饰存在及其形态」，**不支撑**「牡丹寓意富贵」——后者属吉祥纹样通识，需引 `SRC-MOTIF-JIXIANG-001` 的谐音/寓意逻辑，且仍应写成解释。
- `SRC-MOTIF-HAISHUI-001` 是清代**织绣**实例，不能用来断言青花瓷上的海水纹形制。
- `SRC-MOTIF-XIANGYUN-001` 讲的是**建筑彩画**中的祥云，不能直接等同于年画、刺绣、瓷器上的云纹程式。

写文案时若跨了材质或门类，必须换来源或降级为「解释」。

---

## 四、知识包字段说明

| 字段 | 类型 | 写什么 | 不写什么 |
| --- | --- | --- | --- |
| `styleId` | string | 固定五个 id 之一 | 不得改名、不得新增 |
| `styleName` | string | 与样式库一致的中文名 | 不加副标题、不加营销词 |
| `knowledgeVersion` | string | 语义化版本，见第六节 | 不随意跳号 |
| `category` | string | 门类定性，括号内注明是否非遗类别 | 不写「顶级」「代表性」等评价 |
| `regionEra` | string | 地域、时代、兴衰脉络，逐句可追来源 | 不写精确起年（来源未明确时）；不确定处写「常见说法，来源待核」 |
| `isIntangibleCulturalHeritage` | boolean | **只有确有国家级名录依据才为 `true`** | 不得因为「很传统」「很有名」就写 `true` |
| `heritageNote` | string | 名录名称、批次、年份、项目编号；`false` 时说明为何不是非遗 | 不写「正在申报」「有望入选」 |
| `visualFeatures` | string[] | ① 类：可观察的图像细节 | 不夹带寓意、不写「象征」 |
| `typicalMotifs` | object[] | `name` + `note` + `sourceIds`；`note` 说明该纹样在本门类中的实际用法与来源边界 | 不把纹样寓意写成定论；不虚构纹样名 |
| `craftFeatures` | string[] | 工序、工具、技法、材料；有来源 | 不编造工序数量与针法名目 |
| `paletteNotes` | string[] | 用色习惯与设色逻辑；解释类须自带「属解释」标注 | 不把前端主题色当史料 |
| `avoidClaims` | string[] | 明确禁止的错误表述，写成「不要……」 | 不写成建议（「建议避免」力度不够） |
| `sourceIds` | string[] | 本包实际用到的来源 id | 不得引用 `sources.json` 中不存在的 id |

### `isIntangibleCulturalHeritage` 的判定口径

非遗与否**按项目实体判断，不按「传统程度」判断**：

| 知识包 | 取值 | 依据 |
| --- | --- | --- |
| `zhuxianzhen` | `true` | 2006 年第一批国家级非遗代表性项目名录（传统美术类） |
| `bianxiu` | `true` | 2008 年第二批国家级非遗，项目编号 Ⅶ-74，河南省开封市 |
| `jianzhi` | `true` | 2006 年第一批国家级非遗（Ⅶ-16）；2009 年入选联合国教科文组织人类非遗代表作名录 |
| `songhua` | `false` | 青绿山水是画种/技法传统，不是非遗项目 |
| `qinghua` | `false` | 青花瓷是瓷器品种；其**烧制技艺**另有非遗归属，但品种本身不是 |

这一列**不允许为了文案气势而改成 `true`**。若策划需要「非遗」标签，只能挂在确实是非遗的对象上（如「景德镇手工制瓷技艺」「汴绣」「朱仙镇木版年画」），不能挂在画种与瓷器品种上。

---

## 五、前端怎么用

### 5.1 渲染「资料来源」

热点卡片 / 详情页的「资料来源」列表，应由 `sourceIds` 反查 `sources.json` 生成，**不要在组件里硬编码来源名称**。

```ts
// 仅示意，放在前端数据层，不要塞进本目录
import sourcesDoc from '../../culture_knowledge/sources.json';
import zhuxianzhen from '../../culture_knowledge/zhuxianzhen.json';

const byId = new Map(sourcesDoc.sources.map((s) => [s.id, s]));

export function resolveSources(ids: string[]) {
  return ids
    .map((id) => byId.get(id))
    .filter(Boolean)
    .map((s) => ({
      id: s!.id,
      title: s!.title,
      publisher: s!.publisher,
      url: s!.url,
      // 未核实的来源必须在 UI 上显性标注，不可与已核实来源同样呈现
      badge: s!.verification === 'verified' ? undefined : '来源待核',
    }));
}

export const zhuxianzhenSources = resolveSources(zhuxianzhen.sourceIds);
```

渲染纪律：

1. **一条 `sourceIds` 一项**，按数组顺序展示，不合并同类项。
2. `verification: "unverified"` 的来源显示「来源待核」角标，或直接不展示 url。
3. 链接用 `target="_blank" rel="noopener noreferrer"`；外部站点可能失效，需有兜底文案。
4. **不要**把来源渲染成「权威认证」「官方背书」；它们只是出处。
5. 卡片正文若引用了某条具体事实，优先在该句末尾放行内标注（如 `[1]`），再在底部列表展开，而不是只给一整包来源。
6. 来源列表为空时整块隐藏，不要显示「暂无来源」这类暴露数据缺口的话术。

### 5.2 与现有样式库的关系

`frontend/src/data/styleLibrary.ts` 中的 `visualFeatures`、`symbolicMeaning` 是**面向生成提示词的精简版本**；本目录的 `visualFeatures` 是**面向事实核查的完整版本**。两者允许措辞不同，但**不允许冲突**：

- 若样式库写「大红大绿」，而知识包来源只支持「色彩明快鲜艳」，应调整样式库措辞或降级为解释。
- 样式库的 `cardTheme` 色值（如 `#a92822`）是设计取值，知识包的 `paletteNotes` 已注明「不是史料结论」，两者不要互相引用为依据。

### 5.3 给 AI 生成提示词用

把知识包喂给模型时，建议只投喂 `visualFeatures` + `typicalMotifs[].name` + `paletteNotes`，**不要**投喂 `avoidClaims` 之外的推断句；`avoidClaims` 可转为负面提示词（negative prompt）或系统约束。不要把 `regionEra` 整段塞进提示词——模型容易把它改写成营销故事。

---

## 六、如何升级知识包

### 6.1 标准流程

```
发现缺口 / 收到纠错
   ↓
① 新增或替换来源（先 web_fetch 抓正文，拿到 url 与正文证据）
   ↓
② 在 sources.json 追加条目，填 verification 与 verificationNote
   ↓
③ 回填知识包：改字段 → 挂 sourceIds → 在 supports 补一行对应事实
   ↓
④ 一致性检查（见 6.2）
   ↓
⑤ 提升 knowledgeVersion 与 updatedAt，在下方变更记录登记
```

### 6.2 提交前检查清单

- [ ] 新增 `sourceIds` 全部存在于 `sources.json`
- [ ] 每条 `url` 都是本次实际抓取成功的地址（不是搜索结果的跳转链接）
- [ ] `verification: "verified"` 的条目，`supports` 每条都能在正文中找到对应句子
- [ ] `encyclopedia` 类来源的 `supports` 含「通行表述」字样
- [ ] 新增断言没有落进 `visualFeatures`（该字段只放可观察细节）
- [ ] `avoidClaims` 覆盖了本次新增内容最容易出的错
- [ ] 未把前端设计色值写进 `paletteNotes` 当作史实
- [ ] JSON 可被 `JSON.parse` 解析（无尾逗号、无注释）

只读自检命令（不装依赖）：

```powershell
cd D:\wenmai-huazhang
Get-ChildItem culture_knowledge\*.json | ForEach-Object {
  try { Get-Content $_.FullName -Raw | ConvertFrom-Json | Out-Null; "OK   $($_.Name)" }
  catch { "FAIL $($_.Name): $($_.Exception.Message)" }
}
```

### 6.3 版本号规则（语义化）

| 变更类型 | 版本位 | 例子 |
| --- | --- | --- |
| 修正事实错误、补来源、改措辞但不改结论 | PATCH | 1.0.0 → 1.0.1 |
| 新增字段内容、新增纹样条目、扩充 `avoidClaims`、`isICH` 判定变化 | MINOR | 1.0.1 → 1.1.0 |
| 字段结构变更、`styleId` 调整、来源体系重构 | MAJOR | 1.1.0 → 2.0.0 |

`isIntangibleCulturalHeritage` 从 `false` 改 `true` 属 MINOR，但必须在 `heritageNote` 里补上名录名称、批次、年份，并在变更记录里写明依据来源 id。

### 6.4 停用来源

`sourceId` 一旦被引用就**不要删除**。若来源失效：

1. 把 `verification` 改为 `unverified`，`verificationNote` 写「原链接已失效，YYYY-MM-DD 复核」；
2. 找替代来源，新增 id 并同步知识包 `sourceIds`；
3. 旧 id 保留在 `sources.json` 中，`supports` 标注「已被 SRC-xxx 取代」。

直接删 id 会让历史文案的出处悬空。

---

## 七、使用纪律（前端文案红线）

1. **不得**把五个风格都称为「非遗」。青绿山水是画种，青花瓷是瓷器品种，两者 `isICH` 为 `false`。
2. **不得**编造博物馆收藏编号、藏品名、「XX 博物院珍藏」这类无法核实的表述。可以写「故宫博物院藏《千里江山图》卷」——因为来源明示；不能写具体文物号。
3. **不得**编造历史人物、传承人姓名、师承关系、获奖记录。
4. **不得**给出精确年代数字，除非来源明确（如「2006 年」「2008 年」「1127 年」可以，因为来源写了）。
5. **不得**把工艺写成现代工艺（数字印刷、丝网印刷、激光切割、数码印花）。
6. **不得**把美学推断伪装成史实（「象征驱邪纳福」「体现天人合一」直接下断言）。
7. **不得**跨门类搬用纹样含义（把织绣的海水江崖形制说成青花形制；把建筑彩画的祥云说成年画程式）。
8. **不得**使用来源未支持的排名与「最」字表述（四大名画、四大名绣、中国第一）。
9. **建议**：每段涉及文化事实的文案，控制在 1–2 个可核查断言，其余交给视觉描述。

---

## 八、已知局限

- `SRC-MOTIF-XIANGYUN-001` 为讲座页，提纲较简，只能支撑祥云的寓意与「建筑彩画题材」这一层，**没有**纹样形态谱系。若后续要写祥云的造型分类，需补学术来源。
- 汴绣的 36 种针法只有总数，**无具体名目**。任何列出针法名称的文案都必须先补来源。
- 朱仙镇年画的「近千年历史」是来源表述，具体创制年代无确切纪年，`regionEra` 已按此措辞处理。
- 五个知识包均未涉及传承人个人履历，仅 `heritageNote` 与 `regionEra` 引用了来源中的名录信息。
- 本目录不包含图像资产与生成提示词模板，视觉资产仍在 `frontend/public` 与 `docs/examples` 下。

---

## 九、变更记录

| 日期 | 版本 | 内容 |
| --- | --- | --- |
| 2026-10-20 | 1.0.0 | 首次建立。11 条来源全部实际抓取并 `verified`；五个知识包按三类内容边界编写；确立 `isICH` 判定口径与前端渲染纪律。 |