---
name: google-flow-director
description: Google Flow (Veo) 端到端全自动商业制片流水线 Skill。专注于「城市文旅宣传片」、「品牌情绪 TVC」与「产品高光展示」三大方向。内置「主创导演 + 挑剔技术总监」双视角审稿、【强制人工整体脚本审核门禁】、「13.5s 防吞尾安全线 + 发音/字幕双轨词」机制、多模视频批量获取与版本归档（Veo API / Google Drive 云桥接 / 本地 Chrome CDP）、首尾转场咬合抽检，以及基于 Python (PIL) + ffmpeg 的全自动宽银幕/中英字幕/书法落版成片合成与 Google Drive 全资产归档。
---

# Google Flow Director v2.0 (`google-flow-director`)

专为 **Google Flow (Veo 原生音画一体生成)** 打造的**端到端全自动商业制片系统**。从一句话创意或一张产品实拍图出发，经过**双角色挑刺审稿**与**人工整体脚本确认**后，自动串联分镜校验、视频获取、转场抽检、`PIL + ffmpeg` 商业级字幕与落版包装，直至输出可发布的 `final_master.mp4` 母带并归档至 Google Drive。

---

## 核心执行流程（7 步端到端全自动制片流水线 · 含人工脚本审核门禁）

每次用户提出视频创作需求时，必须严格按以下 **7 个阶段**推进（其中 **Stage 3 为强制人工审核暂停点**，未经用户点头严禁跳入批量生成）：

### Stage 1：产品视觉 DNA 解构与全局音画双锁立项

1. **提取产品/参考图 DNA（如有附图）**：调用 `view_file` 解析几何比例、表面材质反光与色彩特征，定义为固定英文锚点 `subject_lock_en`，规划 `T2V`（70%~85% 空镜流体）与 `I2V Ingredients / F2V`（15%~25% 核心器物/SKU）配比。
2. **锁定全局音画双圣经（查阅 `references/cinematography_and_transitions.md`）**：
   - **全局视觉锁 (`style_suffix_en`)**：统一摄影机、镜头焦段、胶片颗粒与色温，末尾强制附带 `clean frame without text, no subtitles, no watermarks, no UI borders`。
   - **全局声音锁 (`voice_and_audio_lock_en`)**：固定跨镜头旁白人设音色（如央视纪录片磁性男中音 / 高奢静奢女声）与配乐演进，防止切镜换人。

### Stage 2：「主创导演 + 挑剔技术总监」双视角博弈打磨剧本

不要写完初稿直接交付，必须在内部完成两轮视角切换：
1. **角色 A（商业主创导演）**：编写分场叙事线、分秒段连续运镜（如 `[0-5s] -> [5-10s] -> [10-13.5s] -> [13.5-15s 余韵留白]`）、6 大无缝转场桥接（`LIGHT_BOKEH` / `WHIP_WIPE` / `MATCH_SHAPE` / `SPEED_RAMP_DIVE` / `MOTION_RELAY` / `SCENE_EXTEND`）以及中文旁白初稿。
2. **角色 B（挑剔技术总监 · 专职挑刺）**：对照以下 4 条红线逐镜审查并修正初稿：
   - **防穿模审查**：剔除多人肢体纠缠、当面吞咽进食或复杂手指特写；若出现人物开口，同一时段仅限 1 人说话并注明其余人紧闭双唇。
   - **13.5s 台词防吞尾红线**：15s 镜头旁白必须控制在 **≤36 字**（`13.5s` 前说完），12s 镜头 **≤28 字**（`10.5s` 前说完），单分句 ≤16 字，末尾预留 **≥1.5s** 无旁白余韵/转场过渡区。
   - **发音/字幕双轨隔离**：拆分 `subtitle_display_zh`（用于分镜展示与 `PIL` 后期压制字幕的标准正字）与 `voiceover_phonetic_zh`（写入 Flow Prompt 的发音轨：将『素坯→素批』『古乐→古悦』『重器→仲器』等易错多音字替换为同音唯一字，并在句末强制追加 `……` 延长 0.25s 尾音呼吸）。
   - **转场动势咬合**：确认上一镜尾 `Exit Momentum` 与下一镜首 `Entry Momentum` 亮度、方向与焦点状态真正匹配。

### 🛑 Stage 3：【强制门禁】人工整体脚本审核（Human Script Review Gate）

- **在生成正式大段工程文件或启动任何视频生成前，必须暂停并向用户呈交审核摘要**：
  1. 全片创意结构、总时长切分与转场设计总览表；
  2. 逐镜画面演进 + 正字旁白文案（及多音字注音替换说明）+ 片尾落版大字文案；
  3. 技术总监挑刺自检结果。
- **询问用户是否确认定稿**：
  - 若用户提出修改意见 → 回到 Stage 2 迭代调整并再次呈审；
  - 仅当用户明确确认通过后 → 将 JSON 中 `review_status.human_script_approved` 设为 `true`，进入后续全自动制片流水线！

### Stage 4：提交前自动预检、故事板编译与常驻铁律归档

定稿后将结构化数据保存至 `/home/antigravity/flow_projects/<slug>.json`，依次执行提交前预检与双模导出（假设脚本目录 `$SKILL_DIR` 为仓库目录或 `/shared/user/.gemini/skills/google-flow-director`）：

```bash
python3 $SKILL_DIR/scripts/export_storyboard.py \
  /home/antigravity/flow_projects/<slug>.json \
  --out-dir /home/antigravity/flow_projects \
  --html-artifact <ArtifactDirectoryPath>/<slug>_storyboard.html
```

- 该命令会自动调用 `validate_storyboard.py` 执行 6 项工程铁律核验，并同步生成：
  1. `<slug>_项目铁律与质检清单.md`（常驻项目目录防遗忘）；
  2. `<slug>_分镜执行单.md`；
  3. `<slug>_导演故事板.html`（通过 `write_to_file` 注册为可预览 HTML Artifact）。

### Stage 5：多模视频批量获取与历史版本无损归档 (`generate_clips.py`)

根据当前运行环境自动选择最合适的视频获取模式，所有视频严格按 `raw_clip_01_v1.mp4`、`_v2.mp4` 递增归档，**绝不覆盖历史素材**：

```bash
# 模式 A（云端 API 直连全自动，需配置 GEMINI_API_KEY）：
python3 $SKILL_DIR/scripts/generate_clips.py /home/antigravity/flow_projects/<slug>.json --mode veo-api

# 模式 B（云端 Remote 环境推荐：从对话上传目录或 Google Drive 自动拉取用户在 Flow 网页生成的原片）：
python3 $SKILL_DIR/scripts/generate_clips.py /home/antigravity/flow_projects/<slug>.json --mode local-import
# 或从云盘 03_Google_Flow_生成视频片段_Clips/<slug>/ 拉取：
python3 $SKILL_DIR/scripts/generate_clips.py /home/antigravity/flow_projects/<slug>.json --mode drive-pull

# 模式 C（本地桌面环境：连接本地开启 9222 调试端口并已登录 Google Flow 的 Chrome）：
python3 $SKILL_DIR/scripts/generate_clips.py /home/antigravity/flow_projects/<slug>.json --mode chrome-cdp
```

### Stage 6：原片转场抽检 + Python (`PIL`) & `ffmpeg` 全自动商业母带合成

1. **原片 1fps 抽帧、尾音防截断检测与首尾转场咬合对比图**：
   ```bash
   python3 $SKILL_DIR/scripts/inspect_clips.py /home/antigravity/flow_projects/<slug>.json --mode raw
   ```
   使用 `view_file` 查看生成的 `qa/qa_transition_01_to_02.jpg` 与 `qa/qa_raw_strip_*.jpg`：若局部头尾有半秒瑕疵或停顿略短，无需重拍，直接在 JSON 中微调 `trim_head_sec` / `trim_tail_sec` 或 `pad_tail_sec` (`tpad` 静止帧克隆)。

2. **全自动后期包装与母带无损合成 (`assemble_master.py`)**：
   ```bash
   python3 $SKILL_DIR/scripts/assemble_master.py /home/antigravity/flow_projects/<slug>.json
   ```
   自动完成：`tpad` 首尾呼吸留白 → 转场匹配 `xfade` & `acrossfade` 叠化拼接 → `PIL` 像素级绘制 `2.35:1` 电影宽银幕遮幅、精确时间窗抗锯齿中英双语字幕（无台词时段自动隐藏）、片尾书法/品牌落版大字平滑淡入 → `loudnorm` 广播级响度标准化，输出 `<slug>_final_master.mp4`！

### Stage 7：初次看片观众视角体检 + Google Drive 全生命周期同步

1. **成片 2fps 全片抽帧与切镜点 ±3 帧体检**：
   ```bash
   python3 $SKILL_DIR/scripts/inspect_clips.py /home/antigravity/flow_projects/<slug>.json --mode master
   ```
   切换为**初次看片的挑剔观众视角**，用 `view_file` 检查 `qa_master_2fps_grid.jpg` 与 `qa_master_cut_boundaries.jpg`（核查字幕对齐、切镜黑帧、落版排版与尾音收束），生成 `<slug>_成片体检报告.md`。

2. **一键同步全套分镜、质检图与 `final_master.mp4` 至 Google Drive**：
   ```bash
   python3 $SKILL_DIR/scripts/sync_to_drive.py --project-dir /home/antigravity/flow_projects --slug <slug>
   ```
