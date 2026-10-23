# 正式入口与功能源码审计（2026-10-24）

本报告依据当前本地源码、导入关系、路由和既有实验资料编写。除明确列出的本轮自动化检查外，表内“源码实现，待运行验证”表示代码已接入正式入口，不代表本轮已经操作验收。实际运行及云端推理结果以同日工程报告和同步验收报告为准。旧验收文件保留原始日期与结论，不能替代当前版本验证。

## 1. 正式版本的判定

正式应用入口为 `frontend/index.html → frontend/src/main.tsx → frontend/src/App.tsx`，配套后端为 `backend/app.py`。React Router 定义全部产品页面；`VITE_STATIC_SHOWCASE=true` 时使用 HashRouter，否则使用 BrowserRouter。GitHub Pages 工作流 `.github/workflows/pages.yml` 使用 `/wenmai-huazhang/` 构建基路径、Node.js 22，并只发布 `frontend/dist`。

当前代码已经包含互动体验与三维展馆；旧 README 主要展示生成工作台，遗漏这些正式入口。当前审计起始时最新提交为 `74cb74d feat: sync Wenmai Huazhang gallery and heritage assets`，这些模块已经由本地 Git 跟踪，本轮文档升级并不等于这些模块全在本轮首次开发。

| 正式路由 | 源文件 | 内容和边界 |
|---|---|---|
| `/` | `frontend/src/pages/Home.tsx` | 品牌首页、风格/创作入口、同作品成图对应的三种互动入口 |
| `/creator` | `frontend/src/pages/AICreator.tsx` | 生成工作台；静态部署明确关闭实时生成 |
| `/styles` | `frontend/src/pages/StyleLibrary.tsx` | 五种文化视觉风格 |
| `/products` | `frontend/src/pages/ProductStudio.tsx` | 八种文创模板预览、PNG 导出 |
| `/gallery` | `frontend/src/pages/Gallery.tsx` | 五组精选案例 + 自动入库/运行期案例；参考成图对照、文化卡、文创入口 |
| `/experience/:id` | `frontend/src/pages/Experience.tsx` | 可缩放画作、热点、画面观察/文化解读/来源 |
| `/story/:id` | `frontend/src/pages/Story.tsx` | 一图一境，章节滚动驱动焦点、故事数据导出 |
| `/wander/:id` | `frontend/src/pages/Wander.tsx` | 当前五件作品均声明 world 深度资产；有限视角 2.5D 画境 |
| `/heritage-gallery` | `frontend/src/pages/HeritageGallery.tsx` | 满视口三维馆、内外机位、昼夜、布展、器物、角色 |
| `/scenarios` | `frontend/src/pages/Scenarios.tsx` | 数字屏/商店/手机场景静态示意，不是终端集成 |
| `/about` | `frontend/src/pages/About.tsx` | 项目说明；部分技术概述早于互动和展馆版本 |

`/heritage-gallery` 和 `/wander/:id` 位于 MainLayout 之外，设计为沉浸式全屏。其余页面沿用站内导航和页脚。

## 2. 核心功能矩阵

| 功能 | 本次源码判定 | 实现证据 | 实际限制 |
|---|---|---|---|
| 五种文化风格 | 源码实现，待运行验证 | `frontend/src/data/styleLibrary.ts`、`backend/style_config.py` | 年画、汴绣、宋画、青花、剪纸；没有第六种正式风格 |
| 文本生成图像 | 源码实现，待运行验证 | `backend/providers/dashscope_qwen_image_provider.py`、`backend/provider_service.py` | 百炼 Qwen Image 3.0；需有效个人配置和联网 |
| 上传参考图/预览 | 源码实现，待运行验证 | `AICreator.tsx`、`generationService.ts`、`backend/app.py::GenerateRequest` | 工作台接受 PNG/JPEG；不能因上传成功就宣称远程模型确认使用，须看响应字段 |
| 主题/主体保持 | 源码实现，待运行验证 | `AICreator.tsx`、`backend/prompt_builder.py` | 通过提示词约束，不能保证任意输出身份完全保持 |
| 风格提示强度 | 源码实现，待运行验证 | `AICreator.tsx`、`backend/prompt_builder.py` | UI 0–100%，调 Prompt 强调；不是训练权重或相似度 |
| 负向提示、构图、用途 | 源码实现，待运行验证 | `GenerateRequest`、`prompt_builder.py` | 控制输出倾向；已有年画猫案例显示负向文字约束未完全生效 |
| 生成图片保存/下载 | 源码实现，待运行验证 | `backend/providers/`、`AICreator.tsx` | 成图由后端保存，浏览器下载 PNG；路径和来源依 provider 而定 |
| 浏览器最近结果/缩略历史 | 源码实现，待运行验证 | `AICreator.tsx` 的 `wenmai_latest_result`、`historyImages` | 最近结果 localStorage；缩略历史为页面内 state，不是完整跨设备作品数据库 |
| 案例自动持久保存 | 源码实现，待运行验证 | `backend/case_store.py`、`backend/app.py`、`caseService.ts` | 成功结果自动存入 `docs/examples/<case>/`；可配置关闭，演示模式默认不存 |
| 案例删除保护 | 源码实现，待运行验证 | `DELETE /cases/{case_id}`、`case_store.py` | 后端仅允许删除运行期案例，保护精选案例；不是多用户鉴权系统 |
| Qwen3-VL 成图理解 | 源码实现，待运行验证 | `backend/services/vision_analysis.py`、`provider_service.py` | Ollama 本机服务；失败保留作品并标记 template_fallback |
| 参考图基础统计 | 源码实现，待运行验证 | `backend/image_analyzer.py`、`POST /analyze-image` | 基础统计/配置的分析 provider，与生成后 Qwen3-VL 解读不同 |
| CultureCard | 源码实现，待运行验证 | `frontend/src/components/creator/CultureCard.tsx`、`backend/culture_card_builder.py` | 结构化画面解读和文化阐释；不能视为史料认证 |
| 文化卡图像导出 | 源码实现，待运行验证 | `CultureCard.tsx`、五组 `culture_card.png` | 前端 1080×1440 PNG；既有卡片可追溯 |
| 八种文创效果/导出 | 源码实现，待运行验证 | `ProductStudio.tsx::PRODUCTS/renderProductExport` | 明信片、海报、帆布袋、书签、杯垫、手机分享、展陈屏、纪念票；1600×1200 PNG；模板效果映射，非制造交付 |
| 参考与生成作品对照 | 源码实现，待运行验证 | `features/culture-experience/components/ArtworkCompare.tsx` | 同案例参考/成图对照；保留来源配对 |
| 真实五组案例 | 源码实现，待运行验证 | `data/savedCases.ts`、`docs/examples/{zhuxianzhen,bianxiu,songhua,qinghua,jianzhi}` | 原参考、成图、文化卡、metadata 均应保留；案例原始日期不是本轮调用日期 |
| 自动参数消融对比 | 未发现正式实现 | 工作台可反复调参数，但无独立批量对比路由或实验调度 | 不将不同强度/负向词的界面控件冒充自动对比功能 |
| 在线真实推理 | 未实现于 GitHub Pages | `.github/workflows/pages.yml`、`VITE_STATIC_SHOWCASE` | Pages 是前端静态浏览；本地后端配置后才可实时生成 |
| 多用户登录/交易/打印终端/实时大屏同步 | 未实现 | `Scenarios.tsx` 自述边界 | 场景方案和文创预览不能宣传为商业系统集成 |

## 3. 新增互动与三维模块

| 功能 | 本次源码判定 | 准确入口/源码 | 限制与版本关系 |
|---|---|---|---|
| 画中有话热点探索 | 源码实现，待运行验证 | `/experience/:id`、`CultureExperienceViewer.tsx`、`HotspotLayer.tsx`、`KnowledgePanel.tsx` | 五件精选作品，25处线索；图像 contain 坐标、缩放拖拽、键盘切换；观察与文化解读分开 |
| 三折叙事 | 源码实现，待运行验证 | `/story/:id`、`frontend/src/data/experiences/*.ts` | 五件各三折；章节焦点由数据定义，不是每次在线重新生成故事 |
| 文化来源注册表 | 源码实现，结构测试通过 | `culture_knowledge/sources.json`、`data/experiences/index.ts` | 11条来源；知识条目有来源关系，并非向量检索/RAG 服务 |
| 五件深度画境 | 源码实现，待运行验证 | `features/painting-world/{PaintingWorld,WorldScene,world,shaders}`、`public/interactive/<style>/world/world.json` | 深度网格、遮罩、局部动效、镜头推进/转头/有限前后；不能绕到物体背面 |
| 画境低性能降级 | 源码实现，待运行验证 | `PaintingWorld.tsx` | WebGL2/低功耗/reduced-motion/持续低帧率判定；`?static=1` 静态+视差 |
| 自动互动内容入库 | 实验/依赖额外条件 | `scripts/interactive/ingest_case.py`、`backend/interactive_jobs.py` | 后台线程，不阻塞出图；需深度估计依赖和模型。自动热点为 approximate/pending，必须人工复核 |
| 新案例互动展示 | 源码实现，待运行验证 | `data/autoExperiences.ts`、`data/savedCases.ts` | 编译期 glob；`docs/examples` 新目录不在默认 Vite root watcher 内，新增后需重启dev/重新构建 |
| Blender 三维展馆 | 源码实现，待运行验证 | `/heritage-gallery`、`HeritageScene.tsx`、`GalleryModel.tsx` | 当前模型 `frontend/public/models/wenmai_gallery_v5.glb`；真实GLB场景，与单图画境技术不同 |
| 场景环绕缩放/机位 | 源码实现，待运行验证 | `HeritageScene.tsx`、`data/heritageGalleryConfig.ts` | OrbitControls、外观/内部/布展机位；室内隐藏屋顶 |
| 第一人称/电影视角 | 源码实现，待运行验证 | `scene/CameraModes.tsx`、`components/ViewModeSwitch.tsx` | 浏览器第一人称依赖 pointer lock，WASD；电影模式程序化巡游 |
| 昼夜及沉浸模式 | 源码实现，待运行验证 | `DayNightRig.tsx`、`HeritageGallery.tsx` | 昼/暮/夜照明切换；隐藏UI/Esc退出 |
| 画框换画/拖动/持久化 | 源码实现，待运行验证 | `GalleryFrame.tsx`、`GalleryPanel.tsx`、`state/curationStore.ts` | localStorage个人布展；馆内作品清单源自五件精选 `savedCases`，未自动收录所有运行期案例 |
| 14件器物DIY布展 | 源码实现，待运行验证 | `props/assets/{assetCatalog,assetProps,AssetInstance,library.gen}`、`DiYLayer.tsx` | 通用/年画/汴绣/山水/青花/剪纸器物；落位吸附、编辑、旋转缩放、专属互动和本地状态；不是新的生成风格 |
| 吉祥物角色探索 | 源码实现，待运行验证 | `mascot/{MascotCompanion,mascotConfig}`、`public/models/wenmai_mascot_ww.glb` | 角色运行、视角、展品信息、楼梯/碰撞等为项目场景规则；不宣传通用物理引擎 |
| 三渲二 | 部分/历史方案 | `scene/sanzhuan2.ts`、`GalleryModel.tsx` | 当前 `TOON_ENABLED=false`，V5保留GLB原PBR颜色；不能声称本轮默认全场景启用三渲二 |
| 纹脉星球 | 调研，未实现 | `docs/interactive_v2/S4_TINY_PLANET_RESEARCH.md` | 不存在正式App路由；不可作为已实现功能截图 |

## 4. 正式资源、旧版本与独立原型

- 正式模型由 `GalleryModel.tsx` 常量选择 V5，不能根据目录里 v4 或无后缀GLB的文件时间替换；运行时角色模型为 `wenmai_mascot_ww.glb`。Blender编辑源、导出物、渲染及历史验收有版本意义，应按资源审计决定发布或归档。
- `tools/dsh-plugins/wenmai-3d-reconstruction/tests/viewer/index.html` 是插件测试查看器，不由 App 导入，也不是产品首页。项目 `frontend/index.html` 才是 Vite入口。
- 器物 `library.gen.ts` 由原设计 HTML 的白名单14件代码移植并被正式模块引用；原始 HTML 路径描述不能当成部署依赖或仍存在的正式页面。
- `docs/interactive_v2/FINAL_ACCEPTANCE.md` 记录2026-10-20阶段“一件三层视差”；当前五件 `animation.mode='world'` 且五份清单存在。保留旧文档作为历史，当前能力用源码与本轮运行界定。
- `docs/heritage_gallery/v4/FINAL_VISUAL_ACCEPTANCE.md` 明确 V4视觉未通过；不得把这个历史结论改成全部通过，也不得用其证明当前V5没有正式集成。
- 五组精选案例、metadata、来源文档、`iCAN_应用方案`、既有LICENSE/第三方说明与Release历史均具有溯源意义，本次审计不删除。
- InstantStyle、OpenAI/Wanx、mock/fast_demo 等 provider 保留兼容代码；默认产品展示使用 Qwen Image，InstantStyle 所需本地权重/独立依赖不随仓库分发。存在provider文件并不代表全部已经本轮真实调用成功。

## 5. 本轮明确修复的子路径兼容问题

为使现有 Pages 入口持续可用，先备份到 `.backup/audit_sync_20261024/`，再做以下小修：

1. 展馆GLB和角色GLB从根绝对URL改为拼接 Vite `BASE_URL`，保留V5查询版本。
2. Story/Experience/Wander、画境下一卷、互动模式切换、知识面板、工具条与错误兜底的站内链接改 React Router `Link`，兼容 BrowserRouter/HashRouter。
3. “从第一折读起”改为按钮调用章节滚动，不覆盖 HashRouter 路由；相关章节链接hash也按当前章节数据定位。
4. `publicUrl` 对已带base的构建图URL、HTTP/data/blob URL保持原样，避免静态降级中二次拼接base导致404。

修改后已真实执行 `npm run lint`（通过）和 `npm test`（44/44通过）。这些检查覆盖类型、案例数据、几何与schema等，不替代浏览器3D交互和云端模型验收。Pages重新构建与实际页面验收由主任务继续执行。
