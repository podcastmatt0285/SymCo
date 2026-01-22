#!/usr/bin/env python3

import os
import shutil

source_dir = os.path.expanduser("~/SymCo")
output_dir = os.path.expanduser("~/SymCotxt")

os.makedirs(output_dir, exist_ok=True)

extensions = (".py", ".txt", ".md", "json")

for root, dirs, files in os.walk(source_dir):
    for file in files:
        if file.endswith(extensions):
            src_path = os.path.join(root, file)

            if os.path.abspath(src_path) == os.path.abspath(__file__):
                continue

            dst_path = os.path.join(output_dir, file + ".txt")
            shutil.copy2(src_path, dst_path)
