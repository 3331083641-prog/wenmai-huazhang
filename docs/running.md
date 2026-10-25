# 部署与常见问题

## 环境与安装

应用需要 Python 3.10+、Node.js 20.19+ 或 22.12+；运行现有前端 TypeScript 测试建议 **Node.js 22.18+ 或 24**。本次检查环境为 Python 3.12.4、Node.js 24.15.0。实时生成需要个人百炼配置，视觉理解另需 Ollama 模型；浏览保存案例、文化互动、文创模板与三维展馆无需生成密钥。

Windows 在项目根目录运行或双击：

```powershell
.\setup_windows.cmd
.\check_environment.cmd
.\start_windows.cmd
# 使用完毕
.\stop_windows.cmd
```

安装脚本创建 `backend/venv`、安装 `backend/requirements.txt`，按锁文件执行 `npm ci` 并准备五类风格素材，不下载 Ollama 模型。首次安装需要下载依赖。启动器从后端 8000–8010、前端 5173–5174 选择空闲端口，打印实际地址，默认进入作品展厅。停止时核对 PID 和 UTC 创建时间，按先子后父顺序停止自身记录的项目进程树，保留 Ollama。运行记录在 `.cache/windows_launcher/`。`npm run clean` 现在使用 Node 删除可再生的前端 `dist`，兼容 Windows。

## 私有配置

DeepSeek 画境复审优先使用 [官方 API 配置指南](configuration/DEEPSEEK_OFFICIAL.md)，用户本机已选择官方服务。另保留 [百炼配置说明](configuration/BAILIAN_DEEPSEEK.md)。配置正确与实际复审通过分别验证，密钥不进入前端。

以 `backend/.env.example` 创建本机 `backend/.env`，设置个人 `DASHSCOPE_API_KEY` 和百炼控制台提供的华北 2（北京）业务空间专属 `DASHSCOPE_BASE_URL`（HTTPS 域名，以 `.cn-beijing.maas.aliyuncs.com` 结尾）。具体域名和模型以个人服务开通情况为准。密钥仅进入后端，不写入前端、截图或 Git。

本地视觉理解设置 `QWEN_VL_ENABLED=true`、`QWEN_VL_BASE_URL=http://127.0.0.1:11434`，`QWEN_VL_MODEL` 与本机安装名一致。默认模型为 `qwen3-vl:4b-instruct-q4_K_M`。尚未安装时由使用者执行 `ollama pull qwen3-vl:4b-instruct-q4_K_M`；已有模型无需重下。`ollama serve` 仅在服务未运行时启动。

环境检查探测默认 Ollama 地址和模型，等待上限 8 秒；连接或超时失败不能证明模型未安装。实际应用配置以运行中后端 `/health` 为准。模型列出不等于真实看图推理通过，性能受内存、显存与图片大小影响。视觉分析默认超时 180 秒；失败时保留已生成图片并明确标记模板文化卡。

## 手动启动与验证顺序

先创建后端环境与本机配置，再安装前端：

```powershell
python -m venv backend/venv
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements.txt
# 仅首次创建，已有配置不要覆盖
Copy-Item backend/.env.example backend/.env
python scripts/prepare_style_assets.py
Set-Location frontend
npm ci
```

验证顺序：后端 `/health` → 后端 `/generate` → 前端 `npm run dev` → 浏览器。先在 `backend` 用项目虚拟环境执行 `python -m uvicorn app:app --host 127.0.0.1 --port 8000`，检查 `http://127.0.0.1:8000/health`。通过 `/docs` 查看 `/generate` 请求结构；合法真实请求可能产生费用，不要批量重试。无密钥返回明确错误不算真实推理通过。随后在另一终端进入 `frontend` 执行 `npm run dev`，打开终端打印的地址。

macOS / Linux 使用 `python3 -m venv backend/venv`、`backend/venv/bin/python` 与对应终端命令，不使用 Windows `.cmd`。

正式路由为 `/` 首页、`/creator` 创作、`/styles` 风格库、`/gallery` 展厅、`/products` 文创、`/scenarios` 场景、`/about` 介绍、`/experience/:id` 热点、`/story/:id` 三折叙事、`/wander/:id` 画境和 `/heritage-gallery` 三维展馆。

## GitHub Pages

`.github/workflows/pages.yml` 在 `main` 推送后安装依赖、类型检查并构建：

```powershell
# frontend 目录
$env:VITE_STATIC_SHOWCASE='true'
$env:VITE_PUBLIC_BASE='/wenmai-huazhang/'
npm run lint
npm run build
```

Pages 使用 HashRouter，例如 `/wenmai-huazhang/#/gallery`；静态资源沿用仓库子路径。它展示保存案例与前端互动，明确禁止实时生成，不运行 FastAPI、Ollama 或深度模型。`npm run preview` 也应使用该子路径。回到本地开发前从当前终端移除这两个变量，或使用新终端。

## 新案例后台构建的边界

真实生成默认保存图片、文化卡与元数据至 `docs/examples/<时间标识案例>/`，展厅通过 `/cases` 拉取。`AUTO_SAVE_CASES=false` 可关闭保存，内置五件案例受删除接口保护。

`AUTO_BUILD_INTERACTIVE=true`（默认）启动后台线程执行 `scripts/interactive/ingest_case.py --refresh <case>`，进度查 `/interactive-jobs`。流水线生成三折叙事、自动热点和画境；定位标为 approximate / pending，需人工复核。深度是单图估计的 2.5D 视差素材。

基础依赖包含 NumPy。完整自动构建还需安装本地深度推理依赖和固定版本权重：

```powershell
.\backend\venv\Scripts\python.exe -m pip install -r backend/requirements-interactive.txt
.\backend\venv\Scripts\python.exe scripts/setup_interactive_models.py
.\backend\venv\Scripts\python.exe scripts/setup_interactive_models.py --check
```

下载器只在手动安装时联网；后台默认 `WENMAI_DEPTH_MODE=model`，只读取本地权重，缺失会明确失败。模型、许可和交付方式见 [模型说明](../models/README.md)。已构建案例无需模型即可浏览。`AUTO_BUILD_INTERACTIVE=false` 可显式关闭自动构建，但这不属于完整创作模式。

任务状态持久化到 `backend/outputs/interactive_jobs.json`；服务重启后保留历史，中断的任务会明确标记失败，可在展厅重试。每件成图先由本地 Qwen3-VL 读取，再逐热点读取原图及实际裁切区域，生成专属观察和三章故事；文化风格资料仅提供背景，不套用通用章节。不使用其他云端文本模型，也不人工补写作品内容。

展厅通过 `/cases` 持续刷新，后台完成后自动开放三个入口，无需重启前端。新画境资产由后端 `/interactive/` 动态提供，避免依赖 Vite 启动时的静态目录索引。构建失败不撤销已保存图像，也不会把旧文件误报为新构建成功。Pages 只能展示构建时已打包的案例，新增作品仍需重新部署。

## 问题处理

| 现象 | 检查项 |
| --- | --- |
| 前后端断连 | 实际端口、`/health`、`VITE_API_BASE_URL`；一键启动自动传递地址 |
| 生成失败 | 个人服务开通、额度、配置和网络；错误返回不算生成通过 |
| 文化卡标记模板 | Ollama、配置模型与后端健康状态；模板不是实际看图结论 |
| 风格图不显示 | 执行 `scripts/prepare_style_assets.py`，检查规范素材 |
| 新作缺互动入口 | 查 `/cases/{caseId}` 与 `/interactive-jobs`、本地 Qwen3-VL、深度依赖及权重；失败时重试，不需要重启 dev |
| 画境降为静态 | WebGL2、低性能设备或低帧率触发降级，仍可阅读说明 |
| 展馆打不开 | 检查 WebGL、GLB 与控制台；展馆是预制场景，不是图片重建 |
| 改配置无效 | 重启相应服务，构建变量需重新构建 |

公网部署后端需自行配置服务地址、访问控制与 HTTPS。仓库不共享作者的模型账号。
