# 五馆观器 · 水院漫游

[下载可直接运行的展馆](<https://github.com/3331083641-prog/wenmai-huazhang/releases/download/pavilion-v15-gallery-access/pavilion-viewer.zip>)。解压后在包含 `web` 的目录运行 `python -m http.server 8731 --bind 127.0.0.1`，浏览器打开 [五馆观器](http://127.0.0.1:8731/web/index.html)。

主殿与五座展馆各自有独立的双向开关交互。在漫游中靠近门口，点击门或出现的按钮即可开关。WASD 行走、Shift 疾行、空格跳跃。澄怀轩和素肌堂各有两跑楼梯，沿后墙上第一跑，在平台折返上第二跑即可进入二层回廊。入池后 C 或 Ctrl 下潜、空格上浮。

## 模型与构建

网页及 Blender 参数化源码随此目录版本化。大文件在同一版本的 [Release](https://github.com/3331083641-prog/wenmai-huazhang/releases/tag/pavilion-v15-gallery-access) 中提供。`pavilion-viewer.zip` 包含完整离线网页、GLB 和清单。`pavilion-blender.zip` 包含 Blender 场景和相对路径贴图。Release 文件的 SHA-256 见 `SHA256SUMS.txt`。

从此目录重建时，使用 Blender 5.2.2 执行 `blender -b --factory-startup --python-exit-code 1 --python src/build_v13.py -- --audit-overlap --out <输出目录>`。导出 62 个网格、2,589,029 个三角面。[模型回读](verification/readback.json) · [楼梯往返、逐门通行与漫游复验](verification/results.json)
