# scripts/assets

《纹脉华章》非遗器物资产的**可复现**脚本，属于项目产物，不再放在 `D:\Codex` 临时目录。

## extract_library.py

从 `C:\Users\WPY11\Desktop\5.html`（Gemini 原始资产文件）里**精确抽行**，生成

`frontend/src/features/heritage-gallery/props/assets/library.gen.ts`

- 抽 5 个 CanvasTexture 生成器 + `MAT` + `box/cyl/addFlushSpandrel`；
- 只抽白名单 14 个 builder（`DIY_A01/A02/A04/A05/A07/A09/B02/C02/D01/D04/E01/E02/E05/F05`）；
- 排除件 `DIY_A06 / A10 / B05 / C03 / D05` 的构建代码**不会被写进任何文件**；
- 内置 fixup：木版套印工作台纸张 `Math.pow(u, 1.6)` 的浮点越界钳制（`Math.max(0, …)`），否则整件模型包围盒变 NaN。

用法：

```powershell
python scripts/assets/extract_library.py
```

> 注意：`5.html` 是资产来源，路径写在脚本顶部 `SRC`；换机器时改这一行即可。
> 原始 HTML 保留不动，不要删。

## 相关验证脚本

`scripts/verify/` 下是浏览器端验收脚本（CDP，需要先 `manage_ui_browser start` 拿端口）：

| 脚本 | 作用 |
|---|---|
| `audit14.mjs` | 调 `window.__wenmaiAudit()` 量 14 件的网格/三角面/包围盒 |
| `place_test.mjs` | 面板选器物 → 场景落位 → 写 localStorage |
| `interact_test.mjs` | `__galleryPick` 定位已摆器物 → 点击 → 校验 `interactionState` |
| `surface_test.mjs` | 桌面吸附（博古架顶放梅瓶）回归 |
| `a09_test.mjs` | 展签架文化解读卡 + 悬停提示 |

运行示例：

```powershell
$env:CDP_PORT='<manage_ui_browser 返回的端口>'; node scripts/verify/audit14.mjs
```