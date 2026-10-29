"""Create source-linked text chunks for the user-provided campus map PDF."""
import hashlib
import json
import re
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent / "dataset_sources" / "campus_map"
PDF = ROOT / "CampusMap.pdf"
rows = []
chunks = []
for page_number, page in enumerate(PdfReader(str(PDF)).pages, 1):
    text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
    text = text.encode("utf-8", "replace").decode("utf-8")
    rows.append({"page_number": page_number, "text": text,
                 "source_type": "user_provided_campus_map",
                 "local_path": "dataset_sources/campus_map/CampusMap.pdf"})
    for start in range(0, len(text), 900):
        piece = text[start:start + 900]
        if not piece.strip():
            continue
        chunks.append({
            "id": f"map-{hashlib.sha256(b'campus-map').hexdigest()[:16]}-{page_number}-{start // 900}",
            "text": piece,
            "metadata": {
                "title": "Presidency University Campus Map",
                "page_number": page_number,
                "chunk_index": start // 900,
                "local_path": "dataset_sources/campus_map/CampusMap.pdf",
                "page_image_path": "dataset_sources/campus_map/campus-map-page-1-preview.png",
                "source_type": "user_provided_campus_map",
            },
        })
(ROOT / "pages.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
(ROOT / "chunks.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in chunks), encoding="utf-8")
print(json.dumps({"pages": len(rows), "characters": sum(len(row["text"]) for row in rows),
                  "chunks": len(chunks), "pdf_bytes": PDF.stat().st_size,
                  "pdf_unchanged_copy": True}, indent=2))
