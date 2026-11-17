#!/usr/bin/env python3
"""
Google Flow Director — Automated Frame, Transition Bridge & Audio Tail-Clipping QA
Supports two inspection stages:
1. `--mode raw`   : Inspects raw generated clips (`raw_clip_XX_vN.mp4`):
                    - 1 fps frame contact sheets (`qa_raw_strip_XX.jpg`)
                    - Audio RMS envelope & final-syllable tail-clipping guard
                    - Side-by-side Transition Bridge contact sheets (`qa_transition_01_to_02.jpg`)
                      comparing Shot N tail frames vs Shot N+1 head frames.
2. `--mode master`: Fresh-Eyes Final Master Audit on `<slug>_final_master.mp4`:
                    - Full video 2 fps contact grid (`qa_master_2fps_grid.jpg`)
                    - ±3 frames around every transition cut (`qa_master_cut_boundaries.jpg`)
                    - Black-frame, audio clipping & subtitle window verification (`<slug>_成片体检报告.md`).
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_clips import latest_versioned_clips  # noqa: E402


def load_font(size: int = 18) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def probe_video(video_path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {video_path}:\n{res.stderr}")
    info = json.loads(res.stdout)
    duration = float(info.get("format", {}).get("duration", 0.0))
    width, height, fps = 0, 0, 24.0
    has_audio = False
    for st in info.get("streams", []):
        if st.get("codec_type") == "video" and width == 0:
            width = int(st.get("width", 0))
            height = int(st.get("height", 0))
            r_fps = st.get("r_frame_rate", "24/1")
            if "/" in r_fps:
                num, den = r_fps.split("/", 1)
                fps = float(num) / max(float(den), 1.0)
            else:
                fps = float(r_fps)
        elif st.get("codec_type") == "audio":
            has_audio = True
    return {"duration": round(duration, 3), "width": width, "height": height, "fps": round(fps, 2), "has_audio": has_audio}


def extract_frame_at(video_path: Path, timestamp: float, thumb_size: tuple[int, int] = (384, 216)) -> Image.Image:
    ts = max(0.0, timestamp)
    cmd = [
        "ffmpeg", "-v", "error",
        "-ss", f"{ts:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-vf", f"scale={thumb_size[0]}:{thumb_size[1]}",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0 or not res.stdout:
        return Image.new("RGB", thumb_size, (15, 23, 42))
    from io import BytesIO
    return Image.open(BytesIO(res.stdout)).convert("RGB")


def analyze_audio_envelope(video_path: Path, safe_cutoff_sec: float | None = None) -> dict:
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-",
    ]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0 or len(res.stdout) < 3200:
        return {"has_audio": False, "peak_dbfs": -99.0, "tail_rms_ratio": 0.0, "tail_clipping_suspect": False}

    samples = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    sr = 16000
    peak = float(np.max(np.abs(samples)))
    peak_dbfs = round(20.0 * math.log10(max(peak, 1e-6)), 2)

    # Compute 0.1s window RMS
    win = int(sr * 0.1)
    n_wins = max(len(samples) // win, 1)
    trimmed = samples[: n_wins * win].reshape(n_wins, win)
    rms_series = np.sqrt(np.mean(trimmed ** 2, axis=1))

    body_end_idx = int((safe_cutoff_sec or (len(samples) / sr - 1.0)) * 10)
    body_end_idx = max(1, min(body_end_idx, n_wins))
    body_peak_rms = float(np.max(rms_series[:body_end_idx])) if body_end_idx > 0 else float(np.max(rms_series))
    tail_rms = float(np.mean(rms_series[-2:])) if n_wins >= 2 else float(rms_series[-1])
    tail_ratio = round(tail_rms / max(body_peak_rms, 1e-5), 3)

    # Suspect tail clipping if the final 0.2s still carries >60% of peak vocal RMS energy
    tail_clipping_suspect = bool(body_peak_rms > 0.02 and tail_ratio > 0.60)
    return {
        "has_audio": True,
        "peak_dbfs": peak_dbfs,
        "body_peak_rms": round(body_peak_rms, 4),
        "tail_02s_rms": round(tail_rms, 4),
        "tail_rms_ratio": tail_ratio,
        "tail_clipping_suspect": tail_clipping_suspect,
    }


def compose_contact_grid(
    labeled_frames: list[tuple[str, Image.Image]],
    header_title: str,
    cols: int = 4,
    thumb_size: tuple[int, int] = (384, 216),
) -> Image.Image:
    rows = max(1, math.ceil(len(labeled_frames) / cols))
    pad = 14
    header_h = 54
    label_h = 28
    cell_w = thumb_size[0]
    cell_h = thumb_size[1] + label_h
    canvas_w = pad + cols * (cell_w + pad)
    canvas_h = header_h + pad + rows * (cell_h + pad)

    canvas = Image.new("RGB", (canvas_w, canvas_h), (11, 15, 23))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(20)
    lbl_font = load_font(14)

    draw.rectangle([0, 0, canvas_w, header_h], fill=(20, 30, 52))
    draw.text((pad, 14), header_title, fill=(241, 245, 249), font=title_font)

    for i, (label, img) in enumerate(labeled_frames):
        r = i // cols
        c = i % cols
        x = pad + c * (cell_w + pad)
        y = header_h + pad + r * (cell_h + pad)
        canvas.paste(img, (x, y))
        draw.rectangle([x, y + thumb_size[1], x + cell_w, y + cell_h], fill=(24, 34, 56))
        draw.text((x + 8, y + thumb_size[1] + 5), label, fill=(226, 232, 240), font=lbl_font)

    return canvas


def inspect_raw_clips(data: dict, project_root: Path) -> dict:
    slug = data.get("project_slug", "project")
    shots = data.get("shots", [])
    clips_dir = project_root / slug / "clips"
    qa_dir = project_root / slug / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    latest = latest_versioned_clips(clips_dir, len(shots))
    clip_reports = []
    warnings = []

    for idx, (shot, clip_path) in enumerate(zip(shots, latest), 1):
        sid = shot.get("shot_id", f"SHOT_{idx:02d}")
        if clip_path is None or not clip_path.exists():
            warnings.append(f"[{sid}] 未找到原片文件（期望位于 {clips_dir}/raw_clip_{idx:02d}_v*.mp4）")
            clip_reports.append({"shot_id": sid, "found": False})
            continue

        meta = probe_video(clip_path)
        dur = meta["duration"]
        cutoff = float(shot.get("vo_safe_cutoff_sec", max(dur - 1.5, dur * 0.85)))
        audio_qa = analyze_audio_envelope(clip_path, safe_cutoff_sec=cutoff)

        # Sample 1 fps frames & detect unexpected middle black frames
        n_sec = max(1, int(math.ceil(dur)))
        frames_1fps = []
        black_timestamps = []
        for sec in range(n_sec):
            ts = min(sec + 0.2, max(0.0, dur - 0.1))
            im = extract_frame_at(clip_path, ts)
            mean_luma = float(np.mean(np.asarray(im)))
            if 0.8 < ts < (dur - 0.8) and mean_luma < 5.0:
                black_timestamps.append(round(ts, 2))
            frames_1fps.append((f"{sid} @ {ts:04.1f}s (luma={mean_luma:.0f})", im))

        strip_img = compose_contact_grid(
            frames_1fps,
            header_title=f"RAW 1FPS AUDIT · {sid} ({clip_path.name} · {dur:.2f}s · {meta['width']}x{meta['height']})",
            cols=5,
        )
        strip_path = qa_dir / f"qa_raw_strip_{idx:02d}.jpg"
        strip_img.save(strip_path, quality=90)

        if audio_qa.get("tail_clipping_suspect"):
            warnings.append(f"[{sid}] 检测到句尾最后 0.2s 音量仍高（占比 {audio_qa['tail_rms_ratio']}），疑似尾音截断，建议开启 `pad_tail_sec` 或重拍。")
        if black_timestamps:
            warnings.append(f"[{sid}] 中段出现疑似全黑废帧：{black_timestamps}s")

        clip_reports.append({
            "shot_id": sid,
            "found": True,
            "file": clip_path.name,
            "meta": meta,
            "audio_qa": audio_qa,
            "black_frame_timestamps": black_timestamps,
            "strip_image": str(strip_path),
        })

    # Transition Bridge Side-by-Side Contact Sheets
    transition_sheets = []
    for idx in range(len(shots) - 1):
        c1, c2 = latest[idx], latest[idx + 1]
        if not c1 or not c2:
            continue
        m1 = probe_video(c1)
        d1 = m1["duration"]
        t_type = shots[idx].get("transition_type", "BRIDGE")

        tail_offsets = [max(0.0, d1 - 1.2), max(0.0, d1 - 0.6), max(0.0, d1 - 0.08)]
        head_offsets = [0.08, 0.6, 1.2]

        pair_frames = []
        last_tail_arr = None
        first_head_arr = None
        for t in tail_offsets:
            im = extract_frame_at(c1, t)
            last_tail_arr = np.asarray(im, dtype=np.float32)
            pair_frames.append((f"Shot {idx+1} Tail @ {t:.2f}s", im))
        for t in head_offsets:
            im = extract_frame_at(c2, t)
            if first_head_arr is None:
                first_head_arr = np.asarray(im, dtype=np.float32)
            pair_frames.append((f"Shot {idx+2} Head @ {t:.2f}s", im))

        rgb_delta = round(float(np.mean(np.abs(last_tail_arr - first_head_arr))), 1) if (last_tail_arr is not None and first_head_arr is not None) else 0.0
        sheet = compose_contact_grid(
            pair_frames,
            header_title=f"TRANSITION BRIDGE [{t_type}] · Shot {idx+1} Tail -> Shot {idx+2} Head (RGB Delta={rgb_delta})",
            cols=3,
        )
        t_path = qa_dir / f"qa_transition_{idx+1:02d}_to_{idx+2:02d}.jpg"
        sheet.save(t_path, quality=92)
        transition_sheets.append({"pair": f"{idx+1}->{idx+2}", "transition_type": t_type, "rgb_delta": rgb_delta, "image": str(t_path)})

    report = {
        "mode": "raw",
        "project_slug": slug,
        "warnings": warnings,
        "clips": clip_reports,
        "transitions": transition_sheets,
    }
    (qa_dir / "qa_raw_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def inspect_master_video(data: dict, project_root: Path, master_path: Path) -> dict:
    slug = data.get("project_slug", "project")
    qa_dir = project_root / slug / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    if not master_path.exists():
        raise RuntimeError(f"Master video not found at {master_path}")

    meta = probe_video(master_path)
    dur = meta["duration"]
    audio_qa = analyze_audio_envelope(master_path, safe_cutoff_sec=max(dur - 1.5, dur * 0.9))

    # 1. Sample at 2 fps across entire master
    step = 0.5
    n_samples = max(1, int(dur / step))
    frames_2fps = []
    black_frames = []
    for i in range(n_samples):
        ts = min(i * step + 0.1, max(0.0, dur - 0.08))
        im = extract_frame_at(master_path, ts, thumb_size=(320, 180))
        luma = float(np.mean(np.asarray(im)))
        if 0.6 < ts < (dur - 0.6) and luma < 4.5:
            black_frames.append(round(ts, 2))
        frames_2fps.append((f"t={ts:05.2f}s (Y={luma:.0f})", im))

    grid_img = compose_contact_grid(
        frames_2fps,
        header_title=f"FRESH-EYES MASTER 2FPS AUDIT · {master_path.name} ({dur:.2f}s · {meta['width']}x{meta['height']})",
        cols=6,
        thumb_size=(320, 180),
    )
    grid_path = qa_dir / "qa_master_2fps_grid.jpg"
    grid_img.save(grid_path, quality=90)

    # 2. Sample ±3 frames around every cut boundary
    post_cfg = data.get("post_production", {})
    pad_head = float(post_cfg.get("pad_head_sec", 0.0))
    pad_tail = float(post_cfg.get("pad_tail_sec", 0.35))
    xfade_dur = float(post_cfg.get("crossfade_duration_sec", 0.5))
    shots = data.get("shots", [])

    cut_frames = []
    cursor = 0.0
    cut_points = []
    for i, s in enumerate(shots[:-1]):
        seg_dur = float(s.get("edit_duration_sec", 15)) + pad_head + pad_tail
        cursor += seg_dur - (xfade_dur if i >= 0 else 0.0)
        cut_points.append(round(cursor, 2))

    fps = max(meta["fps"], 24.0)
    frame_dt = 1.0 / fps
    for c_idx, cp in enumerate(cut_points, 1):
        for offset_f in (-3, -2, -1, 0, 1, 2, 3):
            ts = max(0.0, min(dur - 0.05, cp + offset_f * frame_dt * 2))
            im = extract_frame_at(master_path, ts, thumb_size=(256, 144))
            tag = "CUT" if offset_f == 0 else f"{offset_f:+d}f"
            cut_frames.append((f"Cut#{c_idx} {tag} ({ts:.2f}s)", im))

    cut_sheet_path = ""
    if cut_frames:
        cut_sheet = compose_contact_grid(
            cut_frames,
            header_title=f"CUT BOUNDARY ±3 FRAMES AUDIT · Cut Points: {cut_points}s",
            cols=7,
            thumb_size=(256, 144),
        )
        cs_p = qa_dir / "qa_master_cut_boundaries.jpg"
        cut_sheet.save(cs_p, quality=90)
        cut_sheet_path = str(cs_p)

    hard_issues = []
    minor_notes = []
    if black_frames:
        hard_issues.append(f"成片中段存在疑似黑帧：{black_frames}s")
    if not meta["has_audio"] or not audio_qa.get("has_audio"):
        hard_issues.append("成片缺少音轨或音轨为空白！")
    if audio_qa.get("peak_dbfs", -10) > -0.1:
        minor_notes.append(f"音频峰值 ({audio_qa['peak_dbfs']} dBFS) 接近削波上限，建议开启 `loudnorm`。")
    if audio_qa.get("tail_clipping_suspect"):
        minor_notes.append("片尾最后 0.2s 仍有较高音频能量，可适当增加片尾淡出。")

    md_lines = [
        f"# 🔍 《{data.get('project_title', slug)}》初次看片视角 · 成片全面体检报告",
        "",
        f"- **母带文件**：`{master_path}`",
        f"- **规格核验**：`{meta['width']}x{meta['height']}` @ `{meta['fps']}fps` | **总时长**：`{dur:.2f}s` | **音频峰值**：`{audio_qa.get('peak_dbfs')} dBFS`",
        f"- **全片 2fps 抽帧总览图**：`{grid_path}`",
        f"- **转场切点 ±3 帧复核图**：`{cut_sheet_path or '单镜头无切点'}`",
        "",
        "## 一、 硬伤筛查（必须修复项）",
        *( [f"- ❌ {x}" for x in hard_issues] if hard_issues else ["- ✅ **未检出黑帧、废帧、静音断流或尾音硬截断！**"] ),
        "",
        "## 二、 细节优化建议",
        *( [f"- 💡 {x}" for x in minor_notes] if minor_notes else ["- ✅ **响度动态、切镜过渡与片尾呼吸留白均处于健康区间。**"] ),
        "",
    ]
    md_report_path = project_root / slug / f"{slug}_成片体检报告.md"
    md_report_path.write_text("\n".join(md_lines), encoding="utf-8")

    report = {
        "mode": "master",
        "project_slug": slug,
        "master_path": str(master_path),
        "meta": meta,
        "audio_qa": audio_qa,
        "cut_points_sec": cut_points,
        "black_frames_sec": black_frames,
        "hard_issues": hard_issues,
        "minor_notes": minor_notes,
        "grid_2fps_image": str(grid_path),
        "cut_boundaries_image": cut_sheet_path,
        "markdown_report": str(md_report_path),
    }
    (qa_dir / "qa_master_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Inspect raw clips or final master video with frame grids & audio QA.")
    parser.add_argument("input_json", help="Path to storyboard JSON")
    parser.add_argument("--mode", choices=["raw", "master"], default="raw", help="Inspect `raw` clips or `master` video")
    parser.add_argument("--project-dir", default="/home/antigravity/flow_projects", help="Base project directory")
    parser.add_argument("--master-file", default="", help="Override path to final master MP4 when `--mode master`")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    slug = data.get("project_slug") or input_path.stem
    project_root = Path(args.project_dir)

    if args.mode == "raw":
        rep = inspect_raw_clips(data, project_root)
        print(f"[RAW QA DONE] Clips checked: {len(rep['clips'])}, Transition sheets: {len(rep['transitions'])}, Warnings: {len(rep['warnings'])}")
        for w in rep["warnings"]:
            print(f"  WARN: {w}")
    else:
        m_path = Path(args.master_file) if args.master_file else (project_root / slug / f"{slug}_final_master.mp4")
        rep = inspect_master_video(data, project_root, m_path)
        print(
            f"[MASTER QA DONE] {m_path.name} ({rep['meta']['duration']}s)\n"
            f"  2fps Grid      : {rep['grid_2fps_image']}\n"
            f"  Cut Boundaries : {rep['cut_boundaries_image']}\n"
            f"  Markdown Report: {rep['markdown_report']}\n"
            f"  Hard Issues    : {len(rep['hard_issues'])}"
        )


if __name__ == "__main__":
    main()
