# 非遗器物系统 · 交接说明（致接手 Agent）

项目：`D:\wenmai-huazhang`（React 19 + R3F + three 0.180，dev server 已在 5173 运行）
页面：`/heritage-gallery`

## 已完成（勿重做）

1. **资产抽取**：`frontend/src/features/heritage-gallery/props/assets/library.gen.ts`
   - 由 `scripts\assets\extract_library.py`（仓库内，可复现）从 `用户提供的原始资产 / 本机工具配置` 精确抽行生成（`// @ts-nocheck`）。
   - 含纹理生成器 + MAT + box/cyl/addFlushSpandrel + **仅白名单 14 个 builder**；
     排除件 A06/A10/B05/C03/D05 **代码根本不在文件里**。
   - 重新生成：`python scripts\assets\extract_library.py "用户提供的原始器物.html"`（脚本里已内置 B02 纸张 NaN 钳制）。
   - 14 件全部构建通过，浏览器审计钩子 `window.__wenmaiAudit()` 可量 bbox/网格数/三角面。
2. **元数据**：`assets/assetCatalog.ts`（14 件、6 分类、placement floor/surface/hang、说明、互动说明）
3. **实例化**：`assets/AssetInstance.tsx`（每实例克隆材质、包围盒对齐 y=0、点击触发、状态写回 store）
4. **控制器**：`assets/interactions.ts`（generic 复用 userData.interact / glow 灯光 / spin 转枢轴 / info 派发 `wenmai:asset-info`；关闭时缓动回初始姿态）
5. **接入既有系统**：`catalog.tsx` 增加 `asset` 分类；`diyStore` 增加 editMode/hoverAsset/infoAsset/interactionState 等；
   `DiYLayer` 用 `AssetInstance` 渲染非遗器物；`DiYPanel` 增加「非遗器物」分类（14 张真模型预览卡）。
6. **页面**：`pages/HeritageGallery.tsx` 已加 A09 文化解读卡（监听 `wenmai:asset-info`）与「点击互动 · 名称」底部提示。
7. 已验证：面板 14 卡、莲花灯落位→点击点亮→`interactionState:{active:true}` 持久化、0 控制台异常、`tsc --noEmit` 0 报错。

## 待完成（按优先级）

1. **A09 卡片与悬停提示的浏览器复验**：上次测试 `hit=null`（点击落位可能没生效或模型不在扫描范围），需确认放置成功再点。
2. **surface 摆放**：`placement==='surface'` 的 6 件（C02/D04/E01/E02/E05/F05）应能放在已摆器物的顶面（博古架/展柜/画案）或一层展柜顶，落点用射线打已摆器物/展柜的顶面，记录 `parentInstanceId`。
3. **hang 摆放**：A07 宫灯必须吸附梁架锚点（一层梁架 z≈7.9 或二层顶），无锚点则拒绝并提示。
4. **逐件互动验收**：14 件各执行「添加→落位→点击→再点复位」，截图存 `docs/heritage_gallery/screens/asset-<ID>.png`，并记录 `interactionState` 变化。
   - generic 类（A01/A02/A04/A07/B02/C02/D01/D04/E02/F05）依赖各自 `userData.interact(t)`，点击后应看到对应零件动起来；关闭后缓动回位。
   - glow 类（A05/E05）、spin 类（E01，已建 `Vase_Spin_Pivot`）、info 类（A09）。
5. **多实例**：同款放 2–3 件，确认各自 interactionState 独立、互不干扰（材质已 per-instance clone）。
6. **编辑模式入口**：面板里给「调整位置」按钮（`setEditMode(true)`），编辑态下 AssetInstance 点击只选中、拖动由 DiYLayer 处理。
7. 撤销/重做、器物近景多角度截图（青花/刺绣贴图）。

## 约定与红线

- 不重建第二套场景/渲染器/目录；只扩展现有模块。
- 不改动 15 个画框数据（`wenmai-heritage-gallery-v1`）与用户已保存布展（`wenmai-gallery-diy-v1` 需向后兼容）。
- 不用 PowerShell 改写含中文的源码（会乱码）；用 `write`/`edit` 或 python `io.open(..., encoding='utf-8')`。
- 验证用 managed browser（`manage_ui_browser start`）+ CDP 脚本；截图放 `docs/heritage_gallery/screens/`。
- 不要推送 GitHub，不长期驻留新服务。