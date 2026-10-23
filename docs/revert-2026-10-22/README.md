# 2026-10-22 撤销记录：画境漫游回到 2.5D

按要求撤销了此前几轮加进「画境漫游」的新方案，只保留 2.5D 分层视差版本。

## 撤掉了什么

| 方案 | 原位置 | 现状 |
|---|---|---|
| Wet Paint Flow（油画笔触 / 湿颜料 / 青花·汴绣·剪纸工艺分支） | `frontend/src/features/wet-paint/` | **已彻底删除，不留副本** |
| 2D 生命化微动画（瑞猫呼吸/眨眼/摆尾/热点联动） | `frontend/src/features/living-painting/` | **已彻底删除，不留副本** |
| 三维画境（`PaintingWorld3D`、4 个 GLB、场景数据） | `frontend/src/features/painting-world/three/` | **已彻底删除，不留副本** |
| 三维版文档、截图、演示视频、构建脚本 | `docs/world3d/`、`scripts/world3d/` | **已删除** |
| 三维版读图产物（ScenePlan） | `docs/examples/songhua/scene-plan*.json` | **已删除** |
| 一次性清理脚本 | `scripts/cleanup_woodblock.py` | 已删除 |

`frontend/src/features/` 现在只剩 `culture-experience`、`heritage-gallery`、`painting-world`（纯 2.5D）。

## 现在的画境漫游

- 五件作品全部走 **2.5D 分层视差**（`PaintingWorld`）：单图深度估计 + 分层错位，拖拽观察、滚轮前后、点击热点读文化解读、底部「走进下一卷」。
- `Wander.tsx` 已去掉 `PaintingWorld3D` 与 `THREE_D_WORLDS`，`?engine=3d` 不再是任何入口（带参数访问仍是 2.5D）。
- 没有残留的 wet-paint / living-painting / three 画境引用。

## 验证

| 项 | 结果 |
|---|---|
| `/wander/zhuxianzhen-ruimao` | 2.5D 正常：拖拽观察、滚轮前后、点击元素、视角复位、六个热点、走进下一卷 |
| `/wander/songhua-yunhe` | 2.5D（`__paintingWorld` 存在、`__paintingWorld3D` 不存在） |
| `/wander/songhua-yunhe?engine=3d` | 仍是 2.5D，三维入口已不存在 |
| `/wander/qinghua-dieyun` | 2.5D 正常 |
| `tsc --noEmit` | 通过 |
| `node --test`（4 个测试文件） | 44 条全过 |
| `vite build` | 通过；`dist/assets` 里已无 `.glb` |

截图：`docs/revert-2026-10-22/cat-2.5d.png`（瑞猫迎春 2.5D 进入后界面）。

## 说明

- 本次只动「画境漫游」，展馆、图库、AI 创作、CultureCard、一图一境等功能未改动。
- 过程中发现 `heritage-gallery` 两处语法破损（`catalog.tsx` 的 `<Rod>` 少一个 `}`、`HeritageScene.tsx` 少一个 `</div>`），已顺手修好，否则整站会白屏；该目录是另一轮未提交的新增工作，其余内容未动。
- wet-paint / living-painting 的源码、文档、截图与演示视频已全部删除，`docs/_archive/` 目录本身也已移除；三维版同样没有留任何副本。
- 全程本地操作，未执行任何 git 操作（无 commit / push / 远程发布）。