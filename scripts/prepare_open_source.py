from pathlib import Path
import json, shutil, re, urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / '.cache/publication'
WORK.mkdir(parents=True, exist_ok=True)
for name in ['README.md', '.gitignore']:
    shutil.copy2(ROOT/name, WORK/(name+'.before'))

def write(rel, text):
    p=ROOT/rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.strip()+'\n', encoding='utf-8')

write('LICENSE', '''MIT License

Copyright (c) 2026 PengYi Wen and Wenmai Huazhang contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.''')

write('README.md', r'''# 纹脉华章

### 传统文化视觉智能创作与文创应用平台

[![License: MIT](https://img.shields.io/badge/License-MIT-b8422e.svg)](LICENSE)
![React](https://img.shields.io/badge/React-19-175b60)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-175b60)
![Qwen Image](https://img.shields.io/badge/Qwen_Image-3.0-c29445)

让传统文化从“被观看”走向“被共创”。输入创作主题，选择文化视觉风格，生成作品，阅读与成图对应的文化说明，再将作品用于文创载体预览和下载。

![真实智能生成工作台](docs/images/workspace.png)

## 功能

| 环节 | 已实现功能 |
|---|---|
| 风格选择 | 朱仙镇木版年画、汴绣纹样、宋画青绿山水、青花瓷纹样、中国剪纸 |
| 创作控制 | 主题、参考图、负向提示、风格影响强度、构图模式、输出用途 |
| 图像生成 | DashScope `qwen-image-3.0`，支持文字与可选参考图联合输入 |
| 作品理解 | Ollama 本地 `qwen3-vl:4b-instruct-q4_K_M` 读取真实成图 |
| CultureCard | 作品标题、文化来源、视觉特征、象征含义、应用场景及 PNG 导出 |
| 文创应用 | 预设载体效果预览；明信片、海报、帆布袋效果图下载 |
| 作品保存 | 原图下载、浏览器近期记录及创作参数恢复 |

风格影响强度通过 Prompt 对视觉特征的强调程度实现。文创输出是效果预览文件。基础图像与视觉模型均由第三方提供，项目实现文化资料组织、交互、服务集成及应用工作流。

## 技术结构

```mermaid
flowchart LR
  A[React 创作输入] --> B[FastAPI / Prompt Builder]
  B --> C[DashScope Qwen Image 3.0]
  C --> D[真实作品图]
  D --> E[Ollama Qwen3-VL]
  E --> F[CultureCard]
  D --> G[文创预览]
  F --> H[PNG 下载]
  G --> H
```

前端：React 19、Vite 6、TypeScript、Tailwind CSS 4、React Router 7、Motion。后端：FastAPI、Pydantic、Pillow、DashScope。

## 快速开始

需要 Python 3.10+、Node.js 20.19+（或 22.12+）、npm 和 Ollama。完整的图像生成需要用户自己的阿里云百炼 API Key；模型服务的调用按服务商规则计费。

```bash
git clone https://github.com/3331083641-prog/wenmai-huazhang.git
cd wenmai-huazhang
```

### 1. 本地视觉模型

安装并启动 [Ollama](https://ollama.com)，下载视觉模型：

```bash
ollama pull qwen3-vl:4b-instruct-q4_K_M
```

Ollama 默认监听 `http://127.0.0.1:11434`。运行需要足够的内存／显存，具体取决于模型和设备。

### 2. 后端

Windows PowerShell：

```powershell
python -m venv backend/venv
./backend/venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
# 编辑 backend/.env，填入 DASHSCOPE_API_KEY 和业务空间专属 DASHSCOPE_BASE_URL
./scripts/start_backend.ps1
```

macOS / Linux：

```bash
python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 DASHSCOPE_API_KEY 和业务空间专属 DASHSCOPE_BASE_URL
cd backend
./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/health`，确认图像 provider 与本地视觉模型状态。接口文档：`http://127.0.0.1:8000/docs`。

### 3. 前端

另开终端，在项目目录运行：

```bash
cd frontend
npm ci
npm run dev
```

打开 `http://localhost:5173`。前端 API 地址默认是 `http://127.0.0.1:8000`，可通过 `frontend/.env.local` 中的 `VITE_API_BASE_URL` 修改。

## 使用流程

1. 进入智能生成页，填写主体、位置关系和创作主题。
2. 选择五类文化视觉风格之一，按需上传 JPG／PNG 参考图。
3. 设置负向提示、风格影响强度、构图模式与输出用途。
4. 点击生成，等待真实服务返回作品及图像理解结果。
5. 检查主图和 CultureCard，进入文创转化页查看载体效果。
6. 下载原图、文化卡或文创效果图。

图像理解服务不可用时，系统保留已生成图，卡片标明模板回退来源。正式默认配置禁止用模拟图替代失败的生成请求。

## 目录

```text
backend/       FastAPI、Prompt Builder、provider、图像理解
frontend/      React 应用、风格库、CultureCard、文创预览
assets/        风格参考与素材说明
docs/          架构、使用文档、真实界面及示例
scripts/       可移植的启动脚本
licenses/      保留的第三方许可证
```

已保存的正式案例覆盖五类风格生成、真实成图理解、CultureCard 和三类文创下载，详情见 [案例说明](docs/examples/README.md)。开源目录不包含本机密钥、依赖目录、模型权重、运行缓存或历史备份。

## 文档与参赛材料

- [架构与接口](docs/architecture.md)
- [部署与常见问题](docs/running.md)
- [第三方许可与素材](THIRD_PARTY_NOTICES.md)
- [参赛发行版](https://github.com/3331083641-prog/wenmai-huazhang/releases)

本项目参加 2026 iCAN 大学生创新创业大赛 AI 应用创新挑战赛软件赛道。仓库链接用于获取源码，并非已部署的在线应用地址。

## 许可证

项目原创代码采用 [MIT](LICENSE)。已有文件中的 Apache-2.0 声明保留，适用文件和许可证副本见 [第三方说明](THIRD_PARTY_NOTICES.md)。图片、模型及外部服务不自动随代码许可证授予权利，具体素材说明见 `assets/README.md`。
''')

write('docs/architecture.md', '''# 架构与接口

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
''')
write('docs/running.md', '''# 部署与常见问题

## 配置

以 `backend/.env.example` 为模板，在本机建立 `.env`。填写自己的 `DASHSCOPE_API_KEY`，保留默认生成 provider 和模型。本地 Ollama 启动后，使用与安装一致的 `QWEN_VL_MODEL`。密钥只进入后端配置。

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
''')
write('THIRD_PARTY_NOTICES.md', '''# 第三方组件与素材说明

项目新增和原创代码采用 MIT。`frontend/src/App.tsx` 含有既有 Apache-2.0 声明，该声明原样保留；Apache-2.0全文在 `licenses/Apache-2.0.txt`。前端依赖许可保留在锁文件及其上游包中，Python依赖遵循各自许可。

Qwen Image通过阿里云百炼调用，Ollama视觉模型按其上游模型许可使用；MIT不覆盖模型权重或云端服务条款。可选 InstantStyle provider 代码保留在后端，第三方 InstantStyle 项目和模型权重不捆绑发布。

素材说明见 `assets/README.md`。仓库中的已生成案例用于说明实际输出，不表示对第三方文化素材另行授权。保留的图片和文化内容应按具体来源及使用场景核对。

二维码由免费开源项目 https://github.com/lincolnloop/python-qrcode 生成，使用BSD许可，二维码中的网址可直接读取，无商业二维码平台或动态跳转服务。

演示视频配音使用 https://github.com/rany2/edge-tts 调用语音服务；该工具不作为本应用运行依赖，第三方许可及服务规则仍适用。
''')
for url, name in [('https://raw.githubusercontent.com/spdx/license-list-data/main/text/Apache-2.0.txt','Apache-2.0.txt'),('https://raw.githubusercontent.com/lincolnloop/python-qrcode/main/LICENSE','python-qrcode.txt')]:
    data=urllib.request.urlopen(url, timeout=30).read()
    dest=ROOT/'licenses'/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data)

write('scripts/start_backend.ps1', r'''$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot 'backend/venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw '先按 README 创建 backend/venv 并安装依赖。' }
Set-Location (Join-Path $projectRoot 'backend')
& $python -m uvicorn app:app --host 127.0.0.1 --port 8000
''')
write('scripts/start_frontend.ps1', r'''$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $projectRoot 'frontend')
& npm.cmd run dev
''')

ignore=(ROOT/'.gitignore').read_text(encoding='utf-8')
ignore+='''
# Local evidence, reports, credentials and optional third-party checkout
iCAN_应用方案/
external/
backend/uploads/
backend/logs/
AGENTS.md
*.before
*.pem
*.key
**/.env.*
!**/.env.example
wenmai-huazhang-home-2026-09-28.png
'''
write('.gitignore',ignore)
# Publish only portable configuration examples; never copy backend/.env.
write('backend/.env.example', '''GENERATION_PROVIDER=dashscope_qwen_image
ALLOW_MOCK_FALLBACK=false
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=
DASHSCOPE_IMAGE_MODEL=qwen-image-3.0
QWEN_VL_ENABLED=true
QWEN_VL_BASE_URL=http://127.0.0.1:11434
QWEN_VL_MODEL=qwen3-vl:4b-instruct-q4_K_M
QWEN_VL_TIMEOUT=180
QWEN_VL_CONTEXT_TOKENS=8192
QWEN_VL_TEMPERATURE=0.65
''')
write('frontend/.env.example','VITE_API_BASE_URL=http://127.0.0.1:8000')
cases=ROOT/'iCAN_应用方案/05_生成案例/正式验收_20260929'
labels={'01':'zhuxianzhen','02':'bianxiu','03':'songhua','04':'qinghua','05':'jianzhi'}
for folder in cases.iterdir():
    if folder.name[:2] not in labels: continue
    name=labels[folder.name[:2]]
    out=ROOT/'docs/examples'/name;out.mkdir(parents=True,exist_ok=True)
    for f in ['generated.png','culture_card.png']:
        if (folder/f).is_file():shutil.copy2(folder/f,out/f)
write('docs/examples/README.md', '''# 正式生成案例

五类案例来自2026年9月29日的真实 DashScope Qwen Image 3.0生成，随后由本地Qwen3-VL读取实际图片。每个目录包含作品图与已导出的文化说明卡。文化卡PNG导出尺寸1080×1440，作品尺寸1024×1024。

| 目录 | 风格 | 实际主体 |
|---|---|---|
| zhuxianzhen | 朱仙镇木版年画 | 门楼、瑞兽、牡丹与祥云 |
| bianxiu | 汴绣纹样 | 白兔、牡丹与枝叶 |
| songhua | 宋画青绿山水 | 古亭、松树、溪水与帆船 |
| qinghua | 青花瓷纹样 | 双鱼、莲花、缠枝及水波 |
| jianzhi | 中国剪纸 | 城楼、牡丹与飞燕 |

图片为模型生成案例；文化解释用于辅助理解。该目录不包含 API Key、内部日志或个人环境配置。
''')
print('Prepared README, MIT license, retained notices, portable startup scripts and real examples.')
