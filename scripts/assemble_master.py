#!/usr/bin/env python3
"""
Google Flow Director — Automated Commercial Post-Production & Mastering Engine
Uses Python (PIL) + ffmpeg to automatically assemble raw Google Flow clips into
a broadcast-ready commercial master (`<slug>_final_master.mp4`):
1. Selects latest versioned clip (`raw_clip_XX_vN.mp4`) per shot
2. Applies optional head/tail trim + `ffmpeg tpad` breathing frame clone
3. Joins multi-clip timelines via transition-matched `xfade` & `acrossfade`
4. Renders pixel-sharp 1080p/4K CinemaScope letterbox bars, timed bilingual subtitles
   (from `subtitle_cues` or auto-segmented `subtitle_display_zh`), and a smooth
   alpha-faded Hero End-Card title (`end_card`) via Python `PIL` — zero AI garbled text!
5. Applies optional spatial early-reflection reverb (`aecho`) & EBU R128 `loudnorm`.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_clips import latest_versioned_clips  # noqa: E402
from inspect_clips import probe_video  # noqa: E402

TRANSITION_TO_XFADE = {
    "LIGHT_BOKEH": "fade",
    "MATCH_SHAPE": "fade",
    "WHIP_WIPE": "smoothleft",
    "SPEED_RAMP_DIVE": "circleopen",
    "MOTION_RELAY": "smoothright",
    "SCENE_EXTEND": "fade",
}


def find_cjk_font(serif: bool = False, bold: bool = True, size: int = 36) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if serif:
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/System/Library/Fonts/Songti.ttc",
            "C:/Windows/Fonts/simsun.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/msyh.ttc",
        ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def auto_build_subtitle_cues(shot: dict, clip_dur: float) -> list[dict]:
    explicit = shot.get("subtitle_cues")
    if explicit and isinstance(explicit, list):
        return explicit

    raw_text = (shot.get("subtitle_display_zh") or shot.get("voiceover_zh") or "").strip()
    if not raw_text:
        return []

    clauses = [c.strip() for c in re.split(r"[；。！？!?]+", raw_text) if c.strip()]
    if not clauses:
        return []

    cutoff = float(shot.get("vo_safe_cutoff_sec", max(clip_dur - 1.5, clip_dur * 0.85)))
    usable_start = 0.5
    usable_end = min(cutoff, max(usable_start + 1.0, clip_dur - 0.8))
    total_chars = sum(max(len(c), 1) for c in clauses)
    span = usable_end - usable_start

    cues = []
    cursor = usable_start
    for c in clauses:
        seg_span = span * (max(len(c), 1) / total_chars)
        end_t = min(usable_end, cursor + max(seg_span - 0.15, 0.8))
        cues.append({"start": round(cursor, 2), "end": round(end_t, 2), "text_zh": c, "text_en": ""})
        cursor += seg_span
    return cues


def render_subtitle_strip_png(
    out_png: Path,
    width: int,
    strip_h: int,
    text_zh: str,
    text_en: str = "",
) -> None:
    """Render a crisp anti-aliased RGBA subtitle strip (`width x strip_h`)."""
    img = Image.new("RGBA", (width, strip_h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (width, strip_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)

    scale = width / 1920.0
    zh_font = find_cjk_font(serif=False, bold=True, size=max(18, int(36 * scale)))
    en_font = find_cjk_font(serif=False, bold=False, size=max(12, int(20 * scale)))

    zh_bbox = s_draw.textbbox((0, 0), text_zh, font=zh_font)
    zh_w = zh_bbox[2] - zh_bbox[0]
    zh_h = zh_bbox[3] - zh_bbox[1]

    en_w, en_h = 0, 0
    if text_en:
        en_bbox = s_draw.textbbox((0, 0), text_en, font=en_font)
        en_w = en_bbox[2] - en_bbox[0]
        en_h = en_bbox[3] - en_bbox[1]

    content_w = max(zh_w, en_w)
    pad_x = int(30 * scale)
    pad_y = int(14 * scale)
    gap_y = int(6 * scale) if text_en else 0
    box_w = content_w + pad_x * 2
    box_h = zh_h + en_h + gap_y + pad_y * 2

    bx0 = (width - box_w) // 2
    by0 = (strip_h - box_h) // 2
    bx1 = bx0 + box_w
    by1 = by0 + box_h

    # Soft translucent dark pill backdrop
    pill_layer = Image.new("RGBA", (width, strip_h), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pill_layer)
    p_draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(12 * scale), fill=(8, 13, 23, 158), outline=(251, 191, 36, 65), width=1)

    zh_x = (width - zh_w) // 2
    zh_y = by0 + pad_y - zh_bbox[1]

    # Soft text drop shadow
    s_draw.text((zh_x + 2, zh_y + 2), text_zh, font=zh_font, fill=(0, 0, 0, 210))
    if text_en:
        en_x = (width - en_w) // 2
        en_y = by0 + pad_y + zh_h + gap_y - en_bbox[1]
        s_draw.text((en_x + 1, en_y + 1), text_en, font=en_font, fill=(0, 0, 0, 190))

    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2.2))
    img = Image.alpha_composite(img, pill_layer)
    img = Image.alpha_composite(img, shadow)

    fg_draw = ImageDraw.Draw(img)
    fg_draw.text((zh_x, zh_y), text_zh, font=zh_font, fill=(248, 250, 252, 255))
    if text_en:
        en_x = (width - en_w) // 2
        en_y = by0 + pad_y + zh_h + gap_y - en_bbox[1]
        fg_draw.text((en_x, en_y), text_en, font=en_font, fill=(203, 213, 225, 235))

    img.save(out_png)


def render_scope_bars_png(out_png: Path, width: int, height: int, bar_ratio: float = 2.35) -> int:
    """Render CinemaScope matte bars and return single bar height in pixels."""
    active_h = int(round(width / bar_ratio))
    bar_h = max(0, (height - active_h) // 2)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if bar_h > 0:
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, width, bar_h], fill=(0, 0, 0, 255))
        draw.rectangle([0, height - bar_h, width, height], fill=(0, 0, 0, 255))
    img.save(out_png)
    return bar_h


def render_end_card_png(out_png: Path, width: int, height: int, end_card: dict) -> None:
    """Render centered luxury/cultural serif Hero End-Card overlay."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    scale = width / 1920.0

    # Subtle radial vignette dim so end-card reads clearly on any background
    vignette = Image.new("RGBA", (width, height), (6, 10, 18, 92))
    img = Image.alpha_composite(img, vignette)

    title_zh = end_card.get("title_zh", "")
    subtitle_zh = end_card.get("subtitle_zh", "")
    tagline_en = end_card.get("tagline_en", "")

    title_font = find_cjk_font(serif=True, bold=True, size=max(28, int(74 * scale)))
    sub_font = find_cjk_font(serif=True, bold=False, size=max(16, int(30 * scale)))
    tag_font = find_cjk_font(serif=False, bold=True, size=max(11, int(17 * scale)))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    fg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    f_draw = ImageDraw.Draw(fg)

    cy = height // 2 - int(22 * scale)
    if title_zh:
        tb = f_draw.textbbox((0, 0), title_zh, font=title_font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx = (width - tw) // 2
        ty = cy - th // 2 - tb[1]
        g_draw.text((tx, ty + 3), title_zh, font=title_font, fill=(0, 0, 0, 220))
        f_draw.text((tx, ty), title_zh, font=title_font, fill=(254, 249, 239, 255))

        # Golden hairline divider below main title
        line_y = cy + th // 2 + int(22 * scale)
        line_half = max(int(140 * scale), tw // 3)
        f_draw.line([(width // 2 - line_half, line_y), (width // 2 + line_half, line_y)], fill=(245, 190, 88, 215), width=max(1, int(2 * scale)))
        next_y = line_y + int(18 * scale)
    else:
        next_y = cy

    if subtitle_zh:
        sb = f_draw.textbbox((0, 0), subtitle_zh, font=sub_font)
        sw, sh = sb[2] - sb[0], sb[3] - sb[1]
        sx = (width - sw) // 2
        sy = next_y - sb[1]
        g_draw.text((sx, sy + 2), subtitle_zh, font=sub_font, fill=(0, 0, 0, 200))
        f_draw.text((sx, sy), subtitle_zh, font=sub_font, fill=(241, 245, 249, 245))
        next_y += sh + int(14 * scale)

    if tagline_en:
        eb = f_draw.textbbox((0, 0), tagline_en, font=tag_font)
        ew = eb[2] - eb[0]
        ex = (width - ew) // 2
        ey = next_y - eb[1]
        g_draw.text((ex, ey + 1), tagline_en, font=tag_font, fill=(0, 0, 0, 180))
        f_draw.text((ex, ey), tagline_en, font=tag_font, fill=(251, 191, 36, 220))

    glow = glow.filter(ImageFilter.GaussianBlur(radius=5.0))
    img = Image.alpha_composite(img, glow)
    img = Image.alpha_composite(img, fg)
    img.save(out_png)


def normalize_and_pad_segment(
    src_clip: Path,
    dst_clip: Path,
    width: int,
    height: int,
    fps: int,
    trim_head: float,
    trim_tail: float,
    pad_head: float,
    pad_tail: float,
) -> float:
    meta = probe_video(src_clip)
    raw_dur = meta["duration"]
    effective_body = max(0.5, raw_dur - trim_head - trim_tail)
    target_dur = round(effective_body + pad_head + pad_tail, 3)

    vf_parts = []
    if trim_head > 0 or trim_tail > 0:
        vf_parts.append(f"trim=start={trim_head:.3f}:end={raw_dur - trim_tail:.3f},setpts=PTS-STARTPTS")
    vf_parts.append(
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
    )
    if pad_head > 0 or pad_tail > 0:
        vf_parts.append(
            f"tpad=start_duration={pad_head:.3f}:start_mode=clone:stop_duration={pad_tail:.3f}:stop_mode=clone"
        )
    vf_chain = ",".join(vf_parts)

    if meta["has_audio"]:
        af_parts = []
        if trim_head > 0 or trim_tail > 0:
            af_parts.append(f"atrim=start={trim_head:.3f}:end={raw_dur - trim_tail:.3f},asetpts=PTS-STARTPTS")
        af_parts.append("aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo")
        if pad_head > 0:
            delay_ms = int(round(pad_head * 1000))
            af_parts.append(f"adelay={delay_ms}|{delay_ms}")
        af_parts.append(f"apad=whole_dur={target_dur:.3f}")
        af_chain = ",".join(af_parts)
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(src_clip),
            "-vf", vf_chain,
            "-af", af_chain,
            "-t", f"{target_dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "17",
            "-c:a", "aac", "-b:a", "192k",
            str(dst_clip),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(src_clip),
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={target_dur:.3f}",
            "-vf", vf_chain,
            "-t", f"{target_dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "17",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(dst_clip),
        ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed normalizing {src_clip}:\n{res.stderr}")
    return probe_video(dst_clip)["duration"]


def join_segments_with_xfade(
    seg_paths: list[Path],
    seg_durations: list[float],
    transitions: list[str],
    xfade_dur: float,
    joined_out: Path,
) -> tuple[float, list[float]]:
    if len(seg_paths) == 1 or xfade_dur <= 0.0:
        if len(seg_paths) == 1:
            shutil.copy2(seg_paths[0], joined_out)
            return seg_durations[0], [0.0]
        concat_txt = joined_out.parent / "concat_list.txt"
        concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in seg_paths), encoding="utf-8")
        res = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(joined_out)],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Concat failed:\n{res.stderr}")
        starts = []
        acc = 0.0
        for d in seg_durations:
            starts.append(round(acc, 3))
            acc += d
        return probe_video(joined_out)["duration"], starts

    # Chain N segments via xfade & acrossfade
    inputs = []
    for p in seg_paths:
        inputs.extend(["-i", str(p)])

    v_filters = []
    a_filters = []
    starts = [0.0]
    offset = seg_durations[0] - xfade_dur
    prev_v = "[0:v]"
    prev_a = "[0:a]"

    for i in range(1, len(seg_paths)):
        starts.append(round(offset, 3))
        xfade_name = TRANSITION_TO_XFADE.get(transitions[i - 1], "fade")
        out_v = f"[v{i}]"
        out_a = f"[a{i}]"
        v_filters.append(f"{prev_v}[{i}:v]xfade=transition={xfade_name}:duration={xfade_dur:.3f}:offset={offset:.3f}{out_v}")
        a_filters.append(f"{prev_a}[{i}:a]acrossfade=d={xfade_dur:.3f}:c1=tri:c2=tri{out_a}")
        prev_v = out_v
        prev_a = out_a
        if i < len(seg_paths) - 1:
            offset += seg_durations[i] - xfade_dur

    fc = ";".join(v_filters + a_filters)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        *inputs,
        "-filter_complex", fc,
        "-map", prev_v,
        "-map", prev_a,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17",
        "-c:a", "aac", "-b:a", "192k",
        str(joined_out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"xfade join failed:\n{res.stderr}")
    return probe_video(joined_out)["duration"], starts


def assemble_master(data: dict, project_root: Path, explicit_clips: list[Path] | None = None) -> Path:
    slug = data.get("project_slug", "project")
    shots = data.get("shots", [])
    post_cfg = data.get("post_production", {})
    end_card = data.get("end_card", {})

    res_str = post_cfg.get("resolution", "1920x1080")
    w_s, h_s = res_str.lower().split("x")
    width, height = int(w_s), int(h_s)
    fps = int(post_cfg.get("fps", 24))
    pad_head = float(post_cfg.get("pad_head_sec", 0.0))
    pad_tail = float(post_cfg.get("pad_tail_sec", 0.35))
    xfade_dur = float(post_cfg.get("crossfade_duration_sec", 0.5))
    use_scope = bool(post_cfg.get("cinemascope_bars", True))
    bar_ratio = float(post_cfg.get("bar_ratio", 2.35))
    use_reverb = bool(post_cfg.get("audio_reverb", False))
    use_loudnorm = bool(post_cfg.get("loudnorm", True))

    proj_folder = project_root / slug
    clips_dir = proj_folder / "clips"
    build_dir = proj_folder / "_build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    resolved_clips = explicit_clips if explicit_clips else latest_versioned_clips(clips_dir, len(shots))
    missing = [i + 1 for i, c in enumerate(resolved_clips) if c is None or not Path(c).exists()]
    if missing:
        raise RuntimeError(
            f"Missing raw clips for shot(s) {missing} in {clips_dir}. "
            f"Run `generate_clips.py` first."
        )

    # Step 1: Normalize & tpad each clip
    seg_paths = []
    seg_durations = []
    transitions = []
    for idx, (shot, src_clip) in enumerate(zip(shots, resolved_clips), 1):
        seg_out = build_dir / f"seg_{idx:02d}.mp4"
        t_head = float(shot.get("trim_head_sec", 0.0))
        t_tail = float(shot.get("trim_tail_sec", 0.0))
        seg_d = normalize_and_pad_segment(
            Path(src_clip), seg_out, width, height, fps, t_head, t_tail, pad_head, pad_tail
        )
        seg_paths.append(seg_out)
        seg_durations.append(seg_d)
        transitions.append(shot.get("transition_type", "LIGHT_BOKEH"))

    # Step 2: Join segments with xfade & acrossfade
    joined_path = build_dir / "joined_clean.mp4"
    total_dur, clip_starts = join_segments_with_xfade(seg_paths, seg_durations, transitions, xfade_dur, joined_path)

    # Step 3: Render PIL overlays (CinemaScope bars, Subtitles, End-Card)
    overlay_inputs = ["-i", str(joined_path)]
    filter_steps = []
    curr_v = "[0:v]"
    in_idx = 1

    bar_h = 0
    if use_scope and width > height:
        scope_png = build_dir / "scope_bars.png"
        bar_h = render_scope_bars_png(scope_png, width, height, bar_ratio=bar_ratio)
        if bar_h > 0:
            overlay_inputs.extend(["-i", str(scope_png)])
            next_v = f"[v_scope]"
            filter_steps.append(f"{curr_v}[{in_idx}:v]overlay=0:0{next_v}")
            curr_v = next_v
            in_idx += 1

    # Subtitle strips positioned cleanly above bottom CinemaScope bar (or lower 12% on vertical/16:9)
    strip_h = max(96, int(136 * (width / 1920.0)))
    strip_y = height - bar_h - strip_h - max(10, int(14 * (height / 1080.0)))

    global_cues = []
    for s_idx, shot in enumerate(shots):
        shot_start = clip_starts[s_idx]
        cues = auto_build_subtitle_cues(shot, seg_durations[s_idx])
        for c in cues:
            g_s = round(shot_start + pad_head + float(c.get("start", 0.0)), 3)
            g_e = round(shot_start + pad_head + float(c.get("end", 0.0)), 3)
            if g_e > g_s and g_s < total_dur:
                global_cues.append((g_s, min(g_e, total_dur - 0.2), c.get("text_zh", ""), c.get("text_en", "")))

    for c_i, (g_s, g_e, t_zh, t_en) in enumerate(global_cues, 1):
        cue_png = build_dir / f"sub_cue_{c_i:02d}.png"
        render_subtitle_strip_png(cue_png, width, strip_h, t_zh, t_en)
        overlay_inputs.extend(["-i", str(cue_png)])
        next_v = f"[v_sub_{c_i}]"
        filter_steps.append(
            f"{curr_v}[{in_idx}:v]overlay=0:{strip_y}:enable='between(t,{g_s:.3f},{g_e:.3f})'{next_v}"
        )
        curr_v = next_v
        in_idx += 1

    # Hero End-Card Overlay
    if end_card and end_card.get("enabled"):
        ec_png = build_dir / "end_card.png"
        render_end_card_png(ec_png, width, height, end_card)
        last_clip_start = clip_starts[-1]
        rel_ec_start = float(end_card.get("start_sec_in_last_clip", max(0.0, seg_durations[-1] - 3.2)))
        ec_global_start = max(0.0, min(total_dur - 1.2, last_clip_start + pad_head + rel_ec_start))
        ec_fade = float(end_card.get("fade_in_sec", 0.8))

        overlay_inputs.extend(["-loop", "1", "-t", f"{total_dur:.3f}", "-i", str(ec_png)])
        ec_faded = "[ec_faded]"
        next_v = "[v_ec]"
        filter_steps.append(
            f"[{in_idx}:v]format=rgba,fade=t=in:st={ec_global_start:.3f}:d={ec_fade:.3f}:alpha=1{ec_faded}"
        )
        filter_steps.append(
            f"{curr_v}{ec_faded}overlay=0:0:enable='gte(t,{ec_global_start:.3f})'{next_v}"
        )
        curr_v = next_v
        in_idx += 1

    # Subtle head/tail master video fade
    fade_out_st = max(0.0, total_dur - 0.55)
    filter_steps.append(f"{curr_v}fade=t=in:st=0:d=0.30,fade=t=out:st={fade_out_st:.3f}:d=0.55,format=yuv420p[v_master]")

    # Audio master chain: optional room early reflection reverb + fade + loudnorm
    a_chain = []
    if use_reverb:
        a_chain.append("aecho=0.85:0.82:22|48:0.12|0.06")
    a_chain.append(f"afade=t=in:st=0:d=0.25,afade=t=out:st={max(0.0, total_dur - 0.65):.3f}:d=0.65")
    if use_loudnorm:
        a_chain.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    filter_steps.append(f"[0:a]{','.join(a_chain)}[a_master]")

    master_path = proj_folder / f"{slug}_final_master.mp4"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        *overlay_inputs,
        "-filter_complex", ";".join(filter_steps),
        "-map", "[v_master]",
        "-map", "[a_master]",
        "-t", f"{total_dur:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart",
        str(master_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Master assembly failed:\n{res.stderr}")

    shutil.rmtree(build_dir, ignore_errors=True)
    return master_path


def main():
    parser = argparse.ArgumentParser(description="Assemble commercial master MP4 with PIL subtitles, CinemaScope & Hero End-Card.")
    parser.add_argument("input_json", help="Path to storyboard JSON")
    parser.add_argument("--project-dir", default="/home/antigravity/flow_projects", help="Base project directory")
    parser.add_argument("--clips", nargs="*", default=None, help="Optional explicit list of clip paths in shot order")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: Storyboard JSON not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    explicit = [Path(p) for p in args.clips] if args.clips else None
    master_out = assemble_master(data, Path(args.project_dir), explicit_clips=explicit)
    meta = probe_video(master_out)
    print(
        f"MASTER READY:\n"
        f"- File      : {master_out}\n"
        f"- Resolution: {meta['width']}x{meta['height']} @ {meta['fps']}fps\n"
        f"- Duration  : {meta['duration']}s"
    )


if __name__ == "__main__":
    main()
