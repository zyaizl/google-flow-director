#!/usr/bin/env python3
"""
Google Flow Director — Google Drive Cloud Archive & Sync Script
Automatically organizes and uploads generated storyboard projects (.md, .html, .json,
and optional reference images / Flow video clips) to a structured folder hierarchy
in Google Drive:
  Google_Flow_Director_Hub/
  ├── 01_项目分镜与故事板_Projects/
  │   └── <project_slug>/
  │       ├── <slug>_分镜执行单.md
  │       ├── <slug>_导演故事板.html
  │       └── <slug>.json
  ├── 02_产品与首尾帧垫图资产_Ingredients/
  └── 03_Google_Flow_生成视频片段_Clips/
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
        "projects_folder_url": f"https://drive.google.com/drive/folders/{projects_folder_id}",
        "assets_folder_id": assets_folder_id,
        "clips_folder_id": clips_folder_id,
        "uploaded_files": []
    }

    for json_file in sorted(proj_dir.glob("*.json")):
        slug = json_file.stem
        sub_id = find_or_create_folder(slug, projects_folder_id)
        for related in sorted(proj_dir.glob(f"{slug}*")):
            if related.is_file():
                res = upload_or_update_file(related, sub_id)
                fid = res.get("id", "")
                summary["uploaded_files"].append({
                    "name": related.name,
                    "project": slug,
                    "project_folder_url": f"https://drive.google.com/drive/folders/{sub_id}",
                    "id": fid,
                    "url": res.get("webViewLink") or (f"https://drive.google.com/file/d/{fid}/view" if fid else "")
                })

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
