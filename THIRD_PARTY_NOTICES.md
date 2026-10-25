# 第三方组件与素材说明

项目新增和原创代码采用 MIT。`frontend/src/App.tsx` 含有既有 Apache-2.0 声明，该声明原样保留；Apache-2.0全文在 `licenses/Apache-2.0.txt`。前端依赖许可保留在锁文件及其上游包中，Python依赖遵循各自许可。

Qwen Image通过阿里云百炼调用，Ollama视觉模型按其上游模型许可使用；MIT不覆盖模型权重或云端服务条款。可选 InstantStyle provider 代码保留在后端，第三方 InstantStyle 项目和模型权重不捆绑发布。

自动画境使用本地 **Depth Anything V2 Small**（`depth-anything/Depth-Anything-V2-Small-hf`），用于相对深度估计；Small 权重的上游许可为 Apache-2.0，全文见 `licenses/Apache-2.0.txt`。[模型卡](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf)、[原项目](https://github.com/DepthAnything/Depth-Anything-V2)、[固定版本及权重校验](models/interactive-models.json)。未捆绑 Base/Large/Giant。PyTorch、Transformers 和 Safetensors 按各自许可使用。深度估计不代表自研或自训练模型。

2026-10-25 新增的五件运行期验证作品，采用用户要求准备的 AI 白底参考图；参考图由内置 imagegen 工具生成，不是实物照片，相关来源标记保存在各案例元数据中。产品界面截图另由真实浏览器采集，二者不混用。

素材说明见 `assets/README.md`。仓库中的已生成案例用于说明实际输出，不表示对第三方文化素材另行授权。保留的图片和文化内容应按具体来源及使用场景核对。

二维码由免费开源项目 https://github.com/lincolnloop/python-qrcode 生成，使用BSD许可，二维码中的网址可直接读取，无商业二维码平台或动态跳转服务。

演示视频配音使用 https://github.com/rany2/edge-tts 调用语音服务；该工具不作为本应用运行依赖，第三方许可及服务规则仍适用。
