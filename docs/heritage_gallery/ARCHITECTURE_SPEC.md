# 纹脉展馆 · 架构规格

> 一句话：**Blender 出模型和坐标，网页只读坐标**。
> 建筑形体、展墙、画框锚点、相机机位全部在 Blender 里定，导出成
> `.glb` + `gallery_layout.json` 两份产物；网页不做任何手写坐标。

---

## 1. 资产管线

```
assets/gallery3d/
├── references/raw/            十张参考图（原件，只读）
├── references/analysis2/      measure_v2.py 的输出（summary.json）
├── scripts/                   建模、导出、验收脚本
├── blender/wenmai_gallery.blend        可编辑工程（1245 对象 / 24294 面）
├── models/wenmai_gallery.glb           中间产物
└── exports/
    ├── wenmai_gallery.glb              最终模型（1,641,424 B）
    └── gallery_layout.json             坐标契约

frontend/public/models/wenmai_gallery.glb          ↑ 网页实际加载的那份
frontend/src/features/heritage-gallery/data/gallery_layout.json   ↑ 网页实际读的那份
```

导出链路（每一步都可重跑）：

| 步骤 | 命令（在 `assets/gallery3d/scripts` 下） |
| --- | --- |
| 重建模型 | `blender.exe -b --factory-startup -P build_all.py -- --no-render` |
| 重定相机 | `blender.exe -b ..\blender\wenmai_gallery.blend -P retarget_cameras.py` |
| 导出坐标 | `blender.exe -b ..\blender\wenmai_gallery.blend -P export_layout.py` |
| 相机审计 | `blender.exe -b ..\blender\wenmai_gallery.blend -P camera_audit.py` |
| 截图体检 | `python shot_health.py` |
| 参考图量测 | `python measure_v2.py` |
| 视角配对 | `python match_views.py` |
| 实现验收 | `python verify_web.py <截图> <参考图哈希前缀>` |

`export_layout.py` 一次写两份 `gallery_layout.json`：`assets/gallery3d/exports/` 存档，
`frontend/src/features/heritage-gallery/data/` 供网页 import。两份内容一致，防止出现
"存档和线上不是同一份坐标"的经典事故。

---

## 2. 坐标契约（整个项目最容易出错的地方）

Blender 与网页的轴向不同，转换**只在导出器里做一次**，网页端不再二次换算。

| 项 | Blender | 网页 |
| --- | --- | --- |
| 位置 | `(x, y, z)`，+Z 向上 | `(x, z, -y)`，+Y 向上 |
| 朝向 | 锚点 rot `θ_b`（绕 Z） | `θ_web = θ_b + π` |
| 展墙局部系 | `(u, v)`，u 沿墙向右、v 向上，原点在墙中心 | 同左，`u,v ∈ [0,1]` |

墙上的点这样落到世界：`wallPointToWorld(wall, u, v, offset)`。
`offset = 0.06` 时画框正好贴在展板表面，往回退会嵌进墙，往外推会悬空。

**`gallery_layout.json` 结构**

```jsonc
{
  "envelope": { "min": [-6.17, -1.05, -6.17], "max": [6.17, 9.65, 6.17] },
  "walls":  [ { "id": "f1-back", "floor": 1, "center": [...], "rotationY": 3.1416,
                "size": [4.65, 2.62] } /* 共 7 面 */ ],
  "frames": [ { "id": "FRAME_F1_001", "floor": 1, "wall": "f1-back",
                "u": 0.8333, "v": 0.5, ... } /* 共 15 个 */ ],
  "cameras":[ { "id": "CAM_Front34", "position": [...], "target": [...], "fov": 38.0 } /* 共 10 个 */ ]
}
```

展墙一共 7 面：一层 4 面（`f1-back/f1-front/f1-left/f1-right`），二层 3 面
（`f2-back/f2-left/f2-right`）——二层正面留给外檐，不做展墙。

---

## 3. 相机与视场角（一条踩过坑的约定）

Blender 的镜头焦距在**横画幅**下定义 fov；Three.js 的 `camera.fov` 是**垂直** fov。
直接把 Blender 的 fov 塞进 `camera.fov` 会让模型小一大圈。

定下来的做法：

- `gallery_layout.json` 里的 `fov` 一律是**水平** fov（Blender 口径，不换算）
- 网页用固定参考比例 `REFERENCE_ASPECT = 4/3`（十张参考图的实际比例）；
  `verticalFov(hfov) = 2·atan(tan(hfov/2) / (4/3))`
- 结果：无论窗口多宽，**4:3 的取景始终与参考图一致**，窗口更宽只是多看到两边。
  这是有意的取舍——参考图是 4:3，不能为了填满 16:10 窗口而改构图比例。

10 个机位（id 与 Blender 相机名对应）：

| 网页 id | 来源 | 用途 |
| --- | --- | --- |
| `exterior` | `CAM_Front34` | 默认机位：3/4 略俯，能看到方形台基 + 正面 + 一侧 + 屋顶 |
| `front` / `back` / `left` / `right` | `CAM_Front` 等 | 四向立面 |
| `top` | `CAM_Top` | 俯视屋面 |
| `floor1` / `floor2` | `CAM_F1` / `CAM_F2` | 两层室内 |
| `ceiling` | `CAM_Ceiling` | 仰视梁架 |
| `eave` | `CAM_Detail_Eave` | 檐下细节 |

相机过渡由 `CameraRig` 做 0.85 s 的 `easeInOutCubic` 插值（位置、目标、fov 同时插），
所以切机位不是"跳"过去。

---

## 4. 屋顶可见性规则

内部机位要能看见楼板，就得把屋顶收起来；但**梁架机位看的正是屋顶本身**，
收掉就剩下天空（这是实测发现的 bug：`ceiling` 机位收起屋顶后整屏 201 luma 的近白画面）。

定稿规则写在 `frontend/src/data/heritageGalleryConfig.ts`：

```ts
export const HIDE_ROOF_PRESETS = new Set(['floor1', 'floor2']);   // 只在看房间时收屋顶
```

`INTERIOR_PRESETS`（机位分组）与 `HIDE_ROOF_PRESETS`（屋顶开关）是两件事，不能合并。

---

## 5. 三渲二实现

- 材质：`MeshToonMaterial` + 自绘 3 阶梯度贴图 `createToonGradient(3)`
- 描边：`onBeforeCompile` 注入**反向外壳**——沿视空间法线外扩固定像素量
  （`DEFAULT_OUTLINE_WIDTH_PX = 1.6`，按屏幕分辨率换算，不随距离变粗），
  描边色 `OUTLINE_COLOR = #1a1208`，并且 `outline.raycast = () => {}` 让它不参与拾取
- 分档：`THREE_TONE_STOPS = [0.42, 0.74, 1]`，暗部不做死黑（`TONE_FLOOR = 0.42`），
  这是"三渲二"和"纯卡通"的区别
- 全部逻辑集中在 `scene/sanzhuan2.ts`，`applySanzhuan2(root)` 对整棵 GLB 树一次性处理，
  幂等、可释放（`disposeToonResources`）
- **GLB 里不带任何材质表现**：Blender 的 toon 节点树过 glTF 会丢，色彩关系必须
  在网页端重建。所以 `.blend` 负责形体与物体命名，网页负责表现。

---

## 6. 展陈系统（第二大功能）

```
点击画框 → curationStore.selectFrame(id)
        → GalleryPanel 打开（右侧抽屉）
        → 风格筛选 → 选作品 → assignArtwork(id, artworkId)
        → 贴图热替换（不重载模型）
        → 拖动 → moveFrame(id, u, v)（拖拽期间 OrbitControls 关闭）
        → 恢复默认 / 重置全部
        → persist 到 localStorage（key: wenmai-heritage-gallery-v1）
```

- **拾取与装饰分离**：画框的交互几何体与边框装饰是两个节点，
  装饰件 `raycast = () => {}`，保证点到框上一定是选中，不会因为装饰面片挡住而失灵。
- **贴墙约束**：拖拽时把屏幕射线打到该画框所在墙的平面上，得到 `(u,v)` 后
  再 `clampToWall()`，所以画框永远贴在墙上，不会拖到墙外或穿进楼板。
- **只有坐标进持久化**：`partialize` 只存 `assignments` 与 `positions`，
  其余（选中态、详情态）不落盘，刷新后不会莫名其妙弹出一个抽屉。
- **画框 ID 稳定**：`FRAME_F1_001`–`FRAME_F1_008`、`FRAME_F2_001`–`FRAME_F2_007`，
  与 GLB 里的空物体同名，布局数据换版本也不会串位。

作品来源是项目里真实的 5 件案例（`frontend/src/data/galleryArtworks.ts` 从 `savedCases`
派生：朱仙镇木版年画、汴绣纹样、宋画青绿山水、青花瓷纹样、中国剪纸）。
**不复制参考图里的画作**，画框里的图全部来自本项目的真实作品。

---

## 7. 性能

| 手段 | 现状 | 说明 |
| --- | --- | --- |
| 同材质合批 | 15 个合并网格 / 19 个材质 | 建筑上万个构件合成 15 个 draw batch |
| 运行时规模 | 37 网格 / 19 材质 / 41,192 三角形 | 这是网页实测的 `__galleryStats` |
| DPR 上限 | `dpr={[1, 1.8]}` | 高分屏不无脑 ×2 |
| 阴影 | 单方向光 2048² + `ContactShadows frames={1}` | 影只烘一次，不每帧重算 |
| 按机位卸屋顶 | `layers.roof` 整组隐藏 | 室内机位少画一整个屋顶 |
| 资源释放 | `releaseGalleryAssets` + `disposeToonResources` | 卸载页面不留 GPU 泄漏 |
| 并行加载 | `useGLTF.preload` | 进页面前就开始拉 GLB |

已知取舍：**没有做路由级 `React.lazy` 拆包**。试过，`Suspense` 包住 Canvas 会导致
WebGL 上下文丢失（白屏），已回退；首包因此仍是 1.75 MB（gzip 509 kB）。
要做正确需要把 Canvas 放在稳定父节点下只切 UI，风险大于收益，本轮不做。

---

## 8. 目录与文件职责

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `pages/HeritageGallery.tsx` | 231 | 页面骨架：模式 / 机位 / 沉浸 / 图库抽屉 |
| `scene/HeritageScene.tsx` | 336 | Canvas、天空、光照、相机过渡、拾取探针 |
| `scene/GalleryModel.tsx` | 79 | GLB 加载、去相机节点、分图层、三渲二应用 |
| `scene/GalleryFrame.tsx` | 205 | 单个画框：贴图热替换、拖拽、贴墙约束 |
| `scene/sanzhuan2.ts` | ~500 | 三渲二材质与描边，整套风格只在这里 |
| `scene/materials.ts` | 163 | 调色板、天空贴图、铺装贴图 |
| `scene/primitives.tsx` | 82 | ToonBox / ToonCylinder 基础件 |
| `state/curationStore.ts` | 113 | zustand + persist，唯一的状态真源 |
| `components/GalleryPanel.tsx` | 224 | 右侧图库：风格筛选、选画、取下、恢复 |
| `components/ArtworkDetail.tsx` | 111 | 作品详情 |
| `data/heritageGalleryConfig.ts` | — | 读布局 JSON，导出墙/框/机位与坐标换算 |
| `types/index.ts` | 85 | 共享类型（`GalleryMode` 也在这里） |

> 已删除：`scene/Base.tsx`、`scene/Pavilion.tsx`（第一版占位组件，无人引用）。
> 保留 `materials.toonMaterial`：`GalleryFrame` 的展墙底板还在用。

---

## 9. 浏览模式

| 模式 | 屋顶 | 可见机位 | 用途 |
| --- | --- | --- | --- |
| 外观 | 完整 | 3/4、正面、背面、左右、俯视 | 看建筑本身 |
| 内部 | 按机位收起 | 一层、二层、梁架、檐下 | 走进去 |
| 布展 | 按机位收起 | 3/4、一层、二层 | 点画框换画 |

「沉浸模式」把界面全部隐藏，只留一个「显示界面」按钮，Esc 退出。
另外还有鼠标：左键旋转、滚轮缩放、右键平移，`minDistance 2.4 / maxDistance 52`。