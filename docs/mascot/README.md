# 展馆吉祥物「纹纹」· 进度与验收（第一版）

状态：**第一版已接入展馆、可唤醒可操控，但美术与部分交互仍在收尾，未达最终验收。**

## 已完成

| 项 | 状态 | 说明 |
|---|---|---|
| 获奖作品研究 | ✅ | [research.md](./research.md)。官网是获奖名单公告，无作品图；5 件里只有「狮小炸」有公开文字描述，其余未获取到造型信息，未做视觉推测 |
| 三套概念方案 | ✅ | [design.md](./design.md)。卷云灵猫 28 分 / 剪纸影猫 18 / 瓦猫守灵 20，选定卷云灵猫 |
| Blender 模型 | ⚠️ 第一版 | `assets/mascot/blender/wenmai_mascot_ww.blend`；GLB 788 KB / 9,108 三角面 / 7 材质 / 1 套骨架；三视图与 3/4 视角在 `docs/mascot/previews/` |
| 8 段动画 | ✅ | `Idle 4.0s / Spawn 1.2s / Walk 1.07s / Run 0.8s / Turn 1.33s / Happy 1.5s / Curious 3.0s / Interact 2.0s`，动作名按 GLB 二进制核对 |
| 唤醒入口 | ✅ | 展馆底部空白区「随意点击，唤醒展馆萌宠」，点击后角色从门外跳入并落在馆内空地 |
| 第三 / 第一视角 | ✅ | 默认第三人称跟随；第一人称在角色眼高（实测相机 y≈1.11），第一人称时隐藏角色本体，避免糊镜头 |
| 键位 | ✅ | W/↑ 前进、S/↓ 后退、A/← 左转、D/→ 右转，两套键位等价；Shift 小跑、V 切视角、E 看展品、Esc 退出 |
| 碰撞 | ⚠️ 第一版 | 大厅边界 + 家具/展柜二维障碍盒（从 GLB 网格自动提取 344 个盒子）；尚未逐一验证所有间隙 |
| 室内楼梯 | ✅ 已打通、井口已开 | 见 [stairwell-fix.md](./stairwell-fix.md)：外壳整板 VER_Slab 原本把洞口封死，已拆成四块让出楼梯井；细节见该文档。 | 用模型自带的折返楼梯（INT_ST_*）：A 跑沿 +X 上到后侧平台（y≈1.98），折返 B 跑沿 −X 上到二层 3.6；一上一下都实测过（见下方走位数据） |
| 退出恢复 | ✅ | Esc 或「退出探索」后回到普通看展，OrbitControls 恢复，HUD 消失 |
| 工程 | ✅ | `tsc` 通过、4 个测试文件 44 条全过、`vite build` 通过 |

## 还没做完（下一轮必须先做）

1. **角色造型**：第一版只有腿、没有手臂；口鼻偏尖（略像鼠兔）；耳缘的木刻刀口不明显；胸前青花牌目前是白块，钴蓝纹样没做出来；颈部刺绣项圈过窄。这些是「国赛 IP 水准」的主要差距。
2. **相机手感**：第三人称目前是「高位引导机位」，能看见角色但角度偏俯；靠家具时仍会贴得很近，需要做基于墙体的遮挡淡出（fade）或更聪明的机位。
3. **二层与楼梯通行**：已实测通过——A 跑 (0.35,0.25,3.4) → 平台 (3.05,1.98,3.4) → B 跑 → 二层 (-0.22,3.6,2.62)；反向下楼 y 1.85→1.33→0.81→0.28→0.25 连续无跳变。栏杆尚未做逐格碰撞（只做了楼梯构件的障碍排除）。
4. **展品联动**：靠近画框自动触发 Curious + 打开已有文化卡的逻辑已写，但还没在一次完整走位里录到证据。
5. **动画质量**：Idle/Walk 已有，但要注意脚底打滑（步频与位移是否匹配）与尾巴次级运动。
6. **演示视频与最终对比截图**：尚未录制。

## 关键文件

| 用途 | 路径 |
|---|---|
| 角色模型 | `frontend/public/models/wenmai_mascot_ww.glb` |
| Blender 工程 | `assets/mascot/blender/wenmai_mascot_ww.blend` |
| 角色控制与相机 | `frontend/src/features/heritage-gallery/mascot/MascotCompanion.tsx` |
| 运行参数（出生点/速度/楼梯/展品距离） | `frontend/src/features/heritage-gallery/mascot/mascotConfig.ts` |
| 展馆接入 | `scene/HeritageScene.tsx`（`mascot` 属性）、`pages/HeritageGallery.tsx`（唤醒入口与 HUD） |
| 三视图 | `docs/mascot/previews/{front,side,back,three-quarter}.png` |
| 运行截图 | `docs/mascot/shots/m*.png` |

## 验收做法（下一轮补齐）

1. 走到楼梯上二层，记录 `__mascot.floor` 与高度变化；
2. 靠近任一画框，确认文化卡出现且角色播 Curious；
3. 第一/第三视角各截一张，检查镜头是否被头部遮挡；
4. 录 20–30 秒演示视频：唤醒 → 跳出 → 走动 → 转身 → 上楼梯 → 靠近画框看展 → 切第一视角 → 退出。

截图证据：`m11-cat-visible.png`（第三人称，馆内）、`m12-first-person.png`（第一人称，正对青花画框）。