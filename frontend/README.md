# 纹脉华章前端

前端为面向 2026 年 iCAN 大学生创新创业大赛 AI 应用创新挑战赛软件赛道的交互式创作界面。

## 页面

- 首页：项目定位、当前能力、创作工作流和应用效果示意。
- 风格库：五类传统视觉风格及色彩、构图、纹样参考。
- 智能生成：连接 FastAPI，支持主题与参考图共同输入、风格参数控制、结果展示和文化说明卡下载。
- 文创转化：将最近生成作品放入预设载体模板，展示应用效果。
- 应用场景：数字展陈、文旅文创与线上传播的静态方案示意。
- 关于项目：当前技术链路、已实现能力、后续规划及素材说明。

## 技术与生成服务

React 19、Vite 6、TypeScript、Tailwind CSS 4、React Router 7 和 Motion。图像请求通过 FastAPI 发送，由后端接入阿里云百炼 Qwen Image 3.0。支持 `text_to_image` 与 `image_to_image`；参考图会随生成请求提交。

前端只向本项目后端发送请求，不读取或保存 DashScope API Key。API 地址优先读取 `VITE_API_BASE_URL`，默认值为 `http://127.0.0.1:8000`。

文化说明卡由生成主题与本地风格条目整理，不依赖独立文本模型。最近生成记录保存在当前浏览器 LocalStorage。文创载体和应用场景是效果预览与示意，不连接订单或生产服务。

## 启动与检查

在 `frontend` 目录运行：

```powershell
npm install
npm run dev
```

默认打开 `http://localhost:5173`。类型检查运行 `npm run lint`，构建运行 `npm run build`。