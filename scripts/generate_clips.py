#!/usr/bin/env python3
"""
Google Flow Director — Multi-Mode Video Batch Acquisition & Versioned Archiver
Enforces:
1. Mandatory Human Script Approval Gate (`review_status.human_script_approved == true`)
2. Non-destructive versioned archiving (`raw_clip_01_v1.mp4`, `_v2.mp4`, never overwriting)
3. Multi-environment execution modes:
   - `veo-api`       : Direct cloud batch generation via Gemini / Veo API (`GEMINI_API_KEY`)
   - `drive-pull`    : Pulls raw Flow clips from Google Drive (`Google_Flow_Director_Hub/03_.../<slug>/`)
   - `local-import`  : Imports uploaded `.mp4` clips from `/home/antigravity/upload` or a local folder
   - `chrome-cdp`    : Connects to local desktop Chrome (`127.0.0.1:9222`) logged into Google Flow
   - `demo-synthetic`: Synthesizes timed 1080p test clips (with bokeh transition & safe audio cutoff)
                       via `ffmpeg` for end-to-end pipeline verification.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def next_versioned_path(clips_dir: Path, shot_index: int, ext: str = ".mp4") -> Path:
    """Return `raw_clip_01_v1.mp4`, incrementing `_v2`, `_v3` so existing takes are NEVER overwritten."""
    clips_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"raw_clip_{shot_index:02d}_v"
    existing_versions = []
    for p in clips_dir.glob(f"{prefix}*{ext}"):
        m = re.match(rf"^{re.escape(prefix)}(\d+){re.escape(ext)}$", p.name)
        if m:
            existing_versions.append(int(m.group(1)))
    next_v = (max(existing_versions) + 1) if existing_versions else 1
    return clips_dir / f"{prefix}{next_v}{ext}"


def latest_versioned_clips(clips_dir: Path, num_shots: int) -> list[Path | None]:
    """Find the highest `_vN` clip for each shot 1..num_shots."""
    result: list[Path | None] = []
    for idx in range(1, num_shots + 1):
        prefix = f"raw_clip_{idx:02d}_v"
        candidates = []
        if clips_dir.exists():
            for p in clips_dir.glob(f"{prefix}*.mp4"):
                m = re.match(rf"^{re.escape(prefix)}(\d+)\.mp4$", p.name)
                if m:
                    candidates.append((int(m.group(1)), p))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            result.append(candidates[-1][1])
        else:
            result.append(None)
    return result


def generate_via_veo_api(data: dict, clips_dir: Path, model: str, poll_sec: int = 10) -> list[dict]:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing GEMINI_API_KEY environment variable.\n"
            "To run pure cloud batch generation without a local browser:\n"
            "  export GEMINI_API_KEY='your-api-key'\n"
            "Or in a Remote VM without direct Veo API access, use `--mode drive-pull` or `--mode local-import`."
        )

    aspect_ratio = data.get("aspect_ratio", "16:9")
    shots = data.get("shots", [])
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    manifest = []

    for idx, shot in enumerate(shots, 1):
        sid = shot.get("shot_id", f"SHOT_{idx:02d}")
        prompt = shot.get("flow_video_prompt_en", "")
        duration = min(int(shot.get("flow_gen_duration_sec", 8)), 8)

        submit_url = f"{base_url}/models/{model}:predictLongRunning?key={api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "aspectRatio": aspect_ratio,
                "sampleCount": 1,
                "durationSeconds": duration,
            },
        }
        req = urllib.request.Request(
            submit_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        print(f"[Veo API] Submitting {sid} to {model}...")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                op_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Failed to reach Gemini/Veo API ({exc}). "
                f"If running inside a restricted cloud sandbox, ensure `generativelanguage.googleapis.com` "
                f"is in allowed_hosts, or use `--mode drive-pull` / `--mode local-import`."
            ) from exc

        op_name = op_data.get("name")
        if not op_name:
            raise RuntimeError(f"Unexpected Veo API response for {sid}: {op_data}")

        # Poll operation until done
        poll_url = f"{base_url}/{op_name}?key={api_key}"
        while True:
            time.sleep(poll_sec)
            with urllib.request.urlopen(poll_url, timeout=60) as resp:
                status_data = json.loads(resp.read().decode("utf-8"))
            if status_data.get("done"):
                break
            print(f"  ... waiting for {sid} ({op_name})")

        if "error" in status_data:
            raise RuntimeError(f"Veo generation error on {sid}: {status_data['error']}")

        # Extract video URI from response
        resp_body = status_data.get("response", {})
        samples = (
            resp_body.get("generateVideoResponse", {}).get("generatedSamples")
            or resp_body.get("videos")
            or []
        )
        if not samples:
            raise RuntimeError(f"No video sample returned for {sid}: {status_data}")

        video_uri = samples[0].get("video", {}).get("uri") or samples[0].get("uri")
        if not video_uri:
            raise RuntimeError(f"Missing video URI in sample for {sid}: {samples[0]}")

        dl_url = f"{video_uri}&key={api_key}" if "?" in video_uri else f"{video_uri}?key={api_key}"
        target_path = next_versioned_path(clips_dir, idx, ".mp4")
        urllib.request.urlretrieve(dl_url, str(target_path))
        print(f"  -> Archived: {target_path}")
        manifest.append({"shot_index": idx, "shot_id": sid, "path": str(target_path), "source": "veo-api"})

    return manifest


def import_from_local_dir(data: dict, clips_dir: Path, import_dir: Path) -> list[dict]:
    if not import_dir.exists():
        raise RuntimeError(f"Import directory does not exist: {import_dir}")

    mp4_files = sorted(p for p in import_dir.glob("*.mp4") if "final_master" not in p.name)
    shots = data.get("shots", [])
    if not mp4_files:
        raise RuntimeError(f"No .mp4 files found in {import_dir}.")

    manifest = []
    for idx, shot in enumerate(shots, 1):
        sid = shot.get("shot_id", f"SHOT_{idx:02d}")
        # Match explicit clip_01 / 01 pattern first, else fallback to sorted index
        matched = None
        for p in mp4_files:
            if re.search(rf"(?:clip|scene|shot)?[_\-\s]*0?{idx}(?!\d)", p.stem, re.IGNORECASE):
                matched = p
                break
        if matched is None and idx <= len(mp4_files):
            matched = mp4_files[idx - 1]
        if matched is None:
            print(f"  [WARN] No matching MP4 found for {sid} (index {idx})", file=sys.stderr)
            continue

        target_path = next_versioned_path(clips_dir, idx, ".mp4")
        shutil.copy2(matched, target_path)
        print(f"[Local Import] {matched.name} -> {target_path.name}")
        manifest.append({"shot_index": idx, "shot_id": sid, "path": str(target_path), "source": str(matched)})

    return manifest


def pull_from_google_drive(data: dict, clips_dir: Path, root_folder: str = "Google_Flow_Director_Hub") -> list[dict]:
    slug = data.get("project_slug", "project")
    # Import helper functions from sync_to_drive
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from sync_to_drive import run_gdrive, search_item  # noqa: E402

    roots = search_item(root_folder, is_folder=True)
    if not roots:
        raise RuntimeError(f"Google Drive root folder '{root_folder}' not found.")
    clips_hub = search_item("03_Google_Flow_生成视频片段_Clips", parent_id=roots[0]["id"], is_folder=True)
    if not clips_hub:
        raise RuntimeError("Clips hub '03_Google_Flow_生成视频片段_Clips' not found in Google Drive.")
    proj_folders = search_item(slug, parent_id=clips_hub[0]["id"], is_folder=True)
    target_folder_id = proj_folders[0]["id"] if proj_folders else clips_hub[0]["id"]

    listing_raw = run_gdrive(["readonly", "search", "--parent-id", target_folder_id, "--json"])
    items = json.loads(listing_raw) if listing_raw else []
    if isinstance(items, dict) and "files" in items:
        items = items["files"]

    mp4_items = sorted(
        [it for it in items if str(it.get("name", "")).lower().endswith(".mp4") and "final_master" not in str(it.get("name", ""))],
        key=lambda x: x.get("name", ""),
    )
    if not mp4_items:
        raise RuntimeError(
            f"No raw .mp4 clips found in Google Drive folder (ID: {target_folder_id}). "
            f"Upload your Flow clips to `{root_folder}/03_Google_Flow_生成视频片段_Clips/{slug}/` first."
        )

    tmp_dl = clips_dir / "_drive_staging"
    tmp_dl.mkdir(parents=True, exist_ok=True)
    for it in mp4_items:
        dest = tmp_dl / it["name"]
        run_gdrive(["readonly", "download", it["id"], "--output", str(dest)])

    manifest = import_from_local_dir(data, clips_dir, tmp_dl)
    shutil.rmtree(tmp_dl, ignore_errors=True)
    return manifest


def connect_chrome_cdp(data: dict, clips_dir: Path, cdp_url: str) -> list[dict]:
    version_endpoint = f"{cdp_url.rstrip('/')}/json/version"
    list_endpoint = f"{cdp_url.rstrip('/')}/json/list"
    try:
        with urllib.request.urlopen(version_endpoint, timeout=3) as resp:
            ver_info = json.loads(resp.read().decode("utf-8"))
        with urllib.request.urlopen(list_endpoint, timeout=3) as resp:
            tabs = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Cannot connect to Chrome DevTools Protocol at {cdp_url} ({exc}).\n"
            "Why this happens:\n"
            "  • In a Remote Cloud VM, `127.0.0.1:9222` points to the remote container rather than your local computer's Chrome.\n"
            "How to proceed:\n"
            "  1. [In Remote Cloud] Use `--mode veo-api` (with GEMINI_API_KEY), `--mode drive-pull`, or `--mode local-import`.\n"
            "  2. [On Local Desktop] Launch Chrome locally with:\n"
            "       google-chrome --remote-debugging-port=9222 --user-data-dir=$HOME/.flow-chrome-profile\n"
            "     Log into https://labs.google/fx/tools/flow and re-run `--mode chrome-cdp`."
        ) from exc

    flow_tabs = [t for t in tabs if "labs.google" in t.get("url", "") or "flow" in t.get("title", "").lower()]
    if not flow_tabs:
        raise RuntimeError(
            f"Connected to Chrome ({ver_info.get('Browser', 'Chrome')}), but no open Google Flow tab was found.\n"
            "Please open https://labs.google/fx/tools/flow in that Chrome window and log in first."
        )

    # Export a ready-to-execute CDP batch queue file for browser agent / Playwright runner
    queue_path = clips_dir / "cdp_submission_queue.json"
    clips_dir.mkdir(parents=True, exist_ok=True)
    queue = {
        "browser": ver_info.get("Browser"),
        "flow_tab_id": flow_tabs[0].get("id"),
        "flow_tab_url": flow_tabs[0].get("url"),
        "websocket_debugger_url": flow_tabs[0].get("webSocketDebuggerUrl"),
        "aspect_ratio": data.get("aspect_ratio", "16:9"),
        "tasks": [
            {
                "shot_index": idx,
                "shot_id": s.get("shot_id", f"SHOT_{idx:02d}"),
                "target_archive_path": str(next_versioned_path(clips_dir, idx, ".mp4")),
                "prompt": s.get("flow_video_prompt_en", ""),
            }
            for idx, s in enumerate(data.get("shots", []), 1)
        ],
    }
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Chrome CDP] Connected to Flow tab ({flow_tabs[0].get('url')}). Queue staged at: {queue_path}")
    return [{"shot_index": t["shot_index"], "shot_id": t["shot_id"], "queued_target": t["target_archive_path"]} for t in queue["tasks"]]


def generate_demo_synthetic(data: dict, clips_dir: Path) -> list[dict]:
    """Synthesize 1080p timed test clips with smooth golden bokeh transition & safe speech-window audio."""
    post_cfg = data.get("post_production", {})
    res = post_cfg.get("resolution", "1920x1080")
    w_str, h_str = res.lower().split("x")
    width, height = int(w_str), int(h_str)
    fps = int(post_cfg.get("fps", 24))
    shots = data.get("shots", [])
    manifest = []

    palettes = [
        ("0x1b263b", "0xd97706"),  # Deep cyan-slate to warm kiln amber
        ("0x0f292e", "0x38bdf8"),  # Misty Yaoli jade-teal to twilight blue hour
        ("0x1e1b4b", "0xc084fc"),
        ("0x1c1917", "0xfbbf24"),
    ]

    for idx, shot in enumerate(shots, 1):
        sid = shot.get("shot_id", f"SHOT_{idx:02d}")
        dur = float(shot.get("edit_duration_sec", shot.get("flow_gen_duration_sec", 15)))
        cutoff = float(shot.get("vo_safe_cutoff_sec", max(dur - 1.5, dur * 0.85)))
        bg_hex, glow_hex = palettes[(idx - 1) % len(palettes)]
        target_path = next_versioned_path(clips_dir, idx, ".mp4")

        # Build moving cinematic gradient + golden transition flare near tail (Clip 1) & head (Clip 2)
        # Audio simulates speech energy strictly within [0.5s, cutoff] and gentle ambient chord decay in final 1.5s!
        base_freq = 220 + (idx - 1) * 55
        sim_w, sim_h = 320, max(180, int(round(320 * height / max(width, 1))))
        vf_expr = (
            f"geq="
            f"r='clip(24 + 95*exp(-((X-(W*(0.3+0.4*T/{dur:.2f})))^2+(Y-H*0.5)^2)/(2*(W*0.28)^2)) "
            f"+ 165*gte(T,{dur - 1.4:.2f})*((T-{dur - 1.4:.2f})/1.4)"
            f"+ (155*lte(T,1.2)*((1.2-T)/1.2)*{1 if idx > 1 else 0}),0,255)':"
            f"g='clip(34 + 68*exp(-((X-(W*(0.3+0.4*T/{dur:.2f})))^2+(Y-H*0.5)^2)/(2*(W*0.28)^2)) "
            f"+ 130*gte(T,{dur - 1.4:.2f})*((T-{dur - 1.4:.2f})/1.4)"
            f"+ (125*lte(T,1.2)*((1.2-T)/1.2)*{1 if idx > 1 else 0}),0,255)':"
            f"b='clip(52 + 42*sin(2*PI*T/{dur:.2f}) "
            f"+ 45*gte(T,{dur - 1.4:.2f})*((T-{dur - 1.4:.2f})/1.4)"
            f"+ (45*lte(T,1.2)*((1.2-T)/1.2)*{1 if idx > 1 else 0}),0,255)',"
            f"scale={width}:{height}:flags=bicubic,format=yuv420p"
        )

        af_expr = (
            f"aevalsrc='"
            f"0.18*gte(t,0.5)*lte(t,{cutoff:.2f})*(0.6+0.4*sin(2*PI*3.2*t))*sin(2*PI*{base_freq}*t)"
            f"+ 0.04*sin(2*PI*{base_freq * 1.5}*t)*exp(-t/{dur * 0.9:.2f})"
            f"':s=48000:d={dur:.2f}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_hex}:s={sim_w}x{sim_h}:r={fps}:d={dur:.2f}",
            "-f", "lavfi", "-i", af_expr,
            "-vf", vf_expr,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(target_path),
        ]
        res_proc = subprocess.run(cmd, capture_output=True, text=True)
        if res_proc.returncode != 0:
            raise RuntimeError(f"ffmpeg synthetic generation failed:\n{res_proc.stderr}")

        print(f"[Demo Synthetic] Generated {sid} ({dur:g}s, VO cutoff {cutoff:g}s) -> {target_path.name}")
        manifest.append({"shot_index": idx, "shot_id": sid, "path": str(target_path), "source": "demo-synthetic"})

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Acquire & version-archive video clips for Google Flow Director.")
    parser.add_argument("input_json", help="Path to storyboard JSON file")
    parser.add_argument(
        "--mode",
        choices=["veo-api", "drive-pull", "local-import", "chrome-cdp", "demo-synthetic"],
        default="local-import",
        help="Acquisition mode",
    )
    parser.add_argument("--project-dir", default="/home/antigravity/flow_projects", help="Base project output directory")
    parser.add_argument("--import-dir", default="/home/antigravity/upload", help="Source directory for `--mode local-import`")
    parser.add_argument("--veo-model", default="veo-3.0-generate-preview", help="Model name for `--mode veo-api`")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222", help="Chrome remote debugging endpoint for `--mode chrome-cdp`")
    parser.add_argument("--force", action="store_true", help="Bypass human_script_approved gate check")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        print(f"Error: Storyboard JSON not found at {input_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    slug = data.get("project_slug") or input_path.stem
    human_approved = bool(data.get("review_status", {}).get("human_script_approved", False))

    if not human_approved and not args.force:
        print(
            f"BLOCKED [Human Review Gate]: `{slug}` has `review_status.human_script_approved = false`.\n"
            "Please present the overall script & storyboard to the user for approval first, then set "
            "`human_script_approved: true` (or pass `--force`).",
            file=sys.stderr,
        )
        sys.exit(3)

    clips_dir = Path(args.project_dir) / slug / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "veo-api":
        manifest = generate_via_veo_api(data, clips_dir, model=args.veo_model)
    elif args.mode == "drive-pull":
        manifest = pull_from_google_drive(data, clips_dir)
    elif args.mode == "local-import":
        manifest = import_from_local_dir(data, clips_dir, Path(args.import_dir))
    elif args.mode == "chrome-cdp":
        manifest = connect_chrome_cdp(data, clips_dir, args.cdp_url)
    else:
        manifest = generate_demo_synthetic(data, clips_dir)

    manifest_path = clips_dir / "clips_manifest.json"
    manifest_path.write_text(json.dumps({"project_slug": slug, "mode": args.mode, "clips": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    main()
