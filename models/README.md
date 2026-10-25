# 本地互动模型与交付

互动内容由本机 Ollama 的 **Qwen3-VL** 读取每件成图和其热点裁切区域后生成；不调用其他云端语言模型，也不人工补写作品热点或章节。图像生成使用用户配置的 Qwen Image 服务，与互动分析分开。

**Depth Anything V2 Small** 只负责相对深度估计，辅助生成有限视角的 2.5D 画境。它不撰写文化解读，不恢复遮挡背面，也不提供真实尺度。Small 的上游许可是 Apache-2.0；Base/Large 的许可不同，本项目未捆绑它们。

- [固定版本、文件校验及用途清单](interactive-models.json)
- [官方模型卡](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf)
- [官方项目及许可](https://github.com/DepthAnything/Depth-Anything-V2)
- [Apache-2.0 全文](../licenses/Apache-2.0.txt)

在项目根目录执行：

```powershell
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements-interactive.txt
.\backend\venv\Scripts\python.exe scripts/setup_interactive_models.py
.\backend\venv\Scripts\python.exe scripts/setup_interactive_models.py --check
ollama pull qwen3-vl:4b-instruct-q4_K_M
```

下载器只在显式执行时联网，可用 `--proxy http://127.0.0.1:端口` 设置这次下载的代理；不修改系统代理。模型文件保存于项目 `.cache/models/depth-anything-v2-small/`。后台构建只读取本地固定版本，并校验权重 SHA-256，缺失或损坏时报告失败，不无限等待下载。

Git 源码包含模型接入、依赖、固定 revision、安装校验和许可。权重体积约 99 MB，单独交付，不混进应用源码历史。每件成图随附 `interaction-analysis.json`、`experience.json`、构建报告和 `world/` 资产，记录实际使用的模型、输入图像哈希、深度来源与限制；浏览这些已构建作品无需重新推理。

[本地深度模型交付包与 SHA-256](https://github.com/3331083641-prog/wenmai-huazhang/releases/tag/v2026.10.25) 包含固定权重、配置、模型来源和 Apache-2.0 许可。解压其中的 `depth-anything-v2-small/` 到项目 `.cache/models/`，再执行上面的 `--check`；Ollama Qwen3-VL 另行安装。交付 ZIP 约 92 MB。

如显式设置 `WENMAI_DEPTH_MODE=geometry`，只使用图像与 Qwen 判断生成近似显示深度。此模式会在作品说明标记，不应当成深度模型推理成功；默认 `model` 模式不会静默降级。
