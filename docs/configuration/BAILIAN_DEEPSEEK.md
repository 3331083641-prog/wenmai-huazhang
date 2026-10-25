# 百炼 DeepSeek V4.1 Flash 1017 配置指南

核对日期：2026-10-25。服务供应商为阿里云百炼，模型 ID 为 `deepseek-v4.1-flash-1017`。

> 当前用户已改用 [DeepSeek 官方 API](DEEPSEEK_OFFICIAL.md)。本页仅保留百炼可选配置，不能将两家密钥、地址和模型 ID 混用。

客户端已经实现官方与百炼两种供应商的配置隔离、图像输入和受限复审。**本机成功验证的是官方服务；百炼模式尚未完成有效密钥实测**，不能把官方结果当作百炼通过。互动内容仍由本地 Qwen3-VL 生成，深度由本地 Depth Anything V2 Small 辅助，DeepSeek 仅复审并建议有限参数。

## 1. 密钥填写位置

真实密钥只放在本机文件：

```text
D:\wenmai-huazhang\backend\.env
```

该文件已被 Git 忽略。公开模板是 [backend/.env.example](../../backend/.env.example)，其中密钥必须保持为空。

用文本编辑器打开本机 `backend/.env`，在末尾增加下面三项；如果已有同名项，修改原有行，避免重复定义。保留已有配置，尤其是生图所用的 `DASHSCOPE_*` 和本地模型所用的 `QWEN_VL_*`。

```dotenv
# 把下面的中文提示替换为你的真实百炼密钥，仅在本机编辑
DEEPSEEK_PROVIDER=bailian
DEEPSEEK_API_KEY=在这里粘贴你的百炼API密钥

# 北京地域示例：替换业务空间ID，实际地址以百炼控制台为准
DEEPSEEK_BASE_URL=https://你的业务空间ID.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
DEEPSEEK_MODEL=deepseek-v4.1-flash-1017
```

不要将上面的中文占位内容作为有效配置。文件名是 `.env`，不是 `.env.txt`；保存为 UTF-8。密钥值不加 `Bearer ` 前缀，不带首尾空格。

若文件不存在，可在项目根目录执行以下命令；它只在不存在时复制模板：

```powershell
if (-not (Test-Path -LiteralPath '.\backend\.env')) {
    Copy-Item -LiteralPath '.\backend\.env.example' -Destination '.\backend\.env'
}
```

## 2. 在百炼控制台确认三个信息

| 配置项 | 如何填写 |
|---|---|
| `DEEPSEEK_API_KEY` | 百炼 API Key，须有目标模型访问权限。可独立创建；若现有密钥的权限和地域均匹配，也可在此填写同一值。 |
| `DEEPSEEK_BASE_URL` | 控制台提供的 OpenAI 兼容 Base URL，匹配密钥所属地域、计费方案和业务空间。 |
| `DEEPSEEK_MODEL` | 填 `deepseek-v4.1-flash-1017`，保留 `-1017` 固定版本后缀。 |

百炼的业务空间专属地址通常形如 `https://<业务空间ID>.<地域>.maas.aliyuncs.com/compatible-mode/v1`。本指南给出北京地域示例，不能据此判断你的密钥属于北京；其他地域应从对应控制台复制地址。

Base URL 在 `/compatible-mode/v1` 结束，后续客户端再调用 `/chat/completions`，避免重复拼接路径。百炼密钥使用百炼端点，不填写 DeepSeek 官方直连地址 `https://api.deepseek.com`。

项目生图当前使用的 `DASHSCOPE_BASE_URL` 有独立格式校验。请保留该项，为 DeepSeek 另填 `DEEPSEEK_BASE_URL`，不要直接替换已有生图地址。

## 3. 本项目的保存与接入约定

- 密钥留在 `backend/.env`，不放在前端 `.env`、任何 `VITE_*` 变量、React/HTML 源码、浏览器存储或文档中。
- 不把密钥发送到聊天、截图、终端历史或 GitHub。后续验证程序只报告是否配置、错误类别和调用结果，不输出密钥或请求认证头。
- `.env.example` 可以公开，真实 `.env` 不提交、不打包。不要运行输出整个 `.env` 的诊断命令。
- 后端读取这些变量；设置 `DEEPSEEK_REVIEW_ENABLED=true` 才会执行复审。启用控制、白名单、超时、每日预算和输出校验见 [固定工作流](../interactive/DEEPSEEK_REVIEW_WORKFLOW.md)。
- 当前后端默认从 `backend/.env` 载入环境变量；`WENMAI_ENV_FILE` 可指定另一份配置。使用自定义配置路径时，应在该文件内填写，且确保它同样不会进入版本控制。

可以在项目根目录执行不显示密钥的 Git 检查：

```powershell
git check-ignore backend/.env
git ls-files -- backend/.env
```

第一条应输出 `backend/.env`；第二条应无输出。第二条若列出路径，说明文件已被跟踪，应先处理提交风险。

## 4. 填写后如何判断状态

保存配置后重启后端，检查 `/health` 中 `deepseekReview` 的供应商、模型、enabled 与 configured。该检查不产生付费请求，也不能证明模型权限或画境质量。

启用复审后可针对一件已有作品按 [固定流程](../interactive/DEEPSEEK_REVIEW_WORKFLOW.md) 做真实验证；结果以单件报告为准。本次百炼调用未完成有效密钥验证，已切换官方服务，不能据此宣称百炼接入通过。

后续调用若出现错误，优先核对：401 的密钥、地域和计费方案；403 的模型权限；404 的模型 ID 与接口路径；429 的额度与限流。以实际响应和百炼错误码说明为准，避免自动反复请求。

## 5. 官方参考

以下信息来自百炼官方文档，具体可用性以账号控制台为准：

- [DeepSeek API 调用参考](https://help.aliyun.com/zh/model-studio/deepseek-api)：固定版本 ID、图像输入支持、兼容协议与地域地址。
- [Base URL 总览](https://help.aliyun.com/zh/model-studio/base-url)：密钥与地域、计费方案的匹配要求。
- [获取与配置百炼 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)：在百炼控制台创建和管理密钥。

后续模型调用使用百炼的接口能力和参数，不能直接照搬 DeepSeek 官方直连 API 的全部参数。
