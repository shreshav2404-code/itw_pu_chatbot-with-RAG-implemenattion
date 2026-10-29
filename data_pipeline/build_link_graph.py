"""Build a compact internal navigation/link graph from pages.jsonl."""
import json
import gzip
from pathlib import Path
ROOT = Path(__file__).resolve().parent / "dataset"
pages_file = ROOT / "pages.jsonl"
page_info = {}
for line in pages_file.open(encoding="utf-8"):
    try:
        p = json.loads(line)
        page_info[p["url"]] = {"title": p.get("title", ""), "category": p.get("category", "")}
    except Exception:
        pass
out = ROOT / "site_link_graph.jsonl.gz"
count = 0
with gzip.open(out, "wt", encoding="utf-8") as w:
    for line in pages_file.open(encoding="utf-8"):
        try:
            p = json.loads(line)
        except Exception:
            continue
        seen = set()
        for link in p.get("links", []):
            target = link.get("url", "")
            if target not in page_info:
                continue
            label = link.get("text", "")
            edge_key = (target, label)
            if edge_key in seen:
                continue
            seen.add(edge_key)
            w.write(json.dumps({"source_url": p["url"], "source_title": p.get("title", ""), "source_category": p.get("category", ""), "label": label, "target_url": target, "target_title": page_info[target]["title"], "target_category": page_info[target]["category"]}, ensure_ascii=False) + "\n")
            count += 1
print(json.dumps({"pages_indexed": len(page_info), "internal_edges": count, "output": str(out)}, indent=2))
