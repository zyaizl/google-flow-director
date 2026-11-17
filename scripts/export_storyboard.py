#!/usr/bin/env python3
"""
Google Flow Director — Storyboard Export, Pre-Flight QA & Interactive HTML Generator
Reads a structured storyboard JSON specification, runs Pre-Flight Technical Director QA,
and outputs:
1. A comprehensive Markdown production sheet (`<slug>_分镜执行单.md`)
2. A persistent project iron-rules & QA checklist (`<slug>_项目铁律与质检清单.md`)
3. A self-contained dark-mode Director's Storyboard Web App (`<slug>_导演故事板.html`)
   featuring dual-track voiceover/subtitle display, 13.5s safety cutoff indicators,
   automated mastering preview, and one-click prompt copying.
"""

import argparse
import html
import json
import sys
from pathlib import Path

# Allow sibling import of validate_storyboard
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_storyboard import render_checklist_markdown, validate_storyboard_data  # noqa: E402


def generate_markdown(data: dict, qa_report: dict) -> str:
    title = data.get("project_title", "未命名商业视频项目")
    category = data.get("category", "商业宣传片")
    total_duration = data.get("total_duration_sec", 30)
    aspect_ratio = data.get("aspect_ratio", "16:9")
    creative_concept = data.get("creative_concept", "")
    visual_bible = data.get("visual_bible", {})
    product_dna = data.get("product_dna", None)
    audio_guide = data.get("audio_guide", {})
    post_cfg = data.get("post_production", {})
    end_card = data.get("end_card", {})
    review = data.get("review_status", {})
    shots = data.get("shots", [])

    qa_badge = "✅ 预检通过 (PASS)" if qa_report["passed"] else f"❌ 存在 {qa_report['error_count']} 项待修问题"
    human_badge = "✅ 用户已审核定稿" if qa_report["human_script_approved"] else "⏳ 待用户审核确认（确认前请勿批量生成）"

    lines = [
        f"# 🎬 《{title}》Google Flow 端到端全自动制片执行单",
        "",
        f"- **项目类型**：{category}",
        f"- **目标成片总时长**：{total_duration} 秒 | **画幅比例**：`{aspect_ratio}`",
        f"- **镜头总数**：{len(shots)} 个分镜单元（纯净无字画面 + 13.5s 防吞尾双轨配音 + 代码自动后期合成）",
        f"- **技术总监挑刺预检**：**{qa_badge}** | **人工脚本审核门禁**：**{human_badge}**",
        f"- **审稿说明**：{review.get('review_notes', '遵循六大制片铁律')}",
        f"- **核心创意阐述**：{creative_concept}",
        "",
        "---",
        "",
        "## 一、 全局音画双锁圣经 (Global Visual & Audio Bible — 跨片段一致性锁)",
        "",
        "> **制片铁律**：以下【全局视觉后缀】与【全局配音音色&配乐锁】已 **1:1 内嵌至每个镜头的 Google Flow Prompt**；画面强制 `clean frame without text` 严禁 AI 直出字幕；中文旁白采用**发音防错轨 (`voiceover_phonetic_zh`) + 末尾 `……` 缓冲 + 提前 1.5s 收音**，正字字幕与片尾落版统一由 `scripts/assemble_master.py` (`PIL` + `ffmpeg`) 渲染。",
        "",
        f"- **摄影机与镜头组 (Camera & Lens)**：{visual_bible.get('camera_and_lens', 'ARRI Alexa 65, Anamorphic Lens')}",
        f"- **光影与色彩基底 (Lighting & Color Palette)**：{visual_bible.get('lighting_and_color', 'Golden hour rim light, teal and orange grading')}",
        f"- **材质与空气感 (Texture & Atmosphere)**：{visual_bible.get('texture_and_atmosphere', '35mm film grain, volumetric mist, photorealistic 8k')}",
        f"- **全局配音人设与音色锁 (Narrator Voice Profile)**：{audio_guide.get('voice_profile_zh', '央视纪录片级浑厚磁性男中音，普通话标准，语速沉稳诗意')}",
        "- **全局强制视觉锁定后缀 (Global Visual Style Suffix)**：",
        "```text",
        visual_bible.get("style_suffix_en", ""),
        "```",
        "- **全局强制配音与配乐锁 (Global Voice & Audio Lock)**：",
        "```text",
        audio_guide.get("voice_and_audio_lock_en", audio_guide.get("bgm_prompt_en", "")),
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
        "## 三、 全局配乐与自动化后期母带参数 (Soundscape & Automated Mastering)",
        "",
        f"- **BGM 音乐风格与情绪推进**：{audio_guide.get('bgm_style', '')}",
        f"- **代码后期规格 (`assemble_master.py`)**：分辨率 `{post_cfg.get('resolution', '1920x1080')}` @ `{post_cfg.get('fps', 24)}fps` | "
        f"宽银幕遮幅：`{'开启 (' + str(post_cfg.get('bar_ratio', 2.35)) + ':1)' if post_cfg.get('cinemascope_bars') else '关闭'}` | "
        f"`tpad` 留白：`头 +{post_cfg.get('pad_head_sec', 0)}s / 尾 +{post_cfg.get('pad_tail_sec', 0.35)}s` | "
        f"转场叠化：`{post_cfg.get('crossfade_duration_sec', 0.5)}s`",
    ])
    if end_card and end_card.get("enabled"):
        lines.append(
            f"- **片尾自动落版大字 (`end_card`)**：主标题 **「{end_card.get('title_zh', '')}」** · 副标题 **「{end_card.get('subtitle_zh', '')}」** (`{end_card.get('tagline_en', '')}`)"
        )
    lines.extend([
        "- **独立配乐备用 Prompt (Suno / Udio)**：",
        "```text",
        audio_guide.get("bgm_prompt_en", ""),
        "```",
        "",
        "---",
        "",
        "## 四、 分镜时间轴、双轨防吞尾与转场总览表",
        "",
        "| 镜号 | 时间轴 (成片) | Flow时长 / 台词截止线 | 生成模式 | 画面核心内容 | 正字字幕轨 (`subtitle_display_zh`) | 转场桥接设计 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for s in shots:
        f_dur = s.get("flow_gen_duration_sec", 15)
        cutoff = s.get("vo_safe_cutoff_sec", max(float(f_dur) - 1.5, 6.5))
        disp_vo = s.get("subtitle_display_zh") or s.get("voiceover_zh", "")
        lines.append(
            f"| **{s.get('shot_id')}** | `{s.get('timeline')}` ({s.get('edit_duration_sec')}s) | "
            f"`{f_dur}s` (≤`{cutoff:g}s` 收音) | **{s.get('gen_mode_badge', 'T2V 音画一体')}** | "
            f"{s.get('visual_summary_zh', '')} | 「{disp_vo}」 | "
            f"{s.get('transition_to_next_zh', '尾帧定格淡出')} |"
        )

    lines.extend(["", "---", "", "## 五、 逐镜双轨配音与 Google Flow 一体化指令卡（纯净无字版）", ""])

    for idx, s in enumerate(shots):
        sr = qa_report["shots"][idx] if idx < len(qa_report["shots"]) else {}
        disp_vo = s.get("subtitle_display_zh") or s.get("voiceover_zh", "")
        phon_vo = s.get("voiceover_phonetic_zh") or disp_vo
        cutoff = s.get("vo_safe_cutoff_sec", max(float(s.get("flow_gen_duration_sec", 15)) - 1.5, 6.5))

        lines.extend([
            f"### 🎞️ {s.get('shot_id')} | {s.get('phase_name', '段落')} (`{s.get('timeline')}` · Flow生成 {s.get('flow_gen_duration_sec', 15)}s)",
            "",
            f"- **生成模式**：`{s.get('gen_mode_badge', 'T2V 音画一体')}` — {s.get('gen_mode_reason', '')}",
            f"- **防吞尾安全核验**：共 `{sr.get('cjk_char_count', 0)}` 字（上限 `{sr.get('max_safe_chars', 36)}` 字，预计 `~{sr.get('estimated_vo_sec', 0)}s`），强制 `≤ {cutoff:g}s` 说完，末尾预留 `≥ 1.5s` 静默余韵。",
            f"- **画面与动作拆解 (中文)**：\n{s.get('visual_detail_zh', '')}",
            f"- **摄影机调度 (Camera Control)**：{s.get('camera_movement_zh', '')}",
            f"- **🎙️ Flow 发音防错轨 (`voiceover_phonetic_zh` · 已写入 Prompt)**：「{phon_vo}」",
            f"- **📝 后期正字字幕轨 (`subtitle_display_zh` · 供 `assemble_master.py` 渲染)**：「{disp_vo}」",
            f"- **内嵌同步音效与配乐 (Native SFX & BGM)**：{s.get('sfx_zh', '')}",
        ])

        cues = s.get("subtitle_cues", [])
        if cues:
            lines.append("- **⏱️ 自动化后期字幕时间窗 (`subtitle_cues`)**：")
            for c in cues:
                en_part = f" / *{c.get('text_en')}*" if c.get("text_en") else ""
                lines.append(f"  - `[{c.get('start', 0):04.1f}s - {c.get('end', 0):04.1f}s]` {c.get('text_zh', '')}{en_part}")

        lines.extend([
            "",
            "#### 📋 Google Flow 音画+原生配音一体化 Prompt（直接复制或由 `generate_clips.py` 自动提交）",
            "```text",
            s.get("flow_video_prompt_en", ""),
            "```",
            "",
        ])

        if s.get("keyframe_image_prompt_en"):
            kf_raw = s.get("keyframe_image_prompt_en", "")
            kf_header = (
                "#### 🧩 Flow SceneBuilder 分步延展方案（8s Base + 7s Extend 均含防吞尾配音与音效）"
                if "Extend" in kf_raw
                else "#### 🖼️ 首帧/垫图生成 Prompt（用于 Imagen / Midjourney / Flow Ingredients）"
            )
            lines.extend([
                kf_header,
                "```text",
                kf_raw,
                "```",
                "",
            ])

        lines.extend([
            "#### 🔗 前后镜头无缝转场执行 (Transition Bridge)",
            f"- **承接上一镜 (Entry State)**：{s.get('entry_bridge_zh', '开篇首镜，从黑场或光影中渐显')}",
            f"- **交接下一镜 (Exit State -> Next)**：**【{s.get('transition_type', 'MATCH_CUT')}】** {s.get('transition_to_next_zh', '')}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def generate_html(data: dict, qa_report: dict) -> str:
    title = html.escape(data.get("project_title", "未命名商业视频项目"))
    category = html.escape(data.get("category", "商业宣传片"))
    total_duration = data.get("total_duration_sec", 30)
    aspect_ratio = html.escape(data.get("aspect_ratio", "16:9"))
    creative_concept = html.escape(data.get("creative_concept", ""))
    visual_bible = data.get("visual_bible", {})
    product_dna = data.get("product_dna", None)
    audio_guide = data.get("audio_guide", {})
    post_cfg = data.get("post_production", {})
    end_card = data.get("end_card", {})
    review = data.get("review_status", {})
    shots = data.get("shots", [])

    qa_status_text = "✅ 技术总监预检通过 (0 硬伤)" if qa_report["passed"] else f"❌ 预检拦截 ({qa_report['error_count']} 项错误)"
    qa_pill_style = (
        "background:rgba(52,211,153,0.16);border-color:rgba(52,211,153,0.45);color:#34d399;"
        if qa_report["passed"]
        else "background:rgba(251,113,133,0.18);border-color:rgba(251,113,133,0.5);color:#fb7185;"
    )
    human_status_text = "✅ 人工脚本审核已通过" if qa_report["human_script_approved"] else "⏳ 待人工审核确认脚本"

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
            f'title="{shot_id}: {phase} ({dur:g}s)">'
            f'<span class="tl-id">{shot_id}</span>'
            f'<span class="tl-dur">{dur:g}s</span>'
            f'</a>'
        )

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

    end_card_html = ""
    if end_card and end_card.get("enabled"):
        end_card_html = f"""
        <div class="info-box">
            <div class="info-label">🎬 片尾书法/品牌落版大字 (`assemble_master.py` 自动合成)</div>
            <div class="info-val">
                <strong>{html.escape(end_card.get('title_zh', ''))}</strong> · {html.escape(end_card.get('subtitle_zh', ''))}
                <div style="font-size:0.78rem; color:#94a3b8; margin-top:2px;">{html.escape(end_card.get('tagline_en', ''))}</div>
            </div>
        </div>
        """

    shot_cards_html = []
    for i, s in enumerate(shots):
        sr = qa_report["shots"][i] if i < len(qa_report["shots"]) else {}
        color = colors[i % len(colors)]
        mode_badge = html.escape(s.get("gen_mode_badge", "T2V 音画一体"))
        is_i2v = any(k in mode_badge for k in ("I2V", "F2V", "首", "垫图"))
        badge_class = "badge-purple" if is_i2v else "badge-cyan"

        disp_vo = html.escape(s.get("subtitle_display_zh") or s.get("voiceover_zh", ""))
        phon_vo = html.escape(s.get("voiceover_phonetic_zh") or s.get("voiceover_zh", ""))
        f_dur = s.get("flow_gen_duration_sec", 15)
        cutoff = s.get("vo_safe_cutoff_sec", max(float(f_dur) - 1.5, 6.5))

        cues_html = ""
        cues = s.get("subtitle_cues", [])
        if cues:
            cue_row_items = []
            for c in cues:
                en_sub = f' <span style="color:#64748b;">/ {html.escape(c.get("text_en", ""))}</span>' if c.get("text_en") else ""
                cue_row_items.append(
                    f'<div style="font-size:0.82rem; color:#cbd5e1; margin-top:3px;">'
                    f'<code style="color:#38bdf8;">[{c.get("start",0):04.1f}s-{c.get("end",0):04.1f}s]</code> '
                    f'{html.escape(c.get("text_zh", ""))}{en_sub}</div>'
                )
            cue_rows = "".join(cue_row_items)
            cues_html = f'<div style="margin-top:8px; padding-top:6px; border-top:1px dashed rgba(148,163,184,0.16);"><div class="info-label">⏱️ PIL 自动渲染字幕时间窗</div>{cue_rows}</div>'

        kf_html = ""
        if s.get("keyframe_image_prompt_en"):
            kf_raw = s.get("keyframe_image_prompt_en", "")
            kf_title = (
                "🧩 Flow SceneBuilder 分步延展方案 (8s Base + 7s Extend 均含防吞尾配音与音效)"
                if "Extend" in kf_raw
                else "🖼️ 首帧定妆图 / Ingredients 垫图 Prompt (Imagen / MJ)"
            )
            kf_html = f"""
            <div class="prompt-box kf-box">
                <div class="prompt-header">
                    <span>{kf_title}</span>
                    <button class="copy-btn" onclick="copyText(this)">复制分步方案</button>
                </div>
                <pre>{html.escape(kf_raw)}</pre>
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
                    <span class="shot-time">⏱️ 成片 {html.escape(str(s.get('timeline', '')))} ({s.get('edit_duration_sec')}s) · Flow {f_dur}s · 旁白截止 ≤{cutoff:g}s</span>
                </div>
                <div class="shot-badges">
                    <span class="badge badge-emerald">字数 {sr.get('cjk_char_count', 0)}/{sr.get('max_safe_chars', 36)} (~{sr.get('estimated_vo_sec', 0)}s)</span>
                    <span class="badge {badge_class}">{mode_badge}</span>
                </div>
            </div>

            <p class="mode-reason">💡 <strong>一致性与防吞尾说明：</strong>{html.escape(s.get('gen_mode_reason', ''))}</p>

            <div class="shot-grid">
                <div class="info-box">
                    <div class="info-label">🎥 画面内容与分秒段调度 (中文拆解)</div>
                    <div class="info-val" style="white-space:pre-line;">{html.escape(s.get('visual_detail_zh', ''))}</div>
                </div>
                <div class="info-box">
                    <div class="info-label">🕹️ 运镜轨迹 &amp; 🎙️ 双轨防读错/防吞尾配音设定</div>
                    <div class="info-val">
                        <div><strong>运镜轨迹：</strong>{html.escape(s.get('camera_movement_zh', ''))}</div>
                        <div style="margin-top:5px;"><strong>入画承接：</strong>{html.escape(s.get('entry_bridge_zh', ''))}</div>
                        <div style="margin-top:8px; padding-top:8px; border-top:1px dashed rgba(148,163,184,0.2);">
                            <div><strong style="color:#fbbf24;">🎙️ Flow 发音防错轨 (同音单字 + 末尾……防吞尾)：</strong>「{phon_vo}」</div>
                            <div style="margin-top:4px;"><strong style="color:#38bdf8;">📝 后期高清正字字幕轨 (PIL 逐层压制)：</strong>「{disp_vo}」</div>
                            <div style="margin-top:4px;"><strong style="color:#34d399;">🔊 同步音效与配乐：</strong>{html.escape(s.get('sfx_zh', ''))}</div>
                        </div>
                        {cues_html}
                    </div>
                </div>
            </div>

            <div class="prompt-box">
                <div class="prompt-header">
                    <span>🎬🎙️ Google Flow 音画+原生配音一体化 Prompt（纯净无字 · ≤{cutoff:g}s 收音 + 1.5s 余韵留白）</span>
                    <button class="copy-btn" onclick="copyText(this)">一键复制完整 Flow Prompt</button>
                </div>
                <pre>{html.escape(s.get('flow_video_prompt_en', ''))}</pre>
            </div>

            {kf_html}
        </article>
        {transition_connector}
        """)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Google Flow 全自动制片工作台</title>
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
  .container {{ max-width: 1140px; margin: 0 auto; }}
  header {{
    background: linear-gradient(135deg, rgba(30,41,59,0.85), rgba(15,23,42,0.95));
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
  }}
  .header-top {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }}
  h1 {{ font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em; color: #fff; }}
  .meta-pills {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .pill {{
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: var(--cyan);
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
  }}
  .concept {{ color: #cbd5e1; font-size: 0.95rem; margin-top: 8px; }}
  .review-bar {{
    margin-top: 12px;
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(52, 211, 153, 0.3);
    font-size: 0.86rem;
    color: #cbd5e1;
  }}
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
    letter-spacing: 0.03em;
  }}
  .badge-cyan {{ background: rgba(56,189,248,0.15); color: var(--cyan); border: 1px solid rgba(56,189,248,0.35); }}
  .badge-purple {{ background: rgba(192,132,252,0.18); color: var(--purple); border: 1px solid rgba(192,132,252,0.4); }}
  .badge-amber {{ background: rgba(251,191,36,0.15); color: var(--amber); border: 1px solid rgba(251,191,36,0.35); }}
  .badge-emerald {{ background: rgba(52,211,153,0.15); color: var(--emerald); border: 1px solid rgba(52,211,153,0.35); }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin-bottom: 16px; }}
  .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-bottom: 16px; }}
  .info-box {{
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    padding: 12px 15px;
  }}
  .info-label {{ font-size: 0.77rem; color: var(--muted); text-transform: uppercase; margin-bottom: 4px; font-weight: 600; }}
  .info-val {{ font-size: 0.91rem; color: #f1f5f9; }}
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
    gap: 10px;
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
    white-space: nowrap;
    transition: all 0.15s;
  }}
  .copy-btn:hover {{ background: var(--cyan); color: #090d16; }}
  pre {{
    padding: 14px;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
    font-size: 0.85rem;
    color: #e2e8f0;
    line-height: 1.55;
  }}
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
  .shot-badges {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .shot-num {{ font-size: 1.1rem; font-weight: 800; color: var(--shot-accent); }}
  .shot-phase {{ font-weight: 700; color: #fff; font-size: 1.0rem; }}
  .shot-time {{
    font-size: 0.8rem;
    color: var(--muted);
    background: rgba(15,23,42,0.7);
    padding: 3px 10px;
    border-radius: 6px;
  }}
  .mode-reason {{ font-size: 0.86rem; color: #cbd5e1; margin-bottom: 14px; }}
  .shot-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 12px;
  }}
  .transition-bridge {{
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 6px 0;
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
  .bridge-tag {{ color: var(--purple); font-weight: 700; white-space: nowrap; }}
  .bridge-text {{ color: #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-top">
      <h1>🎬 《{title}》全自动制片执行台</h1>
      <div class="meta-pills">
        <span class="pill" style="{qa_pill_style}">{qa_status_text}</span>
        <span class="pill">{human_status_text}</span>
        <span class="pill">{category}</span>
        <span class="pill">成片总长：{total_duration}s ({aspect_ratio})</span>
      </div>
    </div>
    <p class="concept"><strong>核心创意与叙事线：</strong>{creative_concept}</p>
    <div class="review-bar">
      <strong>🛡️ 双角色挑刺与铁律审计：</strong>{html.escape(review.get('review_notes', '已启用双轨防读错/防吞尾机制与代码级自动后期合成。'))}
    </div>
    <div style="margin-top: 18px;">
      <div class="info-label">⏱️ 全局时间轴与节奏切分（点击色块可跳转对应镜头）</div>
      <div class="timeline-bar">
        {''.join(timeline_blocks_html)}
      </div>
    </div>
  </header>

  <section class="panel">
    <div class="panel-header">
      <span class="badge badge-emerald">GLOBAL VISUAL, AUDIO &amp; MASTERING BIBLE</span>
      <h2>全局音画双锁与 Python + ffmpeg 自动母带配置</h2>
    </div>
    <div class="grid-3">
      <div class="info-box">
        <div class="info-label">摄影机与镜头焦段</div>
        <div class="info-val">{html.escape(visual_bible.get('camera_and_lens', ''))}</div>
      </div>
      <div class="info-box">
        <div class="info-label">🎙️ 全局配音人设与音色锁</div>
        <div class="info-val">{html.escape(audio_guide.get('voice_profile_zh', ''))}</div>
      </div>
      <div class="info-box">
        <div class="info-label">🎞️ 自动后期参数 (`assemble_master.py`)</div>
        <div class="info-val">
          {html.escape(str(post_cfg.get('resolution', '1920x1080')))} @ {post_cfg.get('fps', 24)}fps ·
          tpad 尾留 +{post_cfg.get('pad_tail_sec', 0.35)}s · 叠化 {post_cfg.get('crossfade_duration_sec', 0.5)}s
        </div>
      </div>
      {end_card_html}
    </div>
    <div class="prompt-box">
      <div class="prompt-header">
        <span>🔒 全局强制视觉后缀 (已 1:1 内嵌至下方每个分镜 Prompt)</span>
        <button class="copy-btn" onclick="copyText(this)">复制视觉锁</button>
      </div>
      <pre>{html.escape(visual_bible.get('style_suffix_en', ''))}</pre>
    </div>
    <div class="prompt-box">
      <div class="prompt-header">
        <span>🎙️🎵 全局强制配音音色与配乐锁 (已 1:1 内嵌至下方每个分镜 Prompt)</span>
        <button class="copy-btn" onclick="copyText(this)">复制声音锁</button>
      </div>
      <pre>{html.escape(audio_guide.get('voice_and_audio_lock_en', audio_guide.get('bgm_prompt_en', '')))}</pre>
    </div>
  </section>

  {product_dna_html}

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
    parser = argparse.ArgumentParser(description="Export Google Flow Storyboard JSON to Markdown, QA Checklist, and Interactive HTML.")
    parser.add_argument("input_json", help="Path to storyboard JSON file")
    parser.add_argument("--out-dir", default="/home/antigravity/flow_projects", help="Output directory for generated files")
    parser.add_argument("--html-artifact", default="", help="Optional path to also write the HTML file as an artifact")
    parser.add_argument("--skip-qa-fail", action="store_true", help="Export even if Pre-Flight QA finds hard errors")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: JSON file not found at {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    qa_report = validate_storyboard_data(data)
    slug = data.get("project_slug") or input_path.stem
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    checklist_path = out_dir / f"{slug}_项目铁律与质检清单.md"
    checklist_path.write_text(render_checklist_markdown(data, qa_report), encoding="utf-8")

    if not qa_report["passed"] and not args.skip_qa_fail:
        print(f"ERROR: Pre-Flight QA failed with {qa_report['error_count']} error(s). Fix JSON or pass --skip-qa-fail:", file=sys.stderr)
        for err in qa_report["errors"]:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(2)

    md_content = generate_markdown(data, qa_report)
    html_content = generate_html(data, qa_report)

    md_path = out_dir / f"{slug}_分镜执行单.md"
    html_path = out_dir / f"{slug}_导演故事板.html"

    md_path.write_text(md_content, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")

    if args.html_artifact:
        art_path = Path(args.html_artifact)
        art_path.parent.mkdir(parents=True, exist_ok=True)
        art_path.write_text(html_content, encoding="utf-8")

    print(
        f"SUCCESS:\n"
        f"- Pre-Flight QA : {'PASSED' if qa_report['passed'] else 'WARN'} ({qa_report['warning_count']} warnings)\n"
        f"- Checklist     : {checklist_path}\n"
        f"- Markdown      : {md_path}\n"
        f"- HTML          : {html_path}"
    )


if __name__ == "__main__":
    main()
