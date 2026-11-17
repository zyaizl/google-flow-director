# 🎬 Google Flow Director v2.0 (`google-flow-director`)

专为 **Google Flow (Veo)** 打造的 **AI 商业广告与宣传片端到端全自动制片流水线**（Agent Skill + 双角色审稿与预检引擎 + 多模视频获取 + `PIL/ffmpeg` 自动母带合成 + Google Drive 协同归档）。

聚焦 **「城市文旅宣传片」**、**「品牌情绪 TVC」** 与 **「产品高光展示」** 三大商业视频方向，彻底打通从**一句话创意 → 人工脚本审核 → 纯净视频生成 → 转场咬合抽检 → 代码级宽银幕/字幕/落版合成 → 成片复核归档**的完整闭环。

---

## ✨ v2.0 核心特性与工程壁垒

1. **7 步全自动制片 + 强制人工脚本审核门禁（Human-in-the-Loop）**
   - 内置**「商业主创导演 + 挑剔技术总监」双角色博弈写本**，自动剔除穿模动作并优化运镜；在进入视频批量生成前设置**强制人工整体脚本审核门禁**（`human_script_approved`），确保剧本、分镜与旁白完全符合你的心意后再开拍。
2. **「13.5s 台词安全线 + 发音/字幕双轨词」防吞尾与防误读机制**
   - **防吞尾红线**：15s 镜头强制在 `13.5s` 前结束旁白（≤36 字），预留最后 `1.5s` 纯画面光斑/空镜余韵，配合句末 `……` 延长 0.25s 呼吸衰减，根治句尾被腰斩。
   - **双轨词隔离**：`voiceover_phonetic_zh`（送入 Flow Prompt 的同音唯一字防读错版，如『素坯→素批』）与 `subtitle_display_zh`（供后期脚本渲染高清字幕的标准正字版）自动分离。
3. **常驻《项目铁律清单》与提交前代码级预检 (`validate_storyboard.py`)**
   - 自动核查 `clean frame without text` 纯净无字锁、全局视觉/声音双锁 1:1 注入、字数安全上限、多音字预警与转场成对桥接，生成常驻质检清单防长对话遗忘。
4. **云端/本地自适应多模视频获取与无损版本归档 (`generate_clips.py`)**
   - 支持 **Veo API 云端直连 (`veo-api`)**、**Google Drive 云桥接拉取 (`drive-pull`)**、**本地/上传目录导入 (`local-import`)** 与 **桌面 Chrome 9222 远程接管 (`chrome-cdp`)**；所有素材按 `raw_clip_01_v1.mp4`、`_v2.mp4` 递增归档，绝不覆盖旧版。
5. **Python (`PIL`) + `ffmpeg` 全自动商业母带合成 (`assemble_master.py`)**
   - 告别手工开剪映/PR 排字幕：自动执行 `tpad` 首尾静止帧留白、转场匹配 `xfade` 无缝叠化、像素级渲染 **2.35:1 宽银幕遮幅 + 秒级中英双语字幕条 + 片尾城市/品牌书法级落版大字淡入** + `loudnorm` 广播级响度标准化，一键输出 `<slug>_final_master.mp4`。
6. **首尾转场咬合抽检与初次看片 2fps 成片体检 (`inspect_clips.py`)**
   - 原片阶段自动生成 **1fps 检视条 + 上镜尾/下镜首转场咬合对比图 + 句尾音频截断检测**；成片阶段自动执行 **全片 2fps 抽帧 + 切镜点 ±3 帧复核** 并输出体检报告。

---

## 📂 仓库目录结构

```text
google-flow-director/
├── SKILL.md                                     # 7 步端到端全自动制片 Skill 规范（含人工脚本审核门禁）
├── README.md                                    # 项目架构、云端/本地模式说明与 CLI 手册
├── references/
│   └── cinematography_and_transitions.md        # 商业摄影后缀词库、6 大无缝转场矩阵、双轨防吞尾与避坑标准
├── scripts/
│   ├── validate_storyboard.py                   # 提交前技术总监预检器 & 常驻《项目铁律清单》生成器
│   ├── export_storyboard.py                     # Markdown 执行单 + 交互式 HTML 故事板编译引擎（集成预检）
│   ├── generate_clips.py                        # 多模视频获取与 _v1/_v2 无损归档（Veo API / Drive / Upload / CDP）
│   ├── inspect_clips.py                         # 原片转场咬合抽检 & 成片 2fps + 切点 ±3 帧体检引擎
│   ├── assemble_master.py                       # Python (PIL) + ffmpeg 商业宽银幕/双语字幕/落版自动母带合成器
│   └── sync_to_drive.py                         # Google Drive 全生命周期双向归档工具
└── examples/
    └── jingdezhen_tourism_30s.json              # 实战样片：《景德镇：千年窑火》v2 双轨配音与自动母带完整配置
```

---

## ☁️ 云端 Remote 环境 vs. 本地桌面环境：视频获取怎么选？

| 运行环境 | 能否用 Chrome 9222 接管本地浏览器？ | 推荐全自动方案 |
| :--- | :--- | :--- |
| **云端 Remote 沙箱**<br>*(当前 Antigravity Cloud VM)* | ❌ **不能直接连本地电脑浏览器**<br>云端容器与本地电脑网络隔离，且无头浏览器登录个人 Google Labs 易触发异地风控/验证码拦截。 | 1. **纯云端全自动 (`--mode veo-api`)**：配置 `GEMINI_API_KEY`（并放行 `generativelanguage.googleapis.com`），云端直接调官方 Veo API 批量生成下载。<br>2. **云桥接半自动 (`--mode drive-pull` / `local-import`)**：在 HTML 故事板一键复制 Prompt 到你本地浏览器 Flow 生成，原片拖入对话框上传或 Google Drive，**云端自动拉取 → 抽检 → `PIL+ffmpeg` 合成成片母带 → 推回云盘**！ |
| **本地桌面电脑**<br>*(Mac / Windows / Linux)* | ✅ **原生支持 (`--mode chrome-cdp`)** | 本地以 `--remote-debugging-port=9222` 启动已登录 Google Flow 的 Chrome，直接接管浏览器批量生成并归档。 |

---

## 🚀 端到端全流程 CLI 快速命令

### 1. 提交前铁律预检 + 导出 Markdown 执行单与交互式 HTML 故事板

```bash
python3 scripts/export_storyboard.py examples/jingdezhen_tourism_30s.json \
  --out-dir /home/antigravity/flow_projects
```

### 2. 获取与归档视频片段（以测试合成样片或本地导入为例）

```bash
# 干跑实测整条后期合成管线（自动生成带光斑过渡与安全收音的 1080p 测试原片）：
python3 scripts/generate_clips.py examples/jingdezhen_tourism_30s.json \
  --mode demo-synthetic --project-dir /home/antigravity/flow_projects

# 实际生产：导入上传目录原片 / 从 Google Drive 拉取 / 调用 Veo API：
# python3 scripts/generate_clips.py examples/jingdezhen_tourism_30s.json --mode local-import
# python3 scripts/generate_clips.py examples/jingdezhen_tourism_30s.json --mode drive-pull
# GEMINI_API_KEY=xxx python3 scripts/generate_clips.py examples/jingdezhen_tourism_30s.json --mode veo-api
```

### 3. 原片 1fps 抽帧与首尾转场咬合质检

```bash
python3 scripts/inspect_clips.py examples/jingdezhen_tourism_30s.json \
  --mode raw --project-dir /home/antigravity/flow_projects
```

### 4. Python (`PIL`) + `ffmpeg` 全自动商业母带合成（宽银幕 + 双语字幕 + 书法落版）

```bash
python3 scripts/assemble_master.py examples/jingdezhen_tourism_30s.json \
  --project-dir /home/antigravity/flow_projects
```

### 5. 成片 2fps 全片抽帧与切镜点 ±3 帧体检 + Google Drive 全资产归档

```bash
python3 scripts/inspect_clips.py examples/jingdezhen_tourism_30s.json \
  --mode master --project-dir /home/antigravity/flow_projects

python3 scripts/sync_to_drive.py \
  --project-dir /home/antigravity/flow_projects --slug jingdezhen_tourism_30s
```
