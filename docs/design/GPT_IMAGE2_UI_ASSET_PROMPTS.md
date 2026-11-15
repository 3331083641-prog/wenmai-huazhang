# 纹脉华章 VNext｜GPT Image 2 视觉素材需求与专业生图提示词库

> **文档定位**：本文档为「纹脉华章」全站东方数字艺术深度优化专门定制的 **GPT Image 2 高品质素材生成规范与提示词资产清单**。  
> **最新实装状态（v2.4.0）**：全站 5 组核心素材已完成用户提供生成图的 Alpha 通道精修处理与 WebP 性能优化，均已全量实装于对应的 UI 场景，并配置了真实交互（灵笔创作入口、展馆沉浸导览、天青贯耳尊概念展陈、典藏印匣机制弹窗与飞天水墨花精灵等待态）。全部素材均已建立 WebP 高效加载链路与无障碍访问语义。

---

## 一、全局视觉风格指南与通用生图约束 (Global Art Direction)

为确保所有 GPT Image 2 生成的视觉资产在整站中保持高度的和谐统一，所有素材均须遵守以下五大美学先验：

1. **统一调色盘 (Signature Palette)**：
   - 宣纸原色（#FAF7F2 / #F8EEDC）、松烟沉墨（#3F2B1F / #1F1B1A）、朱砂红（#9E241B）、金箔鎏金（#D2A14A / #E3B35C）、温润羊脂白玉与汝窑天青微调。
2. **材质表现 (Materiality)**：
   - 融合传统天然工巧与当代微光触感：羊脂白玉透光漫射、沉香老木温润手感、细腻生宣纹理、手工锤纹鎏金饰边与宋瓷开片微瑕。严禁廉价塑料感、过度反光镀铬或西式赛博朋克霓虹。
3. **光照与视角 (Lighting & Perspective)**：
   - 统一采用 **45度柔和侧上方影棚顶光**，伴随柔和的环境漫反射与自然接触软阴影；
   - 构图统一采用微俯视等轴透视（Isometric 30°-45°）或正侧特写，保留边缘呼吸空间。
4. **输出规格标准 (Output Specifications)**：
   - **格式**：16-bit 带有 Alpha 透明通道的无损 PNG（Pure Transparent Background，严禁白底假透明）；
   - **边距**：主体居中，四周保留 8%~12% 的安全出血边距，方便 CSS / Motion 做视差与悬停缩放；
   - **分辨率**：推荐 1024×1024px 或 2048×2048px 超高清。

---

## 二、精选核心视觉素材需求清单

---

### 素材编号：UI-IMG-01
- **素材名称**：东方数字艺术三维灵笔（文脉神韵画笔）
- **使用页面**：`AICreator.tsx`（智能生成工坊顶部题头与创作工作台核心焦点）及 `Home.tsx` Hero 辅助视差
- **优先级**：**P0（最高优先级，直接奠定创作工坊的东方艺术意象）**
- **设计目的**：替代目前通用的 Lucide 线性 `Sparkles` / `PenTool` 图标，赋予 AI 创作工具深厚的传统“文房之首”文化底蕴与当代数字交互质感。
- **当前 UI 问题**：目前创想工作台上方主要依赖文字说明与普通平面按钮，缺少一个具有视觉统治力的神圣艺术图腾。
- **推荐文件名**：`ui-img-01-cultural-brush.png`
- **预期存放位置**：`frontend/public/visuals/vnext/`
- **输出规格**：
  - 尺寸：1024×1024 px
  - 格式：PNG，Alpha 透明通道背景（Strictly Transparent Background）
  - 构图：对角线 45 度微悬浮，笔尖朝向左下方，伴随微弱水墨与金粉微尘粒子

#### GPT Image 2 完整生图提示词（可直接复制）：
```text
A cinematic, luxury 3D icon of a legendary Chinese calligraphy brush blending ancient craftsmanship with ethereal digital artistry, floating diagonally at a 45-degree angle against a transparent background. 
The brush shaft is carved from translucent mutton-fat white jade (羊脂白玉) interwoven with intricate Song Dynasty filigree gold veins and cinnabar red lacquer accents. The brush ferrule is crafted from hammered ancient brass with delicate cloud filigree patterns (祥云纹). The brush bristles are made of ultra-soft, pure white badger hair tipped with glowing iridescent cinnabar ink and liquid liquid-gold particles that float subtly off the tip.
Soft studio lighting from top-left, gentle rim light accentuating the translucent depth of the jade, warm reflections, realistic contact shadows. 
Exquisite craftsmanship, contemporary museum exhibition piece, ultra-detailed textures, 8k resolution, photorealistic 3D render, Octane render quality, isolated on a completely transparent background (PNG alpha channel), no background elements, no borders, no text.
```

- **交互实现蓝图**：
  - CSS / Motion：静态呈现时保留细腻的呼吸浮动（`y: [-4, 4], duration: 4s`）；鼠标悬停时笔尖金光微闪并伴随轻微 6 度仰角；点击“开始创作”时轻巧下压划出一道金色轨迹。

---

### 素材编号：UI-IMG-02
- **素材名称**：三维虚实交融玉璧楼阁展馆印徽
- **使用页面**：`Home.tsx`（虚拟展馆聚光灯区块）与 `HeritageGallery.tsx`（进入三维展馆的 HUD 导引印鉴）
- **优先级**：**P0（强化三维虚拟展馆的入口仪式感）**
- **设计目的**：将中国古建筑“重檐歇山顶”与“镂雕玉璧”构图有机融合，作为通往 3D 虚拟展馆的象征性“秘钥徽记”。
- **当前 UI 问题**：现有三维展馆卡片主要使用扁平相机与立方体图标，无法直观体现“五馆水院、画境漫游”的东方建筑园林意境。
- **推荐文件名**：`ui-img-02-heritage-pavilion.png`
- **预期存放位置**：`frontend/public/visuals/vnext/`
- **输出规格**：
  - 尺寸：1024×1024 px
  - 格式：PNG，Alpha 透明背景
  - 构图：正侧微俯角 30 度，主体饱满居中

#### GPT Image 2 完整生图提示词（可直接复制）：
```text
A premium 3D isometric emblem representing a traditional Chinese floating pavilion and an ancient ritual jade bi (玉璧), isolated on a pure transparent background. 
The architecture features a miniature classical Song-style double-eave pavilion (重檐四角攒尖亭) made of deep cinnabar red lacquered wood columns, aged dark cedar brackets (斗栱), and weathered celadon ceramic roof tiles with a delicate glaze sheen. Floating directly behind the pavilion is a magnificent, semi-translucent circular imperial jade ring disc (玉璧) carved with refined archaic cloud scroll reliefs (涡云纹), with soft sunlight transmitting through the jade. 
At the base, subtle ripples of crystalline garden water and miniature mossy stone slabs support the structure.
Cinematic soft gallery spotlight, warm ambient occlusion, museum display artifact aesthetic, elegant minimalism, Blender Cycles render style, ultra-fine details, no text, no watermark, isolated on transparent background (PNG alpha).
```

- **交互实现蓝图**：
  - 悬停时通过 Motion 实现玉璧与亭台的轻量微视差（玉璧慢速旋转 3 度，亭台微升 3px）；点击时带有水波轻漾涟漪动效。

---

### 素材编号：UI-IMG-03
- **素材名称**：五大流派东方意象青瓷天球瓶（文创转化灵感器物）
- **使用页面**：`ProductStudio.tsx`（文创工坊源画载体区）与 `StyleLibrary.tsx`（风格库顶栏题图）
- **优先级**：**P1（高价值增强，强化非遗文创的高级实物感）**
- **设计目的**：作为文创转化的灵感母体，展示传统纹样如何立体包裹于现代高定器物之上。
- **当前 UI 问题**：文创工坊左侧仅展示平面原画卡片，缺少一件具有实体质感的“高定文创灵感器物”作为视觉支点。
- **推荐文件名**：`ui-img-03-celadon-vessel.png`
- **预期存放位置**：`frontend/public/visuals/vnext/`
- **输出规格**：
  - 尺寸：1024×1024 px
  - 格式：PNG，Alpha 透明背景
  - 构图：正视特写，微俯 15 度

#### GPT Image 2 完整生图提示词（可直接复制）：
```text
A pristine 3D luxury art piece featuring an elegant Song Dynasty Ru-ware celadon ceramic vase (天青色汝窑贯耳瓶), isolated on a pure transparent background. 
The vase has a silky, matte eggshell-blue glaze with subtle crackle patterns (开片纹) inlaid with ultra-fine liquid gold leaf threads (金丝铁线工艺). Gracefully wrapping around the vase waist is an embossed traditional dragon-and-cloud embroidery ribbon in vermilion red and indigo silk thread, floating slightly off the porcelain surface. 
Lighting is soft diffused daylight coming from a studio window, creating gentle gradients across the curved ceramic body. 
Refined Oriental aesthetic, tactile craftsmanship, ultra-realistic material shaders, 8k resolution, Octane render, product photography for an haute-couture exhibition, clean alpha transparency, no floor, no shadow cast outside canvas.
```

- **交互实现蓝图**：
  - 在文创转化工作台左侧与源画并列展示；当用户在右侧切换“帆布袋 / 青花瓷杯垫 / 丝巾”等不同载体时，器物表面的金丝流光产生呼吸响应。

---

### 素材编号：UI-IMG-04
- **素材名称**：古籍卷轴式立体书香金石印匣（视觉理解与典藏证书）
- **使用页面**：`Gallery.tsx`（作品展厅藏品认证证书）与 `About.tsx`（数字非遗技术矩阵）
- **优先级**：**P1（高价值，替代纯文本技术描述）**
- **设计目的**：将“本地数据库保存”、“SHA-256防伪追溯”与“CultureCard 自动生成”等抽象技术概念，具象化为一座典雅庄严的东方金石印匣。
- **当前 UI 问题**：作品展厅的“已落盘存储”与“自动防伪”主要靠几行小字标签说明，视觉震撼力不足。
- **推荐文件名**：`ui-img-04-archive-casket.png`
- **预期存放位置**：`frontend/public/visuals/vnext/`
- **输出规格**：
  - 尺寸：1024×1024 px
  - 格式：PNG，Alpha 透明通道

#### GPT Image 2 完整生图提示词（可直接复制）：
```text
An intricate 3D rendered antique Chinese scholar's treasure box (文房百宝嵌印匣), half-open, isolated on a transparent background. 
The casket is crafted from dark polished zitan rosewood (紫檀木) with brass corner reinforcements and an antique bronze clasp. Resting gracefully inside and emerging slightly from the box is a rolled raw-silk handscroll (丝绢手卷) tied with a cinnabar silk cord, accompanied by a square carved imperial soapstone seal (寿山石印章) carved with a mythical Qilin beast on top. Faint golden light and subtle calligraphy dust float out from the opened lid.
Soft museum display spotlight, rich timber grain textures, authentic micro-scratches on brass, tactile silk fabric weave, 8k resolution, Unreal Engine 5 render style, perfectly isolated on transparent PNG, zero background clutter.
```

- **交互实现蓝图**：
  - 点击作品详情时，印匣伴随 150ms 优雅轻微抬升，印匣旁顺滑滑出 SHA-256 溯源存证卡。

---

### 素材编号：UI-IMG-05
- **素材名称**：水墨晕染与金箔四瓣流云花纹精灵（智能等待与动态揭示专属素材）
- **使用页面**：`AICreator.tsx`（智能生成等待动画中心装饰）与页面路由平滑切换
- **优先级**：**P2（可选增强，已有纯代码版墨韵兜底，此素材用于后期顶级视觉升华）**
- **设计目的**：作为生成等待状态中，缓慢旋转、扩散绽放的动态分层纹样。
- **推荐文件名**：`ui-img-05-ink-bloom-sprite.png`
- **预期存放位置**：`frontend/public/visuals/vnext/`
- **输出规格**：
  - 尺寸：1024×1024 px
  - 格式：PNG，透明通道

#### GPT Image 2 完整生图提示词（可直接复制）：
```text
An ethereal abstract Oriental motif depicting an ink wash blooming flower intertwined with swirling golden silk ribbons and Dunhuang flying apsaras cloud scrolls, centered on a pure transparent background. 
The ink ranges from dense pitch black in the core to delicate diluted grey gradients at the edges, resembling real Chinese calligraphy ink diffusing gently on wet rice paper (生宣晕染). Layered seamlessly over the ink are flowing threads of genuine beaten gold leaf (纯金箔) and faint vermilion mineral pigment sprinkles. 
Circular symmetrical mandala-like composition, fluid organic motion captured mid-bloom, high contrast, clean transparent background, no harsh borders, no canvas textures outside the ink blossom, 8k resolution, graphic design masterpiece.
```

- **交互实现蓝图**：
  - 在生成等待时配合 CSS `@keyframes ink-rotate` 顺时针以 12 秒一圈平缓旋转，缩放比例在 0.96 到 1.04 之间如脉搏般缓慢舒张。

---

## 三、GPT Image 2 生成后接入实施准则 (Phase B Implementation Checklist)

1. **落盘核验**：生成的图片由用户放置在 `frontend/public/visuals/vnext/` 目录下，核对文件名是否匹配；
2. **尺寸与画质检查**：通过脚本核验是否真正具备 Alpha 透明通道（避免黑色或白色背景溢出），确认边缘平滑无锯齿；
3. **响应式与性能约束**：
   - 桌面端最大展示尺寸限制在 280px~360px，移动端自适应收缩至 160px~200px；
   - 配合 `loading="lazy"` 与 `decoding="async"`，确保首屏加载速度；
4. **无障碍与降级**：
   - 为每一张素材配置精准的中文语义 `alt` 文本；
   - 在 `prefers-reduced-motion` 启用时，自动禁用所有旋转、浮动与视差动画，转为典雅的静态呈现。
