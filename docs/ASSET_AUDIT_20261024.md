# 文件、素材与历史资料审计（2026-10-24）

本报告记录本次仓库整理开始时的文件元数据快照、素材引用关系及许可边界。运行验收与远程提交状态以本次工程验收报告和 Git 提交为准；文件存在不等于功能已通过运行验证。

## 初始文件快照

递归扫描项目工作树，排除 Git 自身对象库；只读取文件名、类型、大小、修改时间与 Git 状态，不读取凭证内容。扫描结果仅在本机 `logs/audit_inventory_20261024.csv` 和同名 JSON 中保留，不作为发布附件。

| 项目 | 文件数 | 大小 |
|---|---:|---:|
| 工作树全部文件 | 59,240 | 9,460,048,421 字节 |
| 已跟踪文件 | 614 | 150,491,683 字节 |
| 已识别的忽略文件 | 58,624 | 9,309,555,908 字节 |
| 扫描过程中生成的本机日志 | 2 | 830 字节 |

初始 `git status` 仅显示视觉分析服务代码有一处修改，未发现未跟踪的正式业务源码。大量“本地新增文件”已在本地 Git 历史中，是否已上传须与获取后的远程分支比较，不能由 `git status` 单独判断。以上数量不含本次新制作的截图、文档、备份及验收日志。

按本机总占用排序：后端约 5.22 GB、赛事历史资料约 2.65 GB、输出目录约 553 MB、前端约 461 MB、素材约 281 MB、文档约 232 MB。体积主要来自 Python 虚拟环境、Node.js 依赖、视频和过程渲染。最大的已跟踪文件为当前展馆 GLB，约 11.57 MB；未发现超过 50 MB 的已跟踪文件。依赖二进制与大视频均不应随源码同步。

## 正式版本与资源引用

| 内容 | 实际入口及引用关系 | 处理 |
|---|---|---|
| 正式前端 | `frontend/index.html` → `frontend/src/main.tsx` → `App.tsx` 与页面模块 | 保留源码、锁文件及必需静态资源 |
| 已保存作品 | `savedCases.ts`、`galleryArtworks.ts` 和体验配置读取 `docs/examples/` | 五组案例、元数据、原图、成图、文化卡完整保留 |
| 风格展示图 | `styleLibrary.ts`、首页与场景页读取 `frontend/public/`；后端读取 `backend/style_refs/` | 三个分发位置按现有兼容关系保留，不因重复误删 |
| 互动绘卷与漫游 | `frontend/src/features/culture-experience/`、`painting-world/`，读取 `frontend/public/interactive/` 的清单、深度与分层图 | 运行资源均已跟踪，保留 |
| 三维展馆 | `HeritageGallery.tsx` → `HeritageScene.tsx` → `GalleryModel.tsx` → `frontend/public/models/wenmai_gallery_v5.glb` | 以实际页面引用的模型为准 |
| 吉祥物 | `MascotCompanion.tsx` 读取 `frontend/public/models/wenmai_mascot_ww.glb` | 保留模型与 Blender 源文件，完成度以专项验收说明为准 |
| 十四件器物 | `assetCatalog.ts`、`library.gen.ts`、实例与交互模块 | 程序几何和 Canvas 纹理已进入正式源码；原型 HTML 不是运行依赖 |
| Blender 制作链 | `assets/gallery3d/blender/`、布局 JSON、制作脚本及角色源文件 | 保留可编辑源与历史验收证据 |

已有 4 个发布用 GLB、6 个 Blender 源文件、15 个 WebP 均已跟踪。忽略规则中的 `assets/exports/`、`assets/gallery3d/exports/*.glb` 是制作阶段导出副本，版本和字节可能与修复楼梯井后的正式发布模型不同，不能仅凭名称相似替换。没有发现被忽略而缺失于正式前端引用链的新 HTML、React 页面或必需发布模型。

除依赖和构建输出外，HTML 仅有正式前端入口、工具测试查看器，以及被忽略的赛事视频打包入口。工具查看器是开发辅助页；赛事 Remotion 源码与视频属于历史交付材料，不是本轮正式网站入口。

## 五组真实案例核验

对 `zhuxianzhen`、`bianxiu`、`songhua`、`qinghua`、`jianzhi` 五组逐一检查：

- `reference.png`、`generated.png`、`culture_card.png`、`metadata.json` 全部存在。
- 五张参考图的 SHA-256 与各自 `referenceSha256` 完全一致；五张成图的 SHA-256 与各自 `generatedSha256` 完全一致。
- 元数据均记录 `dashscope_qwen_image` / `qwen-image-3.0`，文化分析来源记录为 `qwen3_vl`。本次校验的是现存证据的一致性，并未重新生成五组作品。
- `assets/style_refs/`、`backend/style_refs/`、`frontend/public/` 的五张同名风格图逐一散列相同；它们与案例参考输入是不同职责的资源。

来源和权限说明保留于 [参考素材来源](examples/reference_sources.md)。知识内容来源清单保留于 [文化知识库](../culture_knowledge/README.md) 与 `sources.json`，文献内容出处不构成图片的转载许可。

## 许可边界与历史保留

保留 [MIT](../LICENSE)、[第三方说明](../THIRD_PARTY_NOTICES.md)、`licenses/Apache-2.0.txt` 及二维码组件许可。模型权重和云服务规则不由本仓库 MIT 授权覆盖；可选第三方 InstantStyle 项目与权重不捆绑。

五组参考输入已有项目使用授权和 AI 来源记录，不声明其为实拍、公共领域或 CC0。风格示例图的逐项来源和授权状态在 [素材说明](../assets/README.md) 中仍标为待团队核实，本次继承保留现有运行依赖，不新增来源不明的原始参考图或对其作扩大授权声明。展馆与器物采用项目制作的 Blender / 程序几何链路；原型 HTML 属用户提供素材，未将外部原始文件和私有路径一起发布。

保留赛事 Release、旧验收文档、五组案例及其历史记录。现有 `.bak` 命名脚本和旧场景源属于已跟踪历史资料，本轮未删除；文件名看似临时不能作为直接删除依据。旧截图可以继续作为历史验收证据，新首页展示以本次真实浏览器截图为准。

不纳入新提交：虚拟环境、`node_modules`、缓存、运行日志、上传目录、输出目录、原始参考附件、大视频、私有配置及任务备份。可再生成的依赖、缓存和过程渲染可在需要时清理，本次没有删除任何原始文件。

## 隐私整理与兼容检查

修改前已将五个文件备份至本机忽略目录 `.backup/audit_sync_20261024/`，未将备份发布：

- 生成器物模块、资产说明和两份历史交接文档中，移除含本机用户名的绝对路径，保留来源性质与追溯关系。
- `scripts/assets/extract_library.py` 改为必填来源 HTML 参数，并支持 `--output`，默认输出到当前仓库的器物模块。原脚本没有可移植的 CLI 参数，原型文件也未随仓库分发；现在可明确指定来源，不再绑定某台机器的桌面目录。
- 提取白名单、行区间和 NaN 修复逻辑保持不变；现有器物模块仅修改来源注释，业务几何代码未重新生成。

已执行 Python 语法检查、生成器 `--help`、五个文件的私人路径残留检查和 `git diff --check`，均通过。因原始 HTML 未在仓库内，不在本次运行提取生成过程；当前已提交的生成模块仍可直接供网站使用。前端整体构建与浏览器验收由本次工程检查另行记录。

对已跟踪脚本、工具及资产脚本进行了密钥格式、私钥头、凭证字面赋值和私人路径候选扫描。扫描不读取 `.env`，报告只记录路径、行号和风险类型，不记录候选原文。未发现明确密钥候选；已定位的私人路径已清理。此检查不代替最终待提交内容审查。
