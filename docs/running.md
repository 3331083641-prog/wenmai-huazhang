# 部署与常见问题

## 配置

以 `backend/.env.example` 为模板，在本机建立 `.env`。填写自己的 `DASHSCOPE_API_KEY` 和百炼控制台提供的华北2（北京）业务空间专属 `DASHSCOPE_BASE_URL`（HTTPS 域名，以 `.cn-beijing.maas.aliyuncs.com` 结尾；不能填写公共域名），保留默认生成 provider 和模型。本地 Ollama 启动后，使用与安装一致的 `QWEN_VL_MODEL`。密钥只进入后端配置。

Windows 启动脚本根据脚本所在位置定位项目，不依赖固定盘符。macOS／Linux 使用 README 中的终端命令。前端依赖可由 `npm ci` 按锁文件安装。

## 问题处理

| 现象 | 检查项 |
|---|---|
| 前端无法连接后端 | 确认8000端口、`/health` 和 `VITE_API_BASE_URL` |
| 生成接口报错 | 检查百炼账号额度、API Key及服务网络；界面保留错误反馈 |
| 文化卡来自模板 | 检查 Ollama 是否启动、模型名称、设备内存和本地视觉服务状态 |
| 风格图无法显示 | 确认 `frontend/public` 和 `backend/style_refs` 的五类素材完整 |
| 更改配置没有生效 | 重启相应前端或后端进程 |

网页应用在本机运行；公网部署需自行设置服务地址、访问控制及 HTTPS。开源仓库不共享作者的模型服务账号。
