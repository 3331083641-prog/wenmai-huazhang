# 工程检查记录（2026-10-24）

本记录对应本地正式入口 `frontend/src/App.tsx`、`backend/app.py`、Windows 一键脚本与 `.github/workflows/pages.yml`。工程检查没有启动或停止服务，没有发起云端生成；运行服务和浏览器验收另见本次仓库审计记录。工程整理前已备份启动器、package.json 和两份技术说明至本机 `.backup/audit_sync_20261024/engineering/`，备份不纳入源码发布。

## 实际执行结果

| 检查 | 结果 | 验证范围 |
| --- | --- | --- |
| 前端 `npm test` | 44 项通过，0 项失败 | 案例合并与字段兜底、文化来源引用、五件互动作品、画境清单、热点几何、数据 schema、首页作品图与路由对应关系 |
| 前端 `npm run lint` | 通过 | TypeScript `tsc --noEmit`，不是 ESLint |
| 前端 Pages 配置 `npm run build` | 通过 | `VITE_STATIC_SHOWCASE=true`、`VITE_PUBLIC_BASE=/wenmai-huazhang/`，与现有 Pages 工作流一致 |
| 后端 `python -m unittest discover -s tests -v` | 20 项通过，0 项失败 | 五组真实案例图片及 SHA-256、文化卡配对、缺密钥、失败不伪装成功、视觉理解不可用的明确降级、参考图传递、图片有效性、主体约束 |
| Windows 启动器 PowerShell 语法检查 | 通过 | PowerShell AST 解析无错误 |
| Windows 启动器 `-Action check` | 通过 | 输出环境与配置是否存在；不输出配置值 |
| Windows `npm run clean` | 通过 | 确认目标为项目 `frontend/dist` 后实际清理可再生产物 |

以上离线测试、类型检查和 Pages 构建在兼容修复后已完整重跑：前端仍为 44/44、后端仍为 20/20，最终构建 30.63 秒完成，命令均以 0 退出。已额外确认构建首页引用的脚本、样式、favicon，以及实际使用的展馆 / 吉祥物 GLB 文件存在。源码差异 `git diff --check` 通过。运行服务和浏览器表现由主验收单独记录，不能用构建成功替代。

实际测试环境为 Python 3.12.4、Node.js 24.15.0。后端使用项目已有 `backend/venv/Scripts/python.exe`。npm 缓存指向项目 `.cache/npm`，构建产物 `frontend/dist` 和运行日志不属于源码交付。

后端测试在执行前检查了源码：外部生成请求被 `unittest.mock` 替换，测试图片写入临时目录，不会把测试图片发布为真实案例。上述通过结果不代表本轮完成了云端真实生成或本地视觉推理。

## Pages 与静态资源

工作流保留 `main` 推送部署，Node.js 22 环境、`npm ci`、类型检查与 Vite 构建；通过 Pages 官方 artifact/deploy action 发布，不影响既有发布方式。静态构建使用 HashRouter，实时本地构建使用 BrowserRouter。首页、风格库与画境资源已有 `BASE_URL` 处理。

构建输出的 `index.html` 已确认脚本、样式和 favicon 均使用 `/wenmai-huazhang/` 前缀。五件案例的画境清单存在，来源与字段结构通过离线测试。Pages 上的云端实时生成被显式禁用，展厅仍可读取内置案例。

首轮审计发现 `Experience.tsx`、`Story.tsx`、`Wander.tsx` 和 `CultureExperienceViewer.tsx` 合计 7 处返回展厅链接写为 `href="/gallery"`，子路径部署会跳到域名根目录。本次已统一内部导航为 React Router Link，并补齐画境工具栏、错误边界、故事章节跳转等相关位置；展馆与吉祥物 GLB 使用 BASE_URL，资源解析避免重复添加前缀并保留绝对 URL。修复后的类型检查、测试和 Pages 构建结果见最终执行记录，具体视觉表现以浏览器验收为准。

## Windows 启动脚本

`setup_windows.cmd`、`start_windows.cmd`、`stop_windows.cmd`、`check_environment.cmd` 均以自身目录定位 `scripts/windows_launcher.ps1`。启动器检查 Python / Node 版本，创建项目 venv、安装依赖、从示例配置创建本地配置，并同步规范风格素材。

启动器启动后台隐藏进程，记录 PID 和创建时间；停止时统一转为 UTC ticks 核对，兼容 Windows PowerShell 5 将 JSON 时间解析为字符串与 PowerShell 7 解析为 DateTime 的差异。实测发现旧版字符串对比在 PowerShell 7 不能识别已记录进程，本次已修复停止、重复启动检测与异常清理三处匹配。

Windows venv 的 Python 启动器还可能启动实际监听端口的子进程。本次新增停止进程树：先验证记录根 PID 与创建时间，再读取父子 PID 快照，捕获后代的 PID 和创建时刻；先子后父停止，每个进程停止前再次核对创建时间。不会按名称全局清理，PID 复用和创建时间不合理的进程会跳过。它不停止 Ollama。端口仍从 8000–8010 与 5173–5174 中选择，前端接收实际 API 地址。

`scripts/verify/test_windows_launcher_identity.ps1` 只提取辅助函数并使用假进程数据，不执行启动器动作，也不查询或停止真实进程。15 项回归分别在 Windows PowerShell 5.1 与 PowerShell 7.6.5 通过，覆盖 ISO 字符串、DateTime、DateTimeOffset、JSON 实际类型、时区、1 tick 差异、PID 复用、后代顺序、无关进程、已消失子进程。修复后再次运行后端 20 项回归和启动器 check 均通过，真实启动停止由主验收复测。

本轮未执行 `setup` 的重新安装，也未执行 `start` / `stop`，避免与本次真实运行验收冲突。对应运行行为应结合最终服务验收报告判断，不能将源码检查写成完整启动停止验证。

## 限制与后续优化

- Pages 构建成功但主 JavaScript 约 1.89 MB（gzip 约 554 KB），Vite 提示大包；后续可在独立任务拆分 3D 与页面入口，本次无需大改架构。
- Zod 依赖中的 PURE 注释引发 Rollup 提示，构建自动移除相关注释，未导致失败。
- 运行现有前端 `.ts` 测试建议 Node.js 22.18+ 或 24；原启动器较低的 Node 下限用于应用构建，不等于测试运行器的兼容下限。
- `npm run clean` 已改用 Node `fs.rmSync`，先确认目标为项目 `frontend/dist`，再实际清理旧产物并重新构建。
- 启动器 Ollama 检查等待从 3 秒调整为 8 秒，与后端健康探测一致。错误文案区分连接/超时/响应失败与默认模型未列出；检查失败不推断模型未安装，也不替代真实推理测试。
- 工程环境检查时 Ollama 请求未通过；这是检查时点的结果，最终本地推理状态以主验收的真实服务记录为准。
- 所有原始测试与构建日志保存在本地 `logs/engineering_checks_20261024_*.log`，不建议将运行日志提交 GitHub。
