"""Merge every RAG chunk file into one cleaned, deduplicated corpus for JupyterHub.

Usage: python build_upload_bundle.py <project_root> <out_dir>
Writes <out_dir>/pu_corpus.jsonl.gz and <out_dir>/corpus_stats.json
"""
import collections, gzip, hashlib, json, re, sys
from pathlib import Path

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

# Order = priority when the same text appears in several files (first one wins).
SOURCES = [
    "dataset_sources/user_pdf/chunks.jsonl",
    "dataset/document_chunks.jsonl",
    "dataset/chunks.jsonl",
    "dataset_sources/jspui/item_chunks.jsonl",
    "dataset_sources/library_site/catalog_items_chunks.jsonl",
    "dataset_sources/campus_map/chunks.jsonl",
    "dataset_sources/campus_virtual_tour/chunks.jsonl",
    "dataset_sources/user_media/image_chunks.jsonl",
    "dataset_sources/user_media/video_chunks.jsonl",
    "dataset_sources/user_media/student_interview_chunks.jsonl",
    "dataset_sources/external_research/chunks.jsonl",
]
FOCUSED = "dataset/focused_chunks.jsonl"   # same ids as above, adds topic tags

SOURCE_CLASS = {
    "webpage": "official_website",
    "document": "official_document",
    "user_uploaded_pdf": "official_program_regulation",
    "repository_item_metadata": "repository_metadata",
    "catalog_item": "library_catalog",
    "user_provided_campus_map": "campus_map",
    "virtual_tour": "campus_tour",
    "user_provided_image_caption": "user_photo",
    "user_provided_video": "user_video",
    "user_provided_video_transcript": "user_video",
    "user_provided_audio_transcript": "user_interview",
    "external": "external",
}
UNVERIFIED = {"user_photo", "user_video", "user_interview"}
MIN_CHARS = 40


def read_jsonl(path):
    with open(ROOT / path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def clean(text):
    text = (text or "").replace("�", " ")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


WORD = re.compile(r"[a-z]{3,}")
vocab = set()

def unmirror(text):
    """The campus-map PDF stores some labels mirrored (RECIFFO -> OFFICER). Flip tokens that only
    make sense reversed, using words seen elsewhere in the corpus as the dictionary."""
    out = []
    for tok in text.split(" "):
        core = re.sub(r"[^A-Za-z]", "", tok).lower()
        if len(core) >= 3 and core not in vocab and core[::-1] in vocab:
            tok = tok[::-1]
        out.append(tok)
    return " ".join(out)


def mmss(seconds):
    s = int(float(seconds or 0))
    return f"{s // 60}:{s % 60:02d}"


def normalize(r, path):
    md = r.get("metadata") or {}
    stype = md.get("source_type") or "unknown"
    sclass = SOURCE_CLASS.get(stype, "other")
    text = clean(r.get("text"))
    if sclass == "campus_map":
        text = unmirror(text)

    title = md.get("title") or ""
    page = md.get("page") or md.get("page_number")
    local_path = md.get("local_path") or md.get("frame_path") or md.get("audio_path")
    if sclass == "official_program_regulation":
        title = "B.Tech CSE Programme Regulations & Curriculum 2023-27"
    elif sclass == "campus_map":
        title = "Campus Map (user-provided PDF)"
        local_path = "campus_map.png"          # shipped next to the corpus in upload/
    elif sclass == "user_video":
        title = f"Campus video {md.get('video_id', '')} at {mmss(md.get('start_seconds'))}"
    elif sclass == "user_interview":
        title = f"Student interview at {mmss(md.get('start_seconds'))}"

    rec = {
        "id": r["id"],
        "text": text,
        "title": title,
        "source_class": sclass,
        "source_type": stype,
        "url": md.get("url"),
        "page_url": md.get("page_url"),
        "page": page,
        "local_path": local_path,
        "category": md.get("category"),
        "topics": list(md.get("topic_tags") or []),
        "unverified": sclass in UNVERIFIED or bool(md.get("speech_text_is_automatic_and_unverified")),
    }
    if md.get("start_seconds") is not None:
        rec["start_seconds"], rec["end_seconds"] = md.get("start_seconds"), md.get("end_seconds")
    if sclass == "external" and md.get("source_class"):
        rec["external_kind"] = md["source_class"]
    return {k: v for k, v in rec.items() if v not in (None, "", [])}


# 1. topic tags from the focused file
topics_by_id = collections.defaultdict(set)
focused_ids = set()
for r in read_jsonl(FOCUSED):
    focused_ids.add(r["id"])
    topics_by_id[r["id"]].update((r.get("metadata") or {}).get("topic_tags") or [])

# 2. merge, clean, dedupe
seen_ids, seen_text = set(), {}
records = []
stats = collections.Counter()
per_class = collections.Counter()
for path in SOURCES:
    for r in read_jsonl(path):
        stats["read"] += 1
        if r["id"] in seen_ids:
            stats["dup_id"] += 1
            continue
        seen_ids.add(r["id"])
        rec = normalize(r, path)
        if len(rec["text"]) < MIN_CHARS:
            stats["too_short"] += 1
            continue
        key = hashlib.md5(re.sub(r"\s+", " ", rec["text"].lower()).encode()).hexdigest()
        if key in seen_text:
            stats["dup_text"] += 1
            records[seen_text[key]]["n_copies"] = records[seen_text[key]].get("n_copies", 1) + 1
            continue
        rec["topics"] = sorted(set(rec.get("topics", [])) | topics_by_id.get(r["id"], set()))
        if not rec["topics"]:
            rec.pop("topics")
        seen_text[key] = len(records)
        records.append(rec)
        per_class[rec["source_class"]] += 1
        if rec["source_class"] in ("official_document", "official_website", "official_program_regulation"):
            vocab.update(WORD.findall(rec["text"].lower()))

stats["focused_ids_not_in_sources"] = len(focused_ids - seen_ids)

# 3. write
out_file = OUT / "pu_corpus.jsonl.gz"
with gzip.open(out_file, "wt", encoding="utf-8", compresslevel=6) as fh:
    for rec in records:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

summary = {
    "records": len(records),
    "read": stats["read"],
    "removed_duplicate_ids": stats["dup_id"],
    "removed_duplicate_text": stats["dup_text"],
    "removed_too_short": stats["too_short"],
    "focused_ids_not_in_sources": stats["focused_ids_not_in_sources"],
    "by_source_class": dict(per_class.most_common()),
    "size_mb": round(out_file.stat().st_size / 1e6, 1),
}
(OUT / "corpus_stats.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
