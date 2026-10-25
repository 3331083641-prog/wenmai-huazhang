# DeepSeek 官方 API 配置

核对日期：2026-10-25。用户已选择 DeepSeek 官方服务，Qwen Image 生图继续使用原百炼配置。

## 填写位置

打开本机文件 `D:\wenmai-huazhang\backend\.env`，找到 `DEEPSEEK_API_KEY=`，仅在等号后粘贴 DeepSeek 官方控制台创建的 API Key。不要把接口网址填进密钥项，不加 `Bearer ` 前缀，不把密钥发送到聊天。

本机接口地址和模型 ID 已改为官方配置；公开的 [配置模板](../../backend/.env.example) 中密钥保持为空：

```dotenv
DEEPSEEK_PROVIDER=official
DEEPSEEK_API_KEY=在本机填入DeepSeek官方API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_REVIEW_ENABLED=true
DEEPSEEK_MAX_REVIEW_CALLS=3
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TIMEOUT_SECONDS=180
```

官方文档要求使用模型 ID `deepseek-flash`，当前由 DeepSeek-V4.1-Flash-1017 提供服务并支持图像输入。`deepseek-v4.1-flash-1017` 是此前百炼模式的模型 ID，不直接沿用到本配置。官方路由别名以后可能更新，实际请求与响应模型名会写入复审报告。

`DEEPSEEK_BASE_URL` 可用官方根地址或 `/v1` 兼容地址，客户端追加 `/chat/completions`；不填写整个 Chat Completions 请求路径。密钥、供应商和地址必须匹配。不要更改生图的 `DASHSCOPE_API_KEY`、`DASHSCOPE_BASE_URL`、`DASHSCOPE_IMAGE_MODEL` 或本地 `QWEN_VL_*`。

## 状态与验证

本机已使用官方密钥成功发送真实图像请求，并取得针对青花丹顶鹤可见内容的回复。自动复审已接入后台，详见 [固定工作流与依赖](../interactive/DEEPSEEK_REVIEW_WORKFLOW.md)。配置检查成功、真实 API 连通、单件画境质量通过是三个独立状态；`/health` 仅反映第一项。

`backend/.env` 已被 Git 忽略，不会随源码上传；公开模板不存放真实密钥。更换密钥后须重启后端。本项目不会在浏览器、控制台或报告中显示密钥。

## 官方参考

- [首次 API 调用](https://api-docs.deepseek.com/)：官方地址、`deepseek-flash` 路由及当前对应模型版本。
- [官方图像输入](https://api-docs.deepseek.com/guides/vision/)：真实图像输入格式。
- [官方控制台](https://platform.deepseek.com/)：创建 API Key、查看余额与用量。

实际调用有费用；每件复审最多三轮，独立限制输出长度与超时，优化不会为了调参重复生成图片。未达到门槛会保留“待完善”，接口或浏览器失败会保留“未验证”。
