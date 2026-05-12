#!/usr/bin/env python3
"""
export_txt2.py — Export app source files to ~/Wadswtxt for NotebookLM ingestion.

Copies every relevant .py / .json / .txt / .md file from ~/SymCo,
flattening the tree into <filename>.txt files so NotebookLM can load
them as individual sources. The output dir is wiped on each run so
stale files don't accumulate.
"""

import os
import shutil

SOURCE_DIR = os.path.expanduser("~/SymCo")
OUTPUT_DIR = os.path.expanduser("~/Wadswtxt")

# Directories to skip entirely (matched against each dir name during walk)
SKIP_DIRS = {
    "venv",
    "__pycache__",
    "android",
    "backups",
    "claudeHelper",
    "moved",
    "static",
}

# Individual filenames to skip regardless of location
SKIP_FILES = {
    "export_txt2.py",   # this script
    "cheat.txt",
    "tick_state.txt",
    "wadsworth_backup.sql",
    "reserve_banks_backup.sql",
    "backup.sh",
    "restore.sh",
    "setup.sh",
    "Procfile",
    "Task",
}

# Skip one-off patch and migration scripts (already applied to the live DB)
SKIP_PREFIXES = ("patch_", "migrate_")

# File extensions to include
INCLUDE_EXTENSIONS = (".py", ".txt", ".md", ".json")

# ── Run ───────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Wipe existing output so stale files don't linger between runs
for old in os.listdir(OUTPUT_DIR):
    old_path = os.path.join(OUTPUT_DIR, old)
    if os.path.isfile(old_path):
        os.remove(old_path)

copied = 0
for root, dirs, files in os.walk(SOURCE_DIR):
    # Prune dirs in-place so os.walk never descends into them
    dirs[:] = [
        d for d in dirs
        if d not in SKIP_DIRS and not d.startswith(".")
    ]

    for filename in sorted(files):
        if not filename.endswith(INCLUDE_EXTENSIONS):
            continue
        if filename in SKIP_FILES:
            continue
        if any(filename.startswith(p) for p in SKIP_PREFIXES):
            continue

        src = os.path.join(root, filename)
        if os.path.abspath(src) == os.path.abspath(__file__):
            continue

        # Flatten to a single dir; prefix with subpath to avoid collisions
        rel = os.path.relpath(src, SOURCE_DIR)          # e.g. "banks/brokerage_firm.py"
        flat = rel.replace(os.sep, "__")                # e.g. "banks__brokerage_firm.py"
        dst = os.path.join(OUTPUT_DIR, flat + ".txt")

        shutil.copy2(src, dst)
        copied += 1
        print(f"  {rel}")

print(f"\nExported {copied} files → {OUTPUT_DIR}")
