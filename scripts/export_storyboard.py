#!/usr/bin/env python3
"""
Google Flow Director — Storyboard Export & Interactive HTML Generator
Reads a structured storyboard JSON specification and outputs:
1. A comprehensive, production-ready Markdown production sheet (.md)
2. A self-contained, interactive dark-mode Director's Storyboard Web App (.html)
   with one-click prompt copying, timeline pacing bars, transition connectors,
   and audio/VO cues.
"""

import argparse
import html
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def generate_markdown(data: dict) -> str:
    title = data.get("project_title", "未命名商业视频项目")
    category = data.get("category", "商业宣传片")
    total_duration = data.get("total_duration_sec", 30)
    aspect_ratio = data.get("aspect_ratio", "16:9")
    creative_concept = data.get("creative_concept", "")
    visual_bible = data.get("visual_bible", {})
    product_dna = data.get("product_dna", None)
    audio_guide = data.get("audio_guide", {})
    shots = data.get("shots", [])

    lines = [
        f"# 🎬 《{title}》Google Flow 导演执行分镜单",
        "",
        f"- **项目类型**：{category}",
        f"- **目标成片总时长**：{total_duration} 秒 | **画幅比例**：`{aspect_ratio}`",
        f"- **镜头总数**：{len(shots)} 个分镜（适配 Google Flow 5s~8s 生成机制与无缝桥接）",
        f"- **核心创意阐述**：{creative_concept}",
        "",
        "---",
        "",
        "## 一、 全局视觉圣经 (Global Visual Bible — 一致性锁)",
        "",
        "> **使用说明**：以下【全局风格后缀】已自动拼接至下方每个镜头的 Google Flow 英文 Prompt 尾部，确保所有独立生成的视频片段拥有相同的摄影机质感、胶片颗粒、色温与光影逻辑。",
        "",
        f"- **摄影机与镜头组 (Camera & Lens)**：{visual_bible.get('camera_and_lens', 'ARRI Alexa 65, Anamorphic Lens')}",
        f"- **光影与色彩基底 (Lighting & Color Palette)**：{visual_bible.get('lighting_and_color', 'Golden hour rim light, teal and orange grading')}",
        f"- **材质与空气感 (Texture & Atmosphere)**：{visual_bible.get('texture_and_atmosphere', '35mm film grain, volumetric mist, photorealistic 8k')}",
        "- **全局强制锁定后缀 (Global Style Suffix)**：",
        "```text",
        visual_bible.get("style_suffix_en", ""),
        "```",
        "",
    ]

    if product_dna and product_dna.get("enabled"):
        lines.extend([
            "## 二、 产品/品牌视觉 DNA 锚点 (Product & Brand Visual DNA)",
            "",
            f"- **主体标准外观描述 (Subject Lock EN)**：`{product_dna.get('subject_lock_en', '')}`",
            f"- **材质与反光特征**：{product_dna.get('materials_and_reflections', '')}",
            f"- **Google Flow 垫图策略 (Ingredients Guide)**：{product_dna.get('ingredients_strategy', '')}",
            "",
        ])

    lines.extend([
        "## 三、 全局声音与音乐指导 (BGM & Soundscape)",
        "",
        f"- **BGM 音乐风格与节奏推进**：{audio_guide.get('bgm_style', '')}",
        f"- **Suno / Udio 配乐生成 Prompt**：",
        "```text",
        audio_guide.get("bgm_prompt_en", ""),
        "```",
        "",
        "---",
        "",
        "## 四、 分镜时间轴与转场总览表",
        "",
        "| 镜号 | 时间轴 (成片) | Flow生成时长 | 生成模式 | 景别/运镜 | 画面核心内容 | 转场桥接设计 (衔接下一镜) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for s in shots:
        lines.append(
            f"| **{s.get('shot_id')}** | `{s.get('timeline')}` ({s.get('edit_duration_sec')}s) | "
            f"`{s.get('flow_gen_duration_sec', 8)}s` | **{s.get('gen_mode_badge', 'T2V 纯文生')}** | "
            f"{s.get('camera_movement_zh', '')} | {s.get('visual_summary_zh', '')} | "
            f"{s.get('transition_to_next_zh', '尾帧定格淡出')} |"
        )

    lines.extend(["", "---", "", "## 五、 逐镜 Google Flow 实操指令卡", ""])

    for idx, s in enumerate(shots, 1):
        lines.extend([
            f"### 🎞️ {s.get('shot_id')} | {s.get('phase_name', '段落')} (`{s.get('timeline')}` · 成片截取 {s.get('edit_duration_sec')}s / Flow生成 {s.get('flow_gen_duration_sec', 8)}s)",
            "",
            f"- **生成模式**：`{s.get('gen_mode_badge', 'T2V 纯文生')}` — {s.get('gen_mode_reason', '纯文生即可保证高质感')}",
            f"- **画面与动作拆解 (中文)**：{s.get('visual_detail_zh', '')}",
            f"- **摄影机调度 (Camera Control)**：{s.get('camera_movement_zh', '')}",
            "",
            "#### 📋 Google Flow 视频生成 Prompt（直接复制）",
            "```text",
            s.get("flow_video_prompt_en", ""),
            "```",
            "",
        ])

        if s.get("keyframe_image_prompt_en"):
            lines.extend([
                "#### 🖼️ 首帧/垫图生成 Prompt（用于 Imagen / Midjourney / Flow Ingredients）",
                "```text",
                s.get("keyframe_image_prompt_en", ""),
                "```",
                "",
            ])

        lines.extend([
            "#### 🔗 前后镜头无缝转场执行 (Transition Bridge)",
            f"- **承接上一镜 (Entry State)**：{s.get('entry_bridge_zh', '开篇首镜，从黑场或光影中渐显')}",
            f"- **交接下一镜 (Exit State -> Next)**：**【{s.get('transition_type', 'MATCH_CUT')}】** {s.get('transition_to_next_zh', '')}",
            "",
            "#### 🎙️ 声音与旁白 (Audio & Voiceover)",
            f"- **旁白/字幕文案 (VO)**：「{s.get('voiceover_zh', '（纯画面与音乐呼吸，无旁白）')}」",
            f"- **环境音效 Prompt (SFX)**：`{s.get('sfx_prompt_en', '')}` ({s.get('sfx_zh', '')})",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def generate_html(data: dict) -> str:
    title = html.escape(data.get("project_title", "未命名商业视频项目"))
    category = html.escape(data.get("category", "商业宣传片"))
    total_duration = data.get("total_duration_sec", 30)
    aspect_ratio = html.escape(data.get("aspect_ratio", "16:9"))
    creative_concept = html.escape(data.get("creative_concept", ""))
    visual_bible = data.get("visual_bible", {})
    product_dna = data.get("product_dna", None)
    audio_guide = data.get("audio_guide", {})
    shots = data.get("shots", [])

    # Build timeline blocks
    timeline_blocks_html = []
    colors = ["#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#fb7185", "#fbbf24", "#34d399", "#2dd4bf"]
    for i, s in enumerate(shots):
        dur = float(s.get("edit_duration_sec", 4))
        pct = max((dur / float(total_duration)) * 100.0, 5.0)
        color = colors[i % len(colors)]
        shot_id = html.escape(s.get("shot_id", f"S{i+1:02d}"))
        phase = html.escape(s.get("phase_name", ""))
        timeline_blocks_html.append(
            f'<a href="#shot-{i+1}" class="tl-seg" style="width:{pct:.1f}%; --seg-color:{color};" '
            f'title="{shot_id}: {phase} ({dur}s)">'
            f'<span class="tl-id">{shot_id}</span>'
            f'<span class="tl-dur">{dur:g}s</span>'
            f'</a>'
        )

    # Product DNA block
    product_dna_html = ""
    if product_dna and product_dna.get("enabled"):
        product_dna_html = f"""
        <section class="panel dna-panel">
            <div class="panel-header">
                <span class="badge badge-amber">PRODUCT / BRAND DNA</span>
                <h2>产品与品牌视觉锚点（垫图一致性锁）</h2>
            </div>
            <div class="grid-2">
                <div class="info-box">
                    <div class="info-label">材质与光影反射特征</div>
                    <div class="info-val">{html.escape(product_dna.get('materials_and_reflections', ''))}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">Google Flow Ingredients 垫图策略</div>
                    <div class="info-val">{html.escape(product_dna.get('ingredients_strategy', ''))}</div>
                </div>
            </div>
            <div class="prompt-box">
                <div class="prompt-header">
                    <span>Subject Lock Prompt (固定主体英文描述词)</span>
                    <button class="copy-btn" onclick="copyText(this)">复制 Prompt</button>
                </div>
                <pre>{html.escape(product_dna.get('subject_lock_en', ''))}</pre>
            </div>
        </section>
        """

    # Shots cards
    shot_cards_html = []
    for i, s in enumerate(shots):
        color = colors[i % len(colors)]
        mode_badge = html.escape(s.get("gen_mode_badge", "T2V 纯文生"))
        is_i2v = "I2V" in mode_badge or "F2V" in mode_badge or "首" in mode_badge or "垫图" in mode_badge
        badge_class = "badge-purple" if is_i2v else "badge-cyan"

        kf_html = ""
        if s.get("keyframe_image_prompt_en"):
            kf_html = f"""
            <div class="prompt-box kf-box">
                <div class="prompt-header">
                    <span>🖼️ 首帧定妆图 / Ingredients 垫图 Prompt (Imagen / MJ)</span>
                    <button class="copy-btn" onclick="copyText(this)">复制首帧 Prompt</button>
                </div>
                <pre>{html.escape(s.get('keyframe_image_prompt_en', ''))}</pre>
            </div>
            """

        transition_connector = ""
        if i < len(shots) - 1:
            t_type = html.escape(s.get("transition_type", "MATCH CUT"))
            t_desc = html.escape(s.get("transition_to_next_zh", ""))
            transition_connector = f"""
            <div class="transition-bridge">
                <div class="bridge-line"></div>
                <div class="bridge-pill">
                    <span class="bridge-tag">🔗 转场桥接 · {t_type}</span>
                    <span class="bridge-text">{t_desc}</span>
                </div>
            </div>
            """

        shot_cards_html.append(f"""
        <article id="shot-{i+1}" class="shot-card" style="--shot-accent:{color};">
            <div class="shot-top">
                <div class="shot-title-group">
                    <span class="shot-num">{html.escape(s.get('shot_id', f'SHOT {i+1:02d}'))}</span>
                    <span class="shot-phase">{html.escape(s.get('phase_name', ''))}</span>
                    <span class="shot-time">⏱️ 成片 {html.escape(str(s.get('timeline', '')))} ({s.get('edit_duration_sec')}s) · Flow生成 {s.get('flow_gen_duration_sec', 8)}s</span>
                </div>
                <div class="shot-badges">
                    <span class="badge {badge_class}">{mode_badge}</span>
                </div>
            </div>

            <p class="mode-reason">💡 <strong>一致性与模式说明：</strong>{html.escape(s.get('gen_mode_reason', ''))}</p>

            <div class="shot-grid">
                <div class="info-box">
                    <div class="info-label">🎥 画面内容与动态调度 (中文拆解)</div>
                    <div class="info-val">{html.escape(s.get('visual_detail_zh', ''))}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">🕹️ 摄影机运动与转场前后态</div>
                    <div class="info-val">
                        <div><strong>运镜：</strong>{html.escape(s.get('camera_movement_zh', ''))}</div>
                        <div style="margin-top:6px;"><strong>入画承接：</strong>{html.escape(s.get('entry_bridge_zh', ''))}</div>
                    </div>
                </div>
            </div>

            <div class="prompt-box">
                <div class="prompt-header">
                    <span>🎬 Google Flow 视频生成 Prompt (已注入全局视觉锁)</span>
                    <button class="copy-btn" onclick="copyText(this)">一键复制 Flow Prompt</button>
                </div>
                <pre>{html.escape(s.get('flow_video_prompt_en', ''))}</pre>
            </div>

            {kf_html}

            <div class="audio-bar">
                <div class="audio-item">
                    <span class="audio-tag">🎙️ 旁白/字幕 (VO)</span>
                    <span class="audio-text">「{html.escape(s.get('voiceover_zh', '（无旁白，纯画面情绪）'))}」</span>
                </div>
                <div class="audio-item">
                    <span class="audio-tag">🔊 环境音效 (SFX)</span>
                    <code class="sfx-code">{html.escape(s.get('sfx_prompt_en', ''))}</code>
                </div>
            </div>
        </article>
        {transition_connector}
        """)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Google Flow 导演分镜工作台</title>
<style>
  :root {{
    --bg: #0b0f17;
    --card: #131b2e;
    --card-border: #23304d;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --cyan: #38bdf8;
    --purple: #c084fc;
    --amber: #fbbf24;
    --emerald: #34d399;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: radial-gradient(circle at top right, #172554 0%, var(--bg) 45%);
    color: var(--text);
    line-height: 1.6;
    padding: 32px 20px 80px;
  }}
  .container {{ max-width: 1120px; margin: 0 auto; }}
  header {{
    background: linear-gradient(135deg, rgba(30,41,59,0.85), rgba(15,23,42,0.95));
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }}
  h1 {{ font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em; color: #fff; }}
  .meta-pills {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .pill {{
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: var(--cyan);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
  }}
  .concept {{ color: #cbd5e1; font-size: 0.96rem; margin-top: 8px; }}
  .panel {{
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 22px 26px;
    margin-bottom: 24px;
  }}
  .panel-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
  .panel-header h2 {{ font-size: 1.15rem; color: #fff; }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.04em;
  }}
  .badge-cyan {{ background: rgba(56,189,248,0.15); color: var(--cyan); border: 1px solid rgba(56,189,248,0.35); }}
  .badge-purple {{ background: rgba(192,132,252,0.18); color: var(--purple); border: 1px solid rgba(192,132,252,0.4); }}
  .badge-amber {{ background: rgba(251,191,36,0.15); color: var(--amber); border: 1px solid rgba(251,191,36,0.35); }}
  .badge-emerald {{ background: rgba(52,211,153,0.15); color: var(--emerald); border: 1px solid rgba(52,211,153,0.35); }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 16px; }}
  .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-bottom: 16px; }}
  .info-box {{
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    padding: 12px 15px;
  }}
  .info-label {{ font-size: 0.78rem; color: var(--muted); text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }}
  .info-val {{ font-size: 0.92rem; color: #f1f5f9; }}
  .prompt-box {{
    background: #090d16;
    border: 1px solid #1e293b;
    border-radius: 10px;
    overflow: hidden;
    margin-top: 12px;
  }}
  .kf-box {{ border-color: rgba(192,132,252,0.35); }}
  .prompt-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(30, 41, 59, 0.65);
    padding: 8px 14px;
    font-size: 0.8rem;
    color: #cbd5e1;
    font-weight: 600;
  }}
  .copy-btn {{
    background: rgba(56, 189, 248, 0.16);
    color: var(--cyan);
    border: 1px solid rgba(56, 189, 248, 0.4);
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .copy-btn:hover {{ background: var(--cyan); color: #090d16; }}
  pre {{
    padding: 14px;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
    font-size: 0.86rem;
    color: #e2e8f0;
    line-height: 1.55;
  }}
  /* Timeline Bar */
  .timeline-bar {{
    display: flex;
    gap: 4px;
    width: 100%;
    height: 46px;
    margin-top: 10px;
  }}
  .tl-seg {{
    background: rgba(255,255,255,0.05);
    border-top: 3px solid var(--seg-color);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-decoration: none;
    color: var(--text);
    transition: transform 0.15s, background 0.15s;
    overflow: hidden;
  }}
  .tl-seg:hover {{
    transform: translateY(-2px);
    background: rgba(255,255,255,0.12);
  }}
  .tl-id {{ font-size: 0.75rem; font-weight: 700; color: #fff; }}
  .tl-dur {{ font-size: 0.68rem; color: var(--muted); }}

  /* Shot Card */
  .shot-card {{
    background: var(--card);
    border: 1px solid var(--card-border);
    border-left: 4px solid var(--shot-accent);
    border-radius: 14px;
    padding: 22px 26px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
  }}
  .shot-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 10px;
  }}
  .shot-title-group {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .shot-num {{
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--shot-accent);
  }}
  .shot-phase {{
    font-weight: 700;
    color: #fff;
    font-size: 1.02rem;
  }}
  .shot-time {{
    font-size: 0.82rem;
    color: var(--muted);
    background: rgba(15,23,42,0.7);
    padding: 3px 10px;
    border-radius: 6px;
  }}
  .mode-reason {{
    font-size: 0.86rem;
    color: #cbd5e1;
    margin-bottom: 14px;
  }}
  .shot-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 12px;
  }}
  .audio-bar {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px dashed rgba(148,163,184,0.2);
    font-size: 0.88rem;
  }}
  .audio-item {{ display: flex; align-items: center; gap: 8px; flex: 1; min-width: 260px; }}
  .audio-tag {{ color: var(--amber); font-weight: 600; white-space: nowrap; font-size: 0.8rem; }}
  .sfx-code {{
    background: rgba(15,23,42,0.8);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    color: #93c5fd;
  }}
  /* Transition Bridge */
  .transition-bridge {{
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 6px 0;
    position: relative;
  }}
  .bridge-line {{
    width: 2px;
    height: 16px;
    background: linear-gradient(to bottom, var(--cyan), var(--purple));
  }}
  .bridge-pill {{
    background: rgba(30, 41, 59, 0.9);
    border: 1px solid rgba(192, 132, 252, 0.45);
    border-radius: 999px;
    padding: 6px 18px;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 0.84rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }}
  .bridge-tag {{
    color: var(--purple);
    font-weight: 700;
    white-space: nowrap;
  }}
  .bridge-text {{ color: #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-top">
      <h1>🎬 《{title}》Google Flow 导演执行台</h1>
      <div class="meta-pills">
        <span class="pill">{category}</span>
        <span class="pill">成片总长：{total_duration}s</span>
        <span class="pill">画幅：{aspect_ratio}</span>
        <span class="pill">共 {len(shots)} 个分镜单元</span>
      </div>
    </div>
    <p class="concept"><strong>核心创意与叙事线：</strong>{creative_concept}</p>
    <div style="margin-top: 18px;">
      <div class="info-label">⏱️ 全局时间轴与节奏切分（点击色块可跳转对应镜头）</div>
      <div class="timeline-bar">
        {''.join(timeline_blocks_html)}
      </div>
    </div>
  </header>

  <section class="panel">
    <div class="panel-header">
      <span class="badge badge-emerald">GLOBAL VISUAL BIBLE</span>
      <h2>全局视觉圣经（跨镜头一致性锁）</h2>
    </div>
    <div class="grid-3">
      <div class="info-box">
        <div class="info-label">摄影机与镜头焦段</div>
        <div class="info-val">{html.escape(visual_bible.get('camera_and_lens', ''))}</div>
      </div>
      <div class="info-box">
        <div class="info-label">光影基调与色彩科学</div>
        <div class="info-val">{html.escape(visual_bible.get('lighting_and_color', ''))}</div>
      </div>
      <div class="info-box">
        <div class="info-label">空气介质与胶片质感</div>
        <div class="info-val">{html.escape(visual_bible.get('texture_and_atmosphere', ''))}</div>
      </div>
    </div>
    <div class="prompt-box">
      <div class="prompt-header">
        <span>🔒 全局强制风格后缀 (已自动拼入下方每个分镜 Prompt 末尾)</span>
        <button class="copy-btn" onclick="copyText(this)">复制全局后缀</button>
      </div>
      <pre>{html.escape(visual_bible.get('style_suffix_en', ''))}</pre>
    </div>
  </section>

  {product_dna_html}

  <section class="panel">
    <div class="panel-header">
      <span class="badge badge-amber">AUDIO & BGM</span>
      <h2>全局配乐与声音设计</h2>
    </div>
    <div class="info-box" style="margin-bottom:10px;">
      <div class="info-label">音乐风格与情绪推进</div>
      <div class="info-val">{html.escape(audio_guide.get('bgm_style', ''))}</div>
    </div>
    <div class="prompt-box">
      <div class="prompt-header">
        <span>🎵 Suno / Udio 配乐生成 Prompt</span>
        <button class="copy-btn" onclick="copyText(this)">复制配乐 Prompt</button>
      </div>
      <pre>{html.escape(audio_guide.get('bgm_prompt_en', ''))}</pre>
    </div>
  </section>

  <div class="shots-wrapper">
    {''.join(shot_cards_html)}
  </div>
</div>

<script>
function copyText(btn) {{
  const pre = btn.closest('.prompt-box').querySelector('pre');
  navigator.clipboard.writeText(pre.innerText).then(() => {{
    const orig = btn.innerText;
    btn.innerText = '✅ 已复制';
    setTimeout(() => btn.innerText = orig, 1600);
  }});
}}
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Export Google Flow Storyboard JSON to Markdown and Interactive HTML.")
    parser.add_argument("input_json", help="Path to storyboard JSON file")
    parser.add_argument("--out-dir", default="/home/antigravity/flow_projects", help="Output directory for generated files")
    parser.add_argument("--html-artifact", default="", help="Optional path to also write the HTML file as an artifact")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: JSON file not found at {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    slug = data.get("project_slug") or input_path.stem
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_content = generate_markdown(data)
    html_content = generate_html(data)

    md_path = out_dir / f"{slug}_分镜执行单.md"
    html_path = out_dir / f"{slug}_导演故事板.html"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    if args.html_artifact:
        art_path = Path(args.html_artifact)
        art_path.parent.mkdir(parents=True, exist_ok=True)
        with open(art_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    print(f"SUCCESS:\n- Markdown: {md_path}\n- HTML: {html_path}")


if __name__ == "__main__":
    main()
