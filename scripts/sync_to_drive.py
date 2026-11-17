#!/usr/bin/env python3
"""
Google Flow Director — Google Drive Full-Lifecycle Cloud Archive & Sync Script
Automatically organizes and syncs end-to-end production assets to Google Drive:
  Google_Flow_Director_Hub/
  ├── 01_项目分镜与故事板_Projects/<slug>/
  │   ├── <slug>.json
  │   ├── <slug>_分镜执行单.md
  │   ├── <slug>_导演故事板.html
  │   ├── <slug>_项目铁律与质检清单.md
  │   ├── <slug>_成片体检报告.md
  │   └── qa_*.jpg / qa_*.json
  ├── 02_产品与首尾帧垫图资产_Ingredients/<slug>/
  │   └── (reference & start/end frame images)
  └── 03_Google_Flow_生成视频片段_Clips/<slug>/
      ├── raw_clip_01_v1.mp4 ...
      └── <slug>_final_master.mp4
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run_gdrive(args_list: list[str]) -> str:
    cmd = ["gdrive"] + args_list
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed:\n{res.stderr or res.stdout}")
    return res.stdout.strip()


def search_item(name: str, parent_id: str | None = None, is_folder: bool = False) -> list[dict]:
    search_cmd = ["readonly", "search", "--name-exact", name, "--json"]
    if is_folder:
        search_cmd.extend(["--type", "folder"])
    if parent_id:
        search_cmd.extend(["--parent-id", parent_id])
    out = run_gdrive(search_cmd)
    try:
        items = json.loads(out) if out else []
    except json.JSONDecodeError:
        items = []
    if isinstance(items, dict) and "files" in items:
        items = items["files"]
    return items if isinstance(items, list) else []


def extract_id_from_text(text: str) -> str:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data.get("id") or data.get("file", {}).get("id", "")
    except Exception:
        pass
    m = re.search(r"([a-zA-Z0-9_-]{25,45})", text)
    return m.group(1) if m else ""


def find_or_create_folder(name: str, parent_id: str | None = None) -> str:
    items = search_item(name, parent_id=parent_id, is_folder=True)
    if items:
        return items[0]["id"]

    mkdir_cmd = ["mutate", "mkdir", name]
    if parent_id:
        mkdir_cmd.extend(["--parent", parent_id])
    created_out = run_gdrive(mkdir_cmd)

    items = search_item(name, parent_id=parent_id, is_folder=True)
    if items:
        return items[0]["id"]
    return extract_id_from_text(created_out)


def upload_or_update_file(local_path: Path, parent_id: str) -> dict:
    items = search_item(local_path.name, parent_id=parent_id, is_folder=False)
    if items:
        file_id = items[0]["id"]
        run_gdrive(["mutate", "update", file_id, str(local_path)])
    else:
        run_gdrive(["mutate", "upload", str(local_path), "--parent", parent_id])
    items = search_item(local_path.name, parent_id=parent_id, is_folder=False)
    if items:
        return items[0]
    return {"id": "", "name": local_path.name}


def record_upload(summary: dict, local_path: Path, slug: str, bucket: str, folder_id: str, res: dict) -> None:
    fid = res.get("id", "")
    summary["uploaded_files"].append({
        "name": local_path.name,
        "project": slug,
        "bucket": bucket,
        "folder_url": f"https://drive.google.com/drive/folders/{folder_id}",
        "id": fid,
        "url": res.get("webViewLink") or (f"https://drive.google.com/file/d/{fid}/view" if fid else ""),
    })


def main():
    parser = argparse.ArgumentParser(description="Sync Google Flow Director end-to-end projects & masters to Google Drive.")
    parser.add_argument("--project-dir", default="/home/antigravity/flow_projects", help="Local directory of generated projects")
    parser.add_argument("--slug", default="", help="Optional single project_slug to sync (default: all *.json in project-dir)")
    parser.add_argument("--root-folder", default="Google_Flow_Director_Hub", help="Root folder name in Google Drive")
    parser.add_argument("--skip-raw-clips", action="store_true", help="Upload final_master.mp4 without uploading raw_clip_* takes")
    args = parser.parse_args()

    proj_dir = Path(args.project_dir)
    if not proj_dir.exists():
        print(f"Directory {proj_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    root_id = find_or_create_folder(args.root_folder)
    projects_folder_id = find_or_create_folder("01_项目分镜与故事板_Projects", root_id)
    assets_folder_id = find_or_create_folder("02_产品与首尾帧垫图资产_Ingredients", root_id)
    clips_folder_id = find_or_create_folder("03_Google_Flow_生成视频片段_Clips", root_id)

    summary = {
        "root_folder_id": root_id,
        "root_folder_url": f"https://drive.google.com/drive/folders/{root_id}",
        "projects_folder_id": projects_folder_id,
        "projects_folder_url": f"https://drive.google.com/drive/folders/{projects_folder_id}",
        "assets_folder_id": assets_folder_id,
        "clips_folder_id": clips_folder_id,
        "uploaded_files": [],
    }

    json_candidates = [proj_dir / f"{args.slug}.json"] if args.slug else sorted(proj_dir.glob("*.json"))
    for json_file in json_candidates:
        if not json_file.exists():
            continue
        slug = json_file.stem

        # 1. Storyboards, Checklists & QA Reports -> 01_项目分镜与故事板_Projects/<slug>/
        doc_sub_id = find_or_create_folder(slug, projects_folder_id)
        for related in sorted(proj_dir.glob(f"{slug}*")):
            if related.is_file() and related.suffix.lower() in (".json", ".md", ".html"):
                res = upload_or_update_file(related, doc_sub_id)
                record_upload(summary, related, slug, "01_Projects", doc_sub_id, res)

        sub_workspace = proj_dir / slug
        if sub_workspace.is_dir():
            for doc_extra in sorted(sub_workspace.glob("*.md")):
                res = upload_or_update_file(doc_extra, doc_sub_id)
                record_upload(summary, doc_extra, slug, "01_Projects", doc_sub_id, res)

            qa_dir = sub_workspace / "qa"
            if qa_dir.is_dir():
                for qa_file in sorted(qa_dir.iterdir()):
                    if qa_file.is_file() and qa_file.suffix.lower() in (".jpg", ".png", ".json", ".md"):
                        res = upload_or_update_file(qa_file, doc_sub_id)
                        record_upload(summary, qa_file, slug, "01_Projects_QA", doc_sub_id, res)

            # 2. Ingredients / Reference Images -> 02_产品与首尾帧垫图资产_Ingredients/<slug>/
            ing_dir = sub_workspace / "ingredients"
            if ing_dir.is_dir():
                ing_files = [p for p in sorted(ing_dir.iterdir()) if p.is_file()]
                if ing_files:
                    ing_sub_id = find_or_create_folder(slug, assets_folder_id)
                    for img_f in ing_files:
                        res = upload_or_update_file(img_f, ing_sub_id)
                        record_upload(summary, img_f, slug, "02_Ingredients", ing_sub_id, res)

            # 3. Raw Clips & Final Master MP4 -> 03_Google_Flow_生成视频片段_Clips/<slug>/
            video_targets: list[Path] = []
            master_mp4 = sub_workspace / f"{slug}_final_master.mp4"
            if master_mp4.exists():
                video_targets.append(master_mp4)
            if not args.skip_raw_clips and (sub_workspace / "clips").is_dir():
                video_targets.extend(sorted((sub_workspace / "clips").glob("raw_clip_*.mp4")))

            if video_targets:
                vid_sub_id = find_or_create_folder(slug, clips_folder_id)
                for vf in video_targets:
                    res = upload_or_update_file(vf, vid_sub_id)
                    record_upload(summary, vf, slug, "03_Clips_and_Master", vid_sub_id, res)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
