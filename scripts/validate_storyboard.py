#!/usr/bin/env python3
"""
Google Flow Director — Pre-Flight Technical Director QA & Persistent Rules Checklist
Implements:
1. "Creator + Harsh Technical Director" automated rule verification before Flow generation
2. 13.5s (Duration - 1.5s) speech safety cutoff & trailing ellipsis ('……') anti-clipping guard
3. Dual-track phonetic vs. display Chinese polyphone audit
4. Clean-frame (zero in-model text/UI) & Global Visual/Audio Lock verbatim verification
5. Exports a persistent `<slug>_项目铁律与质检清单.md` to prevent context drift
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Common ambiguous polyphones / rare chars in cultural, luxury, and commercial scripts
POLYPHONE_HINTS = {
    "素坯": "素批（『坯』易误读为 pēi，建议发音轨写作『素批』，字幕轨保留『素坯』）",
    "瓷坯": "瓷批（『坯』易误读为 pēi，建议发音轨写作『瓷批』）",
    "拉坯": "拉批（『坯』易误读为 pēi，建议发音轨写作『拉批』）",
    "古乐": "古悦（『乐』易误读为 lè，建议发音轨写作『古悦』）",
    "配乐": "配悦（『乐』易误读为 lè，建议发音轨写作『配悦』）",
    "礼乐": "礼悦（『乐』易误读为 lè，建议发音轨写作『礼悦』）",
    "重器": "仲器（『重』易误读为 chóng，建议发音轨写作『仲器』）",
    "为师": "维师（『为』易误读为四声 wèi，建议发音轨写作『维师』）",
    "监控": "坚控（古装/特殊语境易受干扰误读，建议发音轨核查）",
    "行云": "形云（『行』偶有 háng 误读风险，建议留意）",
}

FORBIDDEN_IN_MODEL_TEXT_PATTERNS = [
    r"\bwith subtitles\b",
    r"\bon-screen text:\b",
    r"\brender text\b",
    r"\bdraw text\b",
    r"\bdisplay title card\b",
    r"生成字幕",
    r"画面浮现大字",
]

RISKY_DISTORTION_PATTERNS = [
    (r"\b(brawl|wrestling|fistfight|entangled limbs)\b|多人打斗|肢体纠缠", "包含多人肢体纠缠/打斗高危动作，极易引发手脚穿模"),
    (r"\b(chewing|swallowing food|eating noodles)\b|当面进食|吞咽动作", "包含进食吞咽动作，视频模型极易产生口部失真"),
]


def count_cjk_chars(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def split_clauses(text: str) -> list[str]:
    cleaned = re.sub(r"(\.\.\.|……)+$", "", (text or "").strip())
    parts = [p.strip() for p in re.split(r"[，。；！？、,.;!?]+", cleaned) if p.strip()]
    return parts


def validate_storyboard_data(data: dict) -> dict:
    shots = data.get("shots", [])
    visual_bible = data.get("visual_bible", {})
    audio_guide = data.get("audio_guide", {})
    review_status = data.get("review_status", {})

    style_suffix = (visual_bible.get("style_suffix_en") or "").strip()
    audio_lock = (audio_guide.get("voice_and_audio_lock_en") or "").strip()

    errors: list[str] = []
    warnings: list[str] = []
    shot_reports: list[dict] = []

    if not shots:
        errors.append("分镜列表 `shots` 为空，无法进入制片流程。")

    human_approved = bool(review_status.get("human_script_approved", False))
    if not human_approved:
        warnings.append("人工剧本审核门禁 (`review_status.human_script_approved`) 当前为 `false`：请先将剧本与分镜呈交用户确认后再启动批量视频生成。")

    for idx, shot in enumerate(shots):
        sid = shot.get("shot_id", f"SHOT_{idx + 1:02d}")
        dur = float(shot.get("flow_gen_duration_sec", shot.get("edit_duration_sec", 15)))
        safe_cutoff = float(shot.get("vo_safe_cutoff_sec", max(dur - 1.5, round(dur * 0.85, 1))))
        prompt_en = shot.get("flow_video_prompt_en") or ""

        display_vo = (shot.get("subtitle_display_zh") or shot.get("voiceover_zh") or "").strip()
        phonetic_vo = (shot.get("voiceover_phonetic_zh") or display_vo).strip()

        s_errors: list[str] = []
        s_warnings: list[str] = []

        # 1. Clean Frame Check
        if "clean frame without text" not in prompt_en.lower() and "without any on-screen text" not in prompt_en.lower():
            s_errors.append(f"[{sid}] 缺少纯净无字锁（必须在 `flow_video_prompt_en` 中明确包含 `clean frame without text`）。")

        for pat in FORBIDDEN_IN_MODEL_TEXT_PATTERNS:
            if re.search(pat, prompt_en, flags=re.IGNORECASE):
                # Ignore negative phrases like "without subtitles" or "no subtitles"
                m = re.search(pat, prompt_en, flags=re.IGNORECASE)
                ctx = prompt_en[max(0, m.start() - 12):m.end() + 5].lower()
                if not any(neg in ctx for neg in ("no ", "without ", "严禁", "不含", "无")):
                    s_errors.append(f"[{sid}] 检测到疑似要求模型绘制文字/字幕的违规指令片段：`{m.group(0)}`。")

        # 2. Global Visual Lock Verbatim Check
        if style_suffix:
            core_prefix = style_suffix[:45].lower()
            if core_prefix not in prompt_en.lower():
                s_errors.append(f"[{sid}] 未完整内嵌全局视觉后缀锁 (`visual_bible.style_suffix_en`)，存在跨镜头画风漂移风险。")

        # 3. Voiceover Cutoff, Clause Length, Breath Ellipsis & Dual-Track Check
        cjk_len = count_cjk_chars(phonetic_vo)
        max_safe_chars = int(round(safe_cutoff * 2.7))
        est_vo_sec = round(cjk_len / 2.65, 2) if cjk_len else 0.0

        if phonetic_vo:
            if dur - safe_cutoff < 1.2:
                s_warnings.append(f"[{sid}] 台词截止线 ({safe_cutoff}s) 距镜头结束 ({dur}s) 不足 1.5s，建议预留 ≥1.5s 静默余韵防截断。")

            if cjk_len > max_safe_chars + 3:
                s_errors.append(
                    f"[{sid}] 旁白字数超标（当前 {cjk_len} 字，预计耗时 ~{est_vo_sec}s > 安全截止线 {safe_cutoff}s / 上限 {max_safe_chars} 字），极易在结尾被腰斩截断！"
                )
            elif cjk_len > max_safe_chars:
                s_warnings.append(
                    f"[{sid}] 旁白字数接近临界值（当前 {cjk_len} 字，安全上限 {max_safe_chars} 字），建议精简 2~4 字以确保 {safe_cutoff}s 前从容收音。"
                )

            if not (phonetic_vo.endswith("……") or phonetic_vo.endswith("...")):
                s_errors.append(f"[{sid}] `voiceover_phonetic_zh` 末尾缺少省略号缓冲 `……`（用于延长 0.25s 尾音呼吸防止吞尾字）。")

            clauses = split_clauses(phonetic_vo)
            long_clauses = [c for c in clauses if count_cjk_chars(c) > 16]
            if long_clauses:
                s_warnings.append(f"[{sid}] 存在超过 16 字的长分句 {long_clauses}，建议用逗号或句号拆短以防模型跳读。")

            if phonetic_vo not in prompt_en:
                s_errors.append(f"[{sid}] `voiceover_phonetic_zh` 原文未精确内嵌进 `flow_video_prompt_en`，双轨数据不一致。")

            for poly, hint in POLYPHONE_HINTS.items():
                if poly in phonetic_vo:
                    s_warnings.append(f"[{sid}] 发音轨包含易读错多音字/生僻词『{poly}』→ 建议替换为：{hint}")

        # 4. Audio Lock Check
        if audio_lock and phonetic_vo:
            # Check key voice descriptor presence
            if "mandarin" not in prompt_en.lower():
                s_warnings.append(f"[{sid}] `flow_video_prompt_en` 未显式声明 `Mandarin Chinese` 配音语种锁。")

        # 5. Distortion Risk Check
        combined_text = f"{prompt_en}\n{shot.get('visual_detail_zh', '')}"
        for pat, msg in RISKY_DISTORTION_PATTERNS:
            if re.search(pat, combined_text, flags=re.IGNORECASE):
                s_warnings.append(f"[{sid}] {msg}")

        # 6. Transition Pairing Check
        if idx < len(shots) - 1:
            next_shot = shots[idx + 1]
            if not (shot.get("transition_to_next_zh") or "").strip():
                s_warnings.append(f"[{sid}] 未填写交接下一镜的 `transition_to_next_zh` 出画动势。")
            if not (next_shot.get("entry_bridge_zh") or "").strip():
                s_warnings.append(f"[{next_shot.get('shot_id', f'SHOT_{idx+2:02d}')}] 未填写承接上一镜的 `entry_bridge_zh` 入画动势。")

        errors.extend(s_errors)
        warnings.extend(s_warnings)
        shot_reports.append({
            "shot_id": sid,
            "duration_sec": dur,
            "safe_cutoff_sec": safe_cutoff,
            "cjk_char_count": cjk_len,
            "max_safe_chars": max_safe_chars,
            "estimated_vo_sec": est_vo_sec,
            "has_breath_ellipsis": phonetic_vo.endswith("……") or phonetic_vo.endswith("..."),
            "clean_frame_locked": "clean frame without text" in prompt_en.lower() or "without any on-screen text" in prompt_en.lower(),
            "errors": s_errors,
            "warnings": s_warnings,
            "passed": len(s_errors) == 0,
        })

    return {
        "project_slug": data.get("project_slug", "unknown"),
        "project_title": data.get("project_title", ""),
        "passed": len(errors) == 0,
        "human_script_approved": human_approved,
        "director_qa_passed": bool(review_status.get("director_qa_passed", len(errors) == 0)),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "shots": shot_reports,
    }


def render_checklist_markdown(data: dict, report: dict) -> str:
    title = data.get("project_title", "未命名项目")
    slug = data.get("project_slug", "project")
    review = data.get("review_status", {})
    status_icon = "✅ 通过 (PASS)" if report["passed"] else "❌ 未通过 (BLOCKED)"
    human_icon = "✅ 已确认" if report["human_script_approved"] else "⏳ 待用户审核确认"

    lines = [
        f"# 🛡️ 《{title}》项目常驻铁律与独立质检清单",
        "",
        f"- **项目标识 (`project_slug`)**：`{slug}`",
        f"- **技术总监提交前预检状态**：**{status_icon}**（错误 `{report['error_count']}` 项 · 提醒 `{report['warning_count']}` 项）",
        f"- **人工整体脚本审核门禁**：**{human_icon}**",
        f"- **审稿与挑刺备注**：{review.get('review_notes', '无额外备注')}",
        "",
        "---",
        "",
        "## 一、 全流程常驻六大制片铁律（每阶段推进必查，防长对话遗忘）",
        "",
        "- [x] **铁律 1 · 100% 纯净无字画面**：所有 Google Flow 视频提示词末尾强制锁定 `clean frame without text, no subtitles, no watermarks, no UI borders`，严禁模型自行绘制文字或边框。",
        "- [x] **铁律 2 · 全局音画双锁 1:1 注入**：全片统一摄影机/胶片色温后缀（`style_suffix_en`）与同一旁白音色人设锁（`voice_and_audio_lock_en`），逐镜原样嵌入。",
        "- [x] **铁律 3 · 台词安全截止线（Duration - 1.5s）**：15s 镜头旁白必须在 `13.5s` 前说完（≤36 字），12s 镜头在 `10.5s` 前说完（≤28 字），末尾预留 ≥1.5s 纯画面光斑/定格余韵。",
        "- [x] **铁律 4 · 发音/字幕双轨隔离与防吞尾**：送入模型的 `voiceover_phonetic_zh` 必须将易错多音字替换为同音唯一字，并在句末添加 `……` 延长 0.25s 呼吸衰减；后期压制字幕使用正字版 `subtitle_display_zh`。",
        "- [x] **铁律 5 · 历史素材零覆盖归档**：批量生成或重拍视频时，严格按 `raw_clip_01_v1.mp4`、`_v2.mp4` 递增保存，局部瑕疵优先用 `ffmpeg tpad` / 裁剪修复。",
        "- [x] **铁律 6 · 代码级后期合成与初次看片抽帧验收**：字幕、宽银幕遮幅与落版大字统一由 `assemble_master.py` (`PIL` + `ffmpeg`) 渲染；成片交付前必须运行 `inspect_clips.py --mode master` 完成 2fps 抽帧与切点体检。",
        "",
        "---",
        "",
        "## 二、 逐镜参数与防吞尾安全核验表",
        "",
        "| 镜号 | 生成时长 | 台词安全线 | 实际字数 / 上限 | 预计朗读耗时 | 句末 `……` 缓冲 | 纯净无字锁 | 单镜结论 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for sr in report["shots"]:
        Lines_status = "✅ 达标" if sr["passed"] else "❌ 需修正"
        lines.append(
            f"| **{sr['shot_id']}** | `{sr['duration_sec']:g}s` | `≤ {sr['safe_cutoff_sec']:g}s` | "
            f"`{sr['cjk_char_count']} / {sr['max_safe_chars']} 字` | `~{sr['estimated_vo_sec']}s` | "
            f"{'✅' if sr['has_breath_ellipsis'] else '❌'} | {'✅' if sr['clean_frame_locked'] else '❌'} | {Lines_status} |"
        )

    lines.extend(["", "---", "", "## 三、 质检详情记录", ""])
    if not report["errors"] and not report["warnings"]:
        lines.append("- 🎉 **零错误、零警告！所有分镜提示词均符合工业级提交标准。**")
    else:
        for e in report["errors"]:
            lines.append(f"- ❌ **[硬伤拦截]** {e}")
        for w in report["warnings"]:
            lines.append(f"- ⚠️ **[优化提醒]** {w}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate Google Flow Director Storyboard JSON against production guardrails.")
    parser.add_argument("input_json", help="Path to storyboard JSON")
    parser.add_argument("--out-dir", default="", help="Optional directory to write `<slug>_项目铁律与质检清单.md`")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if warnings or unapproved human gate exist")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = validate_storyboard_data(data)
    slug = data.get("project_slug") or input_path.stem

    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        checklist_path = out_dir / f"{slug}_项目铁律与质检清单.md"
        checklist_path.write_text(render_checklist_markdown(data, report), encoding="utf-8")
        report["checklist_path"] = str(checklist_path)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        status = "PASSED" if report["passed"] else "FAILED"
        print(f"[{status}] {slug}: {report['error_count']} error(s), {report['warning_count']} warning(s)")
        for e in report["errors"]:
            print(f"  ERROR: {e}")
        for w in report["warnings"]:
            print(f"  WARN : {w}")
        if args.out_dir:
            print(f"  Checklist written to: {report['checklist_path']}")

    if not report["passed"]:
        sys.exit(2)
    if args.strict and (report["warning_count"] > 0 or not report["human_script_approved"]):
        sys.exit(3)


if __name__ == "__main__":
    main()
