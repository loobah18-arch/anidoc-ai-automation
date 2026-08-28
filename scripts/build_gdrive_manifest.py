#!/usr/bin/env python3
"""
Google Drive Manifest Builder
Creates stable source manifest mapping original filename → Drive ID → canonical name.
Designed for GitHub Actions workflow artifact generation.
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Import existing Drive list helper
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.gdrive_manager import list_gdrive_folder_items


def build_manifest(
    gdrive_folder_url: str,
    output_path: Path,
    episodes_limit: int = None
) -> Dict[str, Any]:
    """
    Build source manifest from Google Drive folder.

    Returns manifest with:
    - version, generated_at
    - sources: list of {drive_file_id, original_filename, canonical_filename, url}
    """
    print(f"📋 [ManifestBuilder] Listing Google Drive folder...")
    items = list_gdrive_folder_items(gdrive_folder_url)

    if not items:
        raise RuntimeError("No items found in Google Drive folder")

    # Filter JJK episodes
    jjk_items = [
        item for item in items
        if any(kw in item["name"].lower() for kw in ["jujutsu", "jjk"])
    ]

    if episodes_limit:
        jjk_items = jjk_items[:episodes_limit]

    print(f"✅ [ManifestBuilder] Found {len(jjk_items)} JJK episodes")

    sources = []
    for item in jjk_items:
        # Canonical filename: sanitize for filesystem safety
        canonical = item["name"].replace(" ", "_")
        canonical = "".join(c for c in canonical if c.isalnum() or c in "._-")
        if not canonical.lower().endswith((".mkv", ".mp4", ".avi")):
            canonical += ".mkv"

        sources.append({
            "drive_file_id": item["id"],
            "original_filename": item["name"],
            "canonical_filename": canonical,
            "url": item["url"]
        })

    manifest = {
        "version": "1.0.0",
        "generated_at": None,  # Will be set by workflow
        "total_sources": len(sources),
        "sources": sources
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✅ [ManifestBuilder] Manifest written: {output_path}")
    print(f"📊 Total sources: {len(sources)}")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Build Google Drive source manifest")
    parser.add_argument("--gdrive-url", required=True, help="Google Drive folder URL or ID")
    parser.add_argument("--output", required=True, help="Output manifest JSON path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of episodes")

    args = parser.parse_args()

    build_manifest(
        gdrive_folder_url=args.gdrive_url,
        output_path=Path(args.output),
        episodes_limit=args.limit
    )


if __name__ == "__main__":
    main()
