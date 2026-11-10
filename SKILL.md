---
name: google-flow-director
description: Google Flow (Veo) 商业广告与宣传片导演工作台 Skill。专注于「城市文旅宣传片」、「品牌情绪 TVC」与「产品高光展示」三大方向。当用户输入视频主题、总时长或上传产品参考图时，自动构建全局视觉与声音圣经（Visual & Audio Bible）、智能切分 15s 多段分镜时间轴、规划无缝转场桥接（Match Cut / 甩镜遮罩 / 光斑呼吸 / 首尾帧接力），生成直接内嵌【纯净电影画面 + 原生中文配音 + 动作音效 + BGM】的一体化 Google Flow 提示词（严禁生成字幕以防字符错乱，字幕留待后期剪辑添加），并自动导出本地 Markdown 执行单、交互式 HTML 故事板且同步至 Google Drive。
---

# Google Flow Director (`google-flow-director`)

专为 **Google Flow (Veo 原生音画一体生成)** 打造的商业视频导演级分镜与多段一致性控制系统。融合了 `HiAPIAI/awesome-ai-video-workflows`（商业主视觉运镜与光影标准）、`BigBanana-AI-Director` / `ArcReel`（全局视觉与声音圣经 + 关键帧资产锁）以及 `creatify-ai/video-ad-generator`（黄金时间轴与高完播节奏）的方法论。

## 适用场景

1. **城市文旅宣传片 (City & Cultural Tourism)**：古今穿越、非遗匠心、自然山河、赛博都市、人文烟火。
2. **品牌情绪 TVC (Brand Anthem & Commercial)**：高奢极简、生活美学、品牌精神升华、质感空镜叙事。
3. **产品高光展示 (Product Hero Showcase)**：数码硬件微距、美妆香氛流体、饮品高速摄影、工业设计光影流转（支持上传实拍产品图提取视觉 DNA）。

---

## 核心执行流程（4 步纯净音画导演工作流）

每次用户提出视频创作需求（例如给出**主题 + 目标总时长 + 可选产品图/风格偏好**）时，必须严格按以下 4 个阶段执行：

### Step 1：产品图视觉 DNA 解构（如有上传图片）与全局音画双锁（Visual & Audio Bible）

1. **若用户上传了产品图 / 品牌 Logo / 参考图**：
   - 立即使用 `view_file` 查看图片，提取 **Product Visual DNA**：
     - 精确几何造型与比例（Shape & Proportions）
     - 表面材质与反光属性（如 `brushed titanium, matte frosted glass, gold foil embossed serif logo`）
     - 核心色彩代码与光影特征
   - 将提取出的英文固定外观词定义为 `subject_lock_en`，并规划 **Google Flow Ingredients（垫图/首帧参考）策略**。
2. **构建全局视觉与声音圣经 (`visual_bible` + `audio_guide`)**：
   - 查阅 `references/cinematography_and_transitions.md`，确定全片唯一的：
     - **摄影机与镜头焦段**（如 `ARRI Alexa 65 + Panavision Anamorphic Lens`）
     - **光影基调与色温色彩**（如 `Warm amber kiln firelight contrasting with deep jade-cyan shadows, Kodak Vision3 500T`）
     - **全局强制视觉后缀 (`style_suffix_en`)**：一段 25~40 词的标准英文摄影后缀。
     - **全局强制配音与声音锁 (`voice_and_audio_lock_en`)**：Google Flow 支持直接带配音与音效，为了防止跨视频片段旁白换人或配乐突变，必须定义固定的**旁白人设音色词**（如 `Consistent warm, deep, magnetic male Mandarin Chinese documentary narrator voice, calm poetic cadence, crisp studio condenser mic`）以及统一的背景配乐基调。
   - **强制合成规则**：`style_suffix_en` 与 `voice_and_audio_lock_en` **必须直接合并且内嵌到每一个镜头的 `flow_video_prompt_en` 中**，确保用户在 Google Flow 中一次复制即可同时生成画风连贯、配音音色统一的纯净成片。
   - **⚠️ 绝不添加字幕指令**：提示词中严禁出现生成字幕或画面大字的指令（AI 视频直出文字极易变形扭曲破坏质感）。分镜表内单独保留中文旁白台词，供用户在剪映/PR等后期剪辑软件中一键语音识别生成高质量字幕。

### Step 2：总时长切分与生成模式决策（支持 15s 一镜到底或快切分镜）

根据用户指定的成片总时长（如 30s 拆分为 2 个 15s 长镜头，或拆分为多个 5s~8s 镜头）：
- **15s 复合一镜到底模式（推荐用于 Google Flow 15s 直出）**：
  - 将 30s 拆为 `CLIP 01 (00:00 - 00:15)` 与 `CLIP 02 (00:15 - 00:30)`。
  - 在每个 15s Prompt 内部按 `[0-5s] -> [5-10s] -> [10-15s]` 规划连续不间断的运镜演进（Continuous Camera Journey）以及精确到秒段的音效与旁白卡点。
  - 同时在备用栏 (`keyframe_image_prompt_en`) 提供 **`8s Base + 7s SceneBuilder Extend`（含分段配音与音效）** 的拆分提示词，方便用户在 Flow 中灵活选择。
- **智能分配生成模式 (`gen_mode_badge`)**：
  - **`T2V 纯文生（音画一体）`（默认占 70%~85%）**：用于风光、流体、水墨、光影空镜，直接靠内嵌的全局视觉锁 + 全局声音锁保持一致。
  - **`I2V 首帧垫图 / Ingredients`（占 15%~25%）**：当画面出现**具体产品本体、品牌 Logo 或核心国宝器物**时启用，指导用户上传参考图作为 Ingredients。
  - **`F2V 首尾帧桥接`（关键变形转场）**：当相邻两镜需要超现实无缝变形时启用。

### Step 3：前后镜头无缝转场桥接 + 音画一体化 Prompt 编写（无字幕纯净画面）

1. **视觉无缝转场（Transition Bridge）**：
   - 从 `references/cinematography_and_transitions.md` 的 6 大转场矩阵（`MATCH_SHAPE` 同心圆匹配、`WHIP_WIPE` 甩镜遮罩、`SPEED_RAMP_DIVE` 微距穿入、`LIGHT_BOKEH` 光斑呼吸、`MOTION_RELAY` 动势接力、`SCENE_EXTEND` 原生延展）中选择转场。
   - 上一段结尾包含 `Exit Momentum`，下一段开头包含对应的 `Entry Momentum`。
2. **音画一体化 Prompt 结构（All-in-One Clean Flow Prompt）**：
   - 每个分镜的 `flow_video_prompt_en` 必须将以下模块融合成一段可直接复制进 Google Flow 的完整提示词（不含任何字幕文字指令）：
     1. **`[Visual & Continuous Camera]`**：分秒段画面与连续运镜描述；
     2. **`[Native Audio, Foley & BGM]`**：与画面动作严格同步的原生环境音效（ASMR/Foley）与背景配乐推进；
     3. **`[Voiceover (Mandarin Chinese)]`**：直接包含旁白音色描述与双引号内的**中文配音台词原文**（例如：`A warm, deep, magnetic male narrator speaks in standard Mandarin Chinese with poetic documentary cadence: "一捧高岭土，落笔藏山河；千度烈焰里，淬炼不灭的温润。"`）；
     4. **`[Global Visual Lock]`**：全局摄影机与胶片光影风格后缀锁。

### Step 4：双模交付（Markdown 执行单 + 交互式 HTML 导演故事板）与云端同步

1. 将完整策划与分镜数据组织为结构化 JSON，保存至 `/home/antigravity/flow_projects/<project_slug>.json`。
2. 调用本 Skill 自带的导出脚本生成本地文件与可视化 HTML：
   ```bash
   python3 /shared/user/.gemini/skills/google-flow-director/scripts/export_storyboard.py \
     /home/antigravity/flow_projects/<project_slug>.json \
     --out-dir /home/antigravity/flow_projects \
     --html-artifact <ArtifactDirectoryPath>/<project_slug>_storyboard.html
   ```
3. 调用云盘同步脚本，自动将生成的 `.md` 分镜执行单、`.html` 交互故事板与 `.json` 源数据归档至用户的 Google Drive（`Google_Flow_Director_Hub/01_项目分镜与故事板_Projects/<project_slug>/`）：
   ```bash
   python3 /shared/user/.gemini/skills/google-flow-director/scripts/sync_to_drive.py \
     --project-dir /home/antigravity/flow_projects
   ```
4. 同时将 `<project_slug>_storyboard.html` 通过 `write_to_file`（带 `ArtifactMetadata`: `UserFacing: true`, `RequestFeedback: false`）注册为可预览 Artifact，并在回复中总结核心分镜亮点与文件/云盘链接。
