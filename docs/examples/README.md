# 当前五组真实案例

这是保存的真实模型输出，不是正在运行的在线推理。

| 风格 / 作品 | 参考输入 | 真实 Qwen Image 3.0 作品 | 实际导出 CultureCard |
|---|---|---|---|
| 朱仙镇木版年画<br>瑞猫迎春 | [原尺寸](zhuxianzhen/reference.png)<br><img src="zhuxianzhen/reference.png" width="160" alt="朱仙镇木版年画参考图"> | [原尺寸](zhuxianzhen/generated.png)<br><img src="zhuxianzhen/generated.png" width="160" alt="朱仙镇木版年画生成作品"> | [原尺寸](zhuxianzhen/culture_card.png)<br><img src="zhuxianzhen/culture_card.png" width="160" alt="朱仙镇木版年画文化说明卡"> |
| 汴绣纹样<br>绣兔牡丹 | [原尺寸](bianxiu/reference.png)<br><img src="bianxiu/reference.png" width="160" alt="汴绣纹样参考图"> | [原尺寸](bianxiu/generated.png)<br><img src="bianxiu/generated.png" width="160" alt="汴绣纹样生成作品"> | [原尺寸](bianxiu/culture_card.png)<br><img src="bianxiu/culture_card.png" width="160" alt="汴绣纹样文化说明卡"> |
| 宋画青绿山水<br>云鹤临水楼 | [原尺寸](songhua/reference.png)<br><img src="songhua/reference.png" width="160" alt="宋画青绿山水参考图"> | [原尺寸](songhua/generated.png)<br><img src="songhua/generated.png" width="160" alt="宋画青绿山水生成作品"> | [原尺寸](songhua/culture_card.png)<br><img src="songhua/culture_card.png" width="160" alt="宋画青绿山水文化说明卡"> |
| 青花瓷纹样<br>青花蝶韵 | [原尺寸](qinghua/reference.png)<br><img src="qinghua/reference.png" width="160" alt="青花瓷纹样参考图"> | [原尺寸](qinghua/generated.png)<br><img src="qinghua/generated.png" width="160" alt="青花瓷纹样生成作品"> | [原尺寸](qinghua/culture_card.png)<br><img src="qinghua/culture_card.png" width="160" alt="青花瓷纹样文化说明卡"> |
| 中国剪纸<br>剪影灵狐 | [原尺寸](jianzhi/reference.png)<br><img src="jianzhi/reference.png" width="160" alt="中国剪纸参考图"> | [原尺寸](jianzhi/generated.png)<br><img src="jianzhi/generated.png" width="160" alt="中国剪纸生成作品"> | [原尺寸](jianzhi/culture_card.png)<br><img src="jianzhi/culture_card.png" width="160" alt="中国剪纸文化说明卡"> |

## 当前配对与证据

| 风格 | 输入主体 | 提示强度 | 原始生成日期 | 参考参与 | 看图解读 |
|---|---|---|---|---|---|
| 朱仙镇木版年画 | 一只狸花猫，清晰保留猫的面部、虎斑纹、四肢和上扬长尾 | 100% | 2026-10-08 | 已确认 | 本地 Qwen3-VL |
| 汴绣纹样 | 白兔 | 100% | 2026-10-08 | 已确认 | 本地 Qwen3-VL |
| 宋画青绿山水 | 双层古典楼阁 | 65% | 2026-09-30 | 已确认 | 本地 Qwen3-VL |
| 青花瓷纹样 | 一只展开双翅的蝴蝶，保留对称翅形、触角和身体 | 65% | 2026-10-08 | 已确认 | 本地 Qwen3-VL |
| 中国剪纸 | 一只赤狐，保留尖耳、狐狸面部、四肢和蓬松长尾轮廓 | 65% | 2026-10-08 | 已确认 | 本地 Qwen3-VL |

年画猫、青花蝴蝶和剪纸狐使用用户原始白底参考图。汴绣白兔依据用户2026-10-08最终要求，使用新 AI 写实兔子输入真实重新生成；不是把新参考图配到旧结果上。宋画楼阁按用户要求复用2026-09-30视频制作时真实生成的作品及其原始建筑输入，未计费重新生成。

各目录 `metadata.json` 记录 SHA-256、参数、模型和对应成图的真实视觉分析。楼阁保留的响应证据有 `referenceImageUsed=true`，没有留存 usage 数量，因此 `modelInputImageCount=null`，不补造数值。本轮另外对现选作品重新执行了本地看图解读；文化卡通过当前应用实际导出按钮下载，图片为1024×1024，卡片为1080×1440。

## 人工图像审核

| 作品 | 主体和风格 | 发现的问题 / 范围 |
|---|---|---|
| 瑞猫迎春 | 狸花猫、上扬尾巴、红黄黑套色与装饰边框明确 | 有可读题字“瑞猫迎春”，说明负向文字限制未完全生效；保留真实输出 |
| 绣兔牡丹 | 单只白兔、粉红耳部、针线方向与绢地、牡丹装饰 | 审美强弱具有主观性；未发现额外动物或明显乱码 |
| 云鹤临水楼 | 双层楼阁、青绿山体、松树、仙鹤 | 此案例主题明确要求仙鹤，属于旧案例原始输出；建筑参考为AI图，不认定历史实物 |
| 青花蝶韵 | 双翅对称蝶形与青白钴蓝纹样 | 属于装饰风格转化，不是实际瓷器制造 |
| 剪影灵狐 | 狐狸轮廓、蓬松尾巴、红白镂空正负形 | 属于视觉方案，不承诺裁切工艺可制造性 |

没有将被用户替换的金鱼与鹿作为当前正式展示；原始真实请求与输出仍保存在本机任务备份中。没有清除Git历史。文化解读不用于认定具体历史出处。[当前来源与权限](reference_sources.md)。
