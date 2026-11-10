#!/usr/bin/env python3
"""
Google Flow Director — Google Drive Cloud Archive & Sync Script
Automatically organizes and uploads generated storyboard projects (.md, .html, .json,
and optional reference images / Flow video clips) to a structured folder hierarchy
in Google Drive:
  Google_Flow_Director_Hub/
  ├── 01_项目分镜与故事板 (Projects)/
  │   └── <project_slug>/
  │       ├── <slug>_分镜执行单.md
  │       ├── <slug>_导演故事板.html
  │       └── <slug>.json
  ├── 02_产品与视觉锚点资产 (Ingredients_Assets)/
  └── 03_Google_Flow_成片素材 (Generated_Clips)/
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_gdrive(args_list: list[str]) -> str:
    cmd = ["gdrive"] + args_list
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed:\n{res.stderr or res.stdout}")
    return res.stdout.strip()


def find_or_create_folder(name: str, parent_id: str | None = None) -> str:
    search_cmd = ["readonly", "search", "--name-exact", name, "--type", "folder", "--json"]
    if parent_id:
        search_cmd.extend(["--parent-id", parent_id])
    out = run_gdrive(search_cmd)
    try:
        items = json.loads(out) if out else []
    except json.JSONDecodeError:
        items = []

    if isinstance(items, dict) and "files" in items:
        items = items["files"]

    if items and isinstance(items, list) and len(items) > 0:
        return items[0]["id"]

    mkdir_cmd = ["mutate", "mkdir", name, "--json"]
    if parent_id:
        mkdir_cmd.extend(["--parent", parent_id])
    created_out = run_gdrive(mkdir_cmd)
    data = json.loads(created_out)
    return data.get("id") or data.get("file", {}).get("id")


def upload_or_update_file(local_path: Path, parent_id: str) -> dict:
    search_cmd = [
        "readonly", "search",
        "--name-exact", local_path.name,
        "--parent-id", parent_id,
        "--json"
    ]
    out = run_gdrive(search_cmd)
    try:
        items = json.loads(out) if out else []
    except json.JSONDecodeError:
        items = []

    if isinstance(items, dict) and "files" in items:
        items = items["files"]

    if items and isinstance(items, list) and len(items) > 0:
        file_id = items[0]["id"]
        up_out = run_gdrive(["mutate", "update", file_id, str(local_path), "--json"])
        return json.loads(up_out)
    else:
        up_out = run_gdrive(["mutate", "upload", str(local_path), "--parent", parent_id, "--json"])
        return json.loads(up_out)


def main():
    parser = argparse.ArgumentParser(description="Sync Google Flow Director projects to Google Drive.")
    parser.add_argument("--project-dir", default="/home/antigravity/flow_projects", help="Local directory of generated projects")
    parser.add_argument("--root-folder", default="Google_Flow_Director_Hub", help="Root folder name in Google Drive")
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
        "assets_folder_id": assets_folder_id,
        "clips_folder_id": clips_folder_id,
        "uploaded_files": []
    }

    # Group files by project slug via .json files
    for json_file in sorted(proj_dir.glob("*.json")):
        slug = json_file.stem
        sub_id = find_or_create_folder(slug, projects_folder_id)
        for related in sorted(proj_dir.glob(f"{slug}*")):
            if related.is_file():
                res = upload_or_update_file(related, sub_id)
                fid = res.get("id") or res.get("file", {}).get("id", "")
                summary["uploaded_files"].append({
                    "name": related.name,
                    "project": slug,
                    "id": fid,
                    "url": f"https://drive.google.com/file/d/{fid}/view" if fid else ""
                })

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
