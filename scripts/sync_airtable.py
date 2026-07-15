#!/usr/bin/env python3
"""
sync_airtable.py — Airtable Image Gallery → GitHub + Supabase
Buffer Blaster | executiveusa/buffer-blaster-

Fetches all images from the Airtable gallery view, downloads them to
assets/airtable/, commits to GitHub, and writes metadata to Supabase.

Usage:
    python scripts/sync_airtable.py
    python scripts/sync_airtable.py --client-slug=mybrands

Env vars required:
    AIRTABLE_API_KEY
    AIRTABLE_BASE_ID (default: apptABTHZ91toPYKi)
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
    GITHUB_TOKEN (for auto-commit)
    GITHUB_REPO  (default: executiveusa/buffer-blaster-)
"""

import os
import sys
import json
import hashlib
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────

AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "apptABTHZ91toPYKi")
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_VIEW_ID = "shrncEgdjoHVI0G8w"  # gallery view from the provided URL

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

ASSETS_DIR = Path("assets/airtable")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ── Airtable fetch ───────────────────────────────────────────────────────────

def fetch_airtable_records() -> list[dict]:
    """Fetch all records from the Airtable gallery view."""
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    records = []
    offset = None

    print(f"Fetching from Airtable base {AIRTABLE_BASE_ID}...")

    while True:
        params = {"view": AIRTABLE_VIEW_ID, "pageSize": 100}
        if offset:
            params["offset"] = offset

        # Try the known table — adapt if schema differs
        response = requests.get(
            f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Images",
            headers=headers,
            params=params,
            timeout=30,
        )

        if response.status_code == 404:
            # Try first table if "Images" doesn't exist
            response = requests.get(
                f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Gallery",
                headers=headers,
                params=params,
                timeout=30,
            )

        response.raise_for_status()
        data = response.json()

        batch = data.get("records", [])
        records.extend(batch)
        print(f"  Fetched {len(batch)} records (total: {len(records)})")

        offset = data.get("offset")
        if not offset:
            break

    return records


# ── Image download ───────────────────────────────────────────────────────────

def download_image(url: str, record_id: str, field_name: str, idx: int) -> dict | None:
    """Download an image and save to assets/airtable/."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Determine extension from content-type or URL
        content_type = response.headers.get("content-type", "image/jpeg")
        ext_map = {
            "image/jpeg": "jpg", "image/jpg": "jpg",
            "image/png": "png", "image/gif": "gif",
            "image/webp": "webp", "image/avif": "avif",
        }
        ext = ext_map.get(content_type.split(";")[0].strip(), "jpg")

        filename = f"{record_id}_{field_name}_{idx}.{ext}"
        filepath = ASSETS_DIR / filename

        # Skip if already downloaded and identical
        if filepath.exists():
            existing_hash = hashlib.md5(filepath.read_bytes()).hexdigest()
            new_hash = hashlib.md5(response.content).hexdigest()
            if existing_hash == new_hash:
                print(f"  ↳ {filename} unchanged, skipping")
                return {"path": str(filepath), "filename": filename, "skipped": True}

        filepath.write_bytes(response.content)
        size_kb = len(response.content) // 1024
        print(f"  ↳ Downloaded {filename} ({size_kb}KB)")

        return {
            "path": str(filepath),
            "filename": filename,
            "size_bytes": len(response.content),
            "content_type": content_type,
            "skipped": False,
        }

    except Exception as e:
        print(f"  ✗ Failed to download {url}: {e}")
        return None


# ── Supabase write ───────────────────────────────────────────────────────────

def upsert_to_supabase(records: list[dict]) -> None:
    """Write asset metadata to Supabase airtable_assets table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("  Supabase not configured — skipping metadata write")
        return

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/airtable_assets",
        headers=headers,
        json=records,
        timeout=30,
    )

    if response.status_code in (200, 201):
        print(f"  ✓ Wrote {len(records)} records to Supabase")
    else:
        print(f"  ✗ Supabase write failed: {response.status_code} {response.text}")


# ── GitHub commit ────────────────────────────────────────────────────────────

def commit_to_github() -> None:
    """Stage and commit all downloaded images."""
    try:
        subprocess.run(["git", "add", "assets/airtable/"], check=True)

        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True
        )
        changed = result.stdout.strip()

        if not changed:
            print("  No new images to commit")
            return

        count = len(changed.splitlines())
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        msg = f"chore: sync airtable gallery [{timestamp}] ({count} images)"

        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"  ✓ Committed and pushed {count} images")

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Git error: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Buffer Blaster — Airtable Gallery Sync")
    print("=" * 60)

    if not AIRTABLE_API_KEY:
        print("ERROR: AIRTABLE_API_KEY not set")
        sys.exit(1)

    # Fetch records
    records = fetch_airtable_records()
    print(f"\nFound {len(records)} records in Airtable gallery\n")

    # Download images
    supabase_rows = []
    total_downloaded = 0
    total_skipped = 0

    for record in records:
        record_id = record["id"]
        fields = record.get("fields", {})

        # Find attachment fields (Airtable attachments are arrays of objects with url)
        for field_name, field_value in fields.items():
            if not isinstance(field_value, list):
                continue

            for idx, attachment in enumerate(field_value):
                if not isinstance(attachment, dict) or "url" not in attachment:
                    continue

                result = download_image(attachment["url"], record_id, field_name, idx)
                if result:
                    if result.get("skipped"):
                        total_skipped += 1
                    else:
                        total_downloaded += 1

                    supabase_rows.append({
                        "airtable_record_id": record_id,
                        "image_url": attachment["url"],
                        "github_path": f"assets/airtable/{result['filename']}",
                        "tags_json": json.dumps(fields.get("Tags", [])),
                        "synced_at": datetime.utcnow().isoformat(),
                    })

    print(f"\nDownloaded: {total_downloaded} | Skipped (unchanged): {total_skipped}")

    # Write metadata
    if supabase_rows:
        print("\nWriting to Supabase...")
        upsert_to_supabase(supabase_rows)

    # Commit to GitHub
    print("\nCommitting to GitHub...")
    commit_to_github()

    # Write local manifest
    manifest_path = ASSETS_DIR / "_manifest.json"
    manifest_path.write_text(json.dumps({
        "synced_at": datetime.utcnow().isoformat(),
        "total_records": len(records),
        "total_images": total_downloaded + total_skipped,
        "assets": [r["github_path"] for r in supabase_rows],
    }, indent=2))

    print(f"\n✓ Sync complete. Manifest: {manifest_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
