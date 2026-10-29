"""Restore the .jsonl files the pipeline scripts expect from the gzipped (and split) copies stored in git.

Usage (from the repo root):  python data_pipeline/unpack_data.py
"""
import gzip
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEEP_GZ = {"site_link_graph.jsonl.gz"}      # the crawler writes this one gzipped itself

targets = {}
for gz in sorted(ROOT.rglob("*.jsonl.gz")):
    if gz.name in KEEP_GZ:
        continue
    part = re.match(r"(.+)\.part\d+\.jsonl\.gz$", gz.name)
    target = gz.with_name(part.group(1) + ".jsonl") if part else gz.with_name(gz.name[:-len(".gz")])
    targets.setdefault(target, []).append(gz)

for target, pieces in targets.items():
    with open(target, "wb") as out:
        for piece in pieces:
            with gzip.open(piece, "rb") as src:
                shutil.copyfileobj(src, out, 4 * 1024 * 1024)
    print(f"{target.relative_to(ROOT)}  ({target.stat().st_size / 1e6:.0f} MB from {len(pieces)} file(s))")
