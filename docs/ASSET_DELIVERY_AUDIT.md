# 素材职责与交付审计

- 唯一编辑源：`assets/style_refs/<style>.png`，用于文化风格介绍。
- 兼容分发目录：`backend/style_refs/` 与 `frontend/public/`。五类文件逐一SHA核对相同；保留现有路径，避免破坏可选InstantStyle与旧部署。`scripts/prepare_style_assets.py`统一分发。
- 实验输入：`docs/examples/<style>/reference.png`，与风格展示图不同；不分发到首页风格卡。
- 实验结果和文化卡：对应目录`generated.png`、`culture_card.png`，以metadata配对。
- 待删除影响范围：五组旧`reference.jpg`仅在旧案例文档引用；文档改为PNG后删除当前副本。旧图仍在任务备份与Git历史中。
- 不删除：已发布iCAN Release、核心代码、文化风格展示图、仍使用的工作台截图和二维码。
- 不纳入此次提交：无关本地历史脚本、缓存、venv、node_modules、本地视频和输出。当前main历史中若有旧大文件，不重写历史隐藏它们。
