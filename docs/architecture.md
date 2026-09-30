# 架构与接口

## 请求流程

React 将主题、风格、参考图、负向提示、强度、构图和用途提交给 FastAPI。Pydantic 校验输入；Prompt Builder 组织文化风格资料与用户约束；DashScope provider 提交 `messages`、图像条件及 `negative_prompt`，接收真实图像。

图像保存后，本地 Ollama Qwen3-VL 读取图片数据，返回主体、主色、构图、视觉特征与文化解读。前端组织 CultureCard，并将同一作品传入 ProductStudio 的载体模板。

## 接口

| 接口 | 方法 | 用途 |
|---|---|---|
| `/health` | GET | provider、本地图像理解与素材状态 |
| `/generate` | POST | 真实生成、视觉分析与文化卡 |
| `/analyze-image` | POST | 参考图尺寸、色彩等基础统计 |
| `/outputs/*` | GET | 本机生成文件 |
| `/style_refs/*` | GET | 风格参考素材 |

生成字段：`theme`、`style`、`styleName`、`outputType`、`styleStrength`、`compositionMode`、`negativePrompt`、`uploadedImage`、`generationProvider`。

`styleStrength` 由界面百分数转为0～1，映射为文本风格强调。`uploadedImage` 使用图片数据输入。最终调用参数由 provider 管理。最近记录保存在浏览器 LocalStorage，图像文件保存在后端本机。

## 输出

正式验收记录：原图1024×1024 PNG，文化卡1080×1440 PNG，明信片／海报／帆布袋效果图1600×1200 PNG。文化卡保留标题、文化来源、视觉特征、象征含义和应用场景，视觉分析另含主体、主色与构图观察。
