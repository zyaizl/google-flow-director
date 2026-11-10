---
name: google-flow-director
description: Google Flow (Veo) 商业广告与宣传片导演工作台 Skill。专注于「城市文旅宣传片」、「品牌情绪 TVC」与「产品高光展示」三大方向。当用户输入视频主题、总时长或上传产品参考图时，自动构建全局视觉圣经（Visual Bible）、智能切分超出 15s 限制的多段分镜时间轴、规划无缝转场桥接（Match Cut / 甩镜遮罩 / 首尾帧接力），并自动导出本地 Markdown 分镜执行单与可交互 HTML 导演故事板。
---

# Google Flow Director (`google-flow-director`)

专为 **Google Flow (Veo)** 打造的商业视频导演级分镜与多段一致性控制系统。融合了 `HiAPIAI/awesome-ai-video-workflows`（商业主视觉运镜与光影标准）、`BigBanana-AI-Director` / `ArcReel`（全局视觉圣经与关键帧资产锁）以及 `creatify-ai/video-ad-generator`（黄金时间轴与高完播节奏）的方法论。

## 适用场景

1. **城市文旅宣传片 (City & Cultural Tourism)**：古今穿越、非遗匠心、自然山河、赛博都市、人文烟火。
2. **品牌情绪 TVC (Brand Anthem & Commercial)**：高奢极简、生活美学、品牌精神升华、质感空镜叙事。
3. **产品高光展示 (Product Hero Showcase)**：数码硬件微距、美妆香氛流体、饮品高速摄影、工业设计光影流转（支持上传实拍产品图提取视觉 DNA）。

---

## 核心执行流程（4 步导演工作流）

每次用户提出视频创作需求（例如给出**主题 + 目标总时长 + 可选产品图/风格偏好**）时，必须严格按以下 4 个阶段执行：

### Step 1：产品图视觉 DNA 解构（如有上传图片）与全局视觉圣经（Global Visual Bible）

1. **若用户上传了产品图 / 品牌 Logo / 参考图**：
   - 立即使用 `view_file` 查看图片，提取 **Product Visual DNA**：
     - 精确几何造型与比例（Shape & Proportions）
     - 表面材质与反光属性（如 `brushed titanium, matte frosted glass, gold foil embossed serif logo`）
     - 核心色彩代码与光影特征
   - 将提取出的英文固定外观词定义为 `subject_lock_en`，并规划 **Google Flow Ingredients（垫图/首帧参考）策略**。
2. **构建全局视觉圣经 (`visual_bible`)**：
   - 查阅 `references/cinematography_and_transitions.md`，确定全片唯一的：
     - **摄影机与镜头焦段**（如 `ARRI Alexa 65 + Panavision Anamorphic Lens` 或 `Phantom Flex4K 1000fps + Laowa 24mm Probe Macro`）
     - **光影基调与色温色彩**（如 `Golden hour rim lighting with deep cyan shadows, Kodak Vision3 500T`）
     - **全局强制后缀 (`style_suffix_en`)**：一段 25~40 词的标准英文摄影后缀，**必须一字不差地自动拼接到每一个镜头的 `flow_video_prompt_en` 尾部**，从根本上解决纯文生视频跨镜头画风割裂的问题。

### Step 2：总时长切分与生成模式决策（纯文生为主 + 关键帧按需辅助）

根据用户指定的成片总时长（如 15s、30s、45s、60s），突破 Google Flow 单次生成上限：
- **成片单镜时长 (Edit Duration)**：遵循商业大片黄金节奏，单镜剪辑时长控制在 **3s ~ 6s**（前 3s 黄金视觉钩子 → 中段节奏递进/微距交错 → 高潮快切或升格凝视 → 尾段品牌定格）。
- **Flow 生成时长 (Flow Gen Duration)**：每个镜头在 Google Flow 中默认生成 `5s` 或 `8s`（长镜头可标注使用 SceneBuilder `Extend` 至 `15s`），从中截取动势最完美的核心秒数。
- **智能分配生成模式 (`gen_mode_badge`)**：
  - **`T2V 纯文生`（默认占 70%~80% 镜头）**：用于城市风光、光影空镜、流体粒子、环境氛围。靠【全局风格后缀 + 精确运镜指令】保持一致。
  - **`I2V 首帧垫图 / Ingredients`（占 15%~25% 镜头）**：当画面出现**具体产品本体、品牌 Logo 或绝对不能变形的核心地标定格**时启用。同时输出 `keyframe_image_prompt_en` 供生成首帧或直接上传实拍产品图。
  - **`F2V 首尾帧桥接`（占 5%~10% 关键转场）**：当相邻两镜需要超现实无缝变形（如古建筑藻井无缝化作现代摩天大楼穹顶）时启用。

### Step 3：前后镜头无缝转场桥接设计（Transition Bridge）

严禁让相邻两个镜头毫无逻辑地硬切！在撰写第 $N$ 镜和第 $N+1$ 镜时，必须从 `references/cinematography_and_transitions.md` 的 6 大转场矩阵中选择匹配的转场：
- `MATCH_SHAPE`（图形同心圆/几何匹配转场）
- `WHIP_WIPE`（快速甩镜前景遮罩转场）
- `SPEED_RAMP_DIVE`（极速推镜穿入材质/云层转场）
- `LIGHT_BOKEH`（眩光漫射/失焦呼吸转场）
- `MOTION_RELAY`（同向运动速度接力转场）
- `SCENE_EXTEND`（Google Flow SceneBuilder 原生延展）

**关键要求**：第 $N$ 镜的 `flow_video_prompt_en` 结尾必须包含 `Exit Momentum`（出画动势描述），第 $N+1$ 镜的 `flow_video_prompt_en` 开头必须包含对应的 `Entry Momentum`（入画动势描述）。

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

---

## Storyboard JSON 数据结构规范

生成的 `<project_slug>.json` 必须包含以下字段：

```json
{
  "project_slug": "jingdezhen_30s",
  "project_title": "景德镇：千年窑火，一瓷一世界",
  "category": "城市文旅宣传片",
  "total_duration_sec": 30,
  "aspect_ratio": "16:9",
  "creative_concept": "以『泥、火、釉、光』四重意象串联30秒，用图形匹配（圆形拉坯机→圆形青花碗→古窑穹顶）与火光失焦转场实现一气呵成的东方电影感。",
  "visual_bible": {
    "camera_and_lens": "ARRI Alexa 65, Panavision Primo 70 Anamorphic Lens (35mm & 85mm Macro)",
    "lighting_and_color": "Warm kiln firelight amber contrasting with Song Dynasty Qingbaijade cyan shadows, Kodak Vision3 500T",
    "texture_and_atmosphere": "Subtle 35mm film grain, floating clay dust motes in volumetric light beams, ultra-tactile ceramic glaze",
    "style_suffix_en": "Shot on ARRI Alexa 65, Panavision Primo 70 anamorphic lens, Kodak Vision3 500T 35mm film grain, warm amber kiln rim lighting contrasting with deep cyan shadows, volumetric atmospheric mist, cinematic commercial color grading, photorealistic, 8k, smooth camera movement."
  },
  "product_dna": {
    "enabled": false,
    "subject_lock_en": "",
    "materials_and_reflections": "",
    "ingredients_strategy": ""
  },
  "audio_guide": {
    "bgm_style": "前半段空灵古琴泛音与陶土揉捏ASMR低频，15秒起加入史诗感大提琴与现代电子脉冲鼓点，25秒瓷器清脆敲击声收尾。",
    "bgm_prompt_en": "Cinematic oriental ambient soundtrack, ethereal Guqin harmonics and tactile ceramic percussion building into epic orchestral cello and modern deep cinematic bass pulse, emotional, Wong Kar-wai and A24 film score aesthetic, 90 BPM."
  },
  "shots": [
    {
      "shot_id": "SHOT 01",
      "phase_name": "黄金钩子 · 指尖生泥",
      "timeline": "00:00 - 00:04",
      "edit_duration_sec": 4,
      "flow_gen_duration_sec": 8,
      "gen_mode_badge": "T2V 纯文生",
      "gen_mode_reason": "湿润陶土旋转特写属于高质感流体/材质镜头，纯文生配合微距光影词即可展现极佳质感。",
      "visual_summary_zh": "光影暗室中，老匠人布满纹理的双手在高速旋转的拉坯机上塑出湿润的圆形陶碗中心。",
      "visual_detail_zh": "极近景俯拍（Top-down Macro），一束温暖的琥珀色侧逆光切过暗室，湿润的高岭土在拉坯转盘中心高速旋转，匠人苍劲的双手稳稳按压出完美的同心圆碗口，细密的水珠与泥浆微粒在光束中飞溅。",
      "camera_movement_zh": "垂直90度俯拍旋转推进（Top-down overhead shot slowly spiraling and pushing in toward the spinning circular center）",
      "entry_bridge_zh": "开篇第一镜：黑场中一束丁达尔暖光骤然亮起，聚焦于旋转的陶土中心。",
      "transition_type": "MATCH_SHAPE (同心圆图形匹配)",
      "transition_to_next_zh": "镜头最后1秒急速推进至圆形陶坯正中心占满画面80%，与下一镜圆形古窑天窗/青花圆盘形成1:1同心圆图形匹配转场。",
      "flow_video_prompt_en": "Extreme close-up overhead top-down shot of weathered artisan hands shaping wet spinning porcelain clay on a potter's wheel. Shimmering water droplets and fine mist fly off the spinning circular rim in slow motion. At the end of the shot, the camera pushes in rapidly with a clockwise spiral directly into the dark circular center of the clay bowl until the circle fills the frame. Shot on ARRI Alexa 65, Panavision Primo 70 anamorphic lens, Kodak Vision3 500T 35mm film grain, warm amber kiln rim lighting contrasting with deep cyan shadows, volumetric atmospheric mist, cinematic commercial color grading, photorealistic, 8k, smooth camera movement.",
      "keyframe_image_prompt_en": "",
      "voiceover_zh": "一捧高岭土，在指尖醒来。",
      "sfx_zh": "低沉的转盘转动声、湿润泥土摩挲声与水滴飞溅高保真ASMR",
      "sfx_prompt_en": "ASMR wet clay spinning on potter wheel, gentle water splashes, deep resonant room tone"
    }
  ]
}
```
