# 🎬 Google Flow Director (`google-flow-director`)

专为 **Google Flow (Veo)** 打造的 AI 商业广告与宣传片导演工作台（Agent Skill + 自动化分镜导出引擎）。

聚焦 **「城市文旅宣传片」**、**「品牌情绪 TVC」** 与 **「产品高光展示」** 三大商业视频方向，解决 Google Flow 单次生成 5s~15s 限制下的**多段视觉一致性**与**无缝转场桥接**难题。

---

## ✨ 核心特性

1. **全局视觉圣经（Global Visual Bible 一致性锁）**
   - 自动为全片锁定摄影机型号、变形宽银幕/微距镜头焦段、胶片颗粒与色温光影基底（`style_suffix_en`），强制注入每个镜头的 Google Flow Prompt 尾部，确保 80% 纯文生视频（T2V）跨镜头画风高度统一。
2. **纯文生为主 + 关键镜头按需首尾帧/垫图（80/20 黄金法则）**
   - **T2V 纯文生**：大气风光、流体水墨、光影粒子、环境空镜直接纯文生。
   - **I2V 首帧垫图（Ingredients）**：针对核心产品 SKU、品牌 Logo 或标志性器物，支持上传实拍产品图自动提取视觉 DNA，或输出高精首帧生图 Prompt。
   - **F2V 首尾帧桥接**：针对高难度跨时空变形转场，精准定义首尾帧状态。
3. **6 大电影级无缝转场矩阵（Transition Bridge）**
   - 内置 `MATCH_SHAPE`（同心圆/几何图形匹配）、`WHIP_WIPE`（快速甩镜前景遮罩）、`SPEED_RAMP_DIVE`（微距极速穿入）、`LIGHT_BOKEH`（散景光斑失焦呼吸）、`MOTION_RELAY`（同向运动速度接力）与 `SCENE_EXTEND`（Flow 原生延展），让上一段结尾动势与下一段开头动势严丝合缝。
4. **双模交付引擎（Markdown 执行单 + 交互式 HTML 故事板）**
   - 一键输出商业级 `.md` 拍摄执行单与暗黑模式 `.html` 可视化导演工作台（含时间轴节奏条、转场连线胶囊、Google Flow / Suno BGM 一键复制按钮）。

---

## 📂 仓库目录结构（代码与方法论层 — 部署于 GitHub）

```text
google-flow-director/
├── SKILL.md                                     # Agent Skill 核心工作流与 JSON 规范
├── README.md                                    # 项目架构与使用文档
├── references/
│   └── cinematography_and_transitions.md        # 商业摄影机后缀词库与 6 大无缝转场公式
├── scripts/
│   ├── export_storyboard.py                     # Markdown + 交互式 HTML 故事板编译引擎
│   └── sync_to_drive.py                         # 一键同步项目成片分镜与资产至 Google Drive
└── examples/
    └── jingdezhen_tourism_30s.json              # 实战样片：《景德镇：千年窑火》30s 分镜 JSON
```

---

## ☁️ GitHub 与 Google Drive 云盘协同分工架构

为了保证代码版本干净、资产存储安全高效，本项目采用 **「GitHub 管引擎与方法论 + Google Drive 管项目剧本与多媒体资产」** 的双云架构：

| 平台 | 存放内容 | 原因与优势 |
| :--- | :--- | :--- |
| **GitHub 仓库** (`google-flow-director`) | `SKILL.md` 提示词工程架构、摄影与转场词库 (`references/`)、自动化导出与同步脚本 (`scripts/`)、标准 JSON 模板 (`examples/`) | 适合版本控制、跨设备/跨环境拉取 Skill、持续迭代导演算法与转场词库。 |
| **Google Drive 云盘** (`Google_Flow_Director_Projects/`) | 每次生成的具体项目文件夹：包含 `.md` 分镜执行单（可在线转 Google Docs 协作）、`.html` 交互故事板、`.json` 分镜源数据、上传的**产品实拍参考图/首尾帧垫图**、以及 Google Flow 生成的 `.mp4` 视频片段 | 适合存放大图、视频素材与每次产出的业务分镜文档，方便手机/电脑随时查看与团队共享。 |

---

## 🚀 快速使用命令

### 1. 编译生成本地 Markdown 执行单与 HTML 交互故事板

```bash
python3 scripts/export_storyboard.py examples/jingdezhen_tourism_30s.json \
  --out-dir ./output
```

### 2. 将生成的项目资产一键归档至 Google Drive 云盘

```bash
python3 scripts/sync_to_drive.py --project-dir /home/antigravity/flow_projects
```
