# Presidency University RAG data preparation

## Main outputs

- `dataset/` contains the university-domain crawl: 4,333 saved HTML pages so far, text passages, page links, 2,522 downloaded public university documents, extracted document text, and media references.
- `dataset/focused_chunks.jsonl` is the topic-tagged retrieval file for exams/passing/makeup/year progression, programs/curricula, fees/assistance, academic support, Launchpad, calendar/timetable, campus facilities, the repository, library catalog, uploaded PDF, and campus tour.
- `dataset_sources/` keeps other sources separate: DSpace repository, Koha library site, supplied academic PDF, campus map, compressed user-photo derivatives, internet research (Wikipedia and UGC), and the 360-degree campus tour.

## Data format

JSONL records are UTF-8. Web/page chunks include a stable chunk ID and `metadata` with page URL, title, category, heading, chunk index, and source type. Document chunks preserve both the source URL and the downloaded relative file path. Media manifests preserve page URL, asset URL, tag/type, and available alt/title/caption metadata. Repository items preserve DSpace handle and collection context.

For ingestion, start with `dataset/focused_chunks.jsonl` for the priority topics. Use `dataset/chunks.jsonl` and `dataset/document_chunks.jsonl` for the full first-party textual corpus. Keep `dataset_sources/external_research/` in a separate collection, and retain source class so answers can distinguish the official university website, regulator data, and secondary sources.

## Refresh and extraction scripts

Run from this folder:

```powershell
node .\crawl_presidency.mjs
python .\find_unindexed_links.py
node .\crawl_unindexed.mjs
python .\extract_documents.py
python .\build_link_graph.py
python .\normalize_chunk_ids.py
python .\build_focused_dataset.py
python .\finalize_dataset.py
```

The crawler downloads linked university-domain documents up to 50 MB each. Media binaries are inventoried rather than bulk-downloaded; 142 low-resolution images from the linked 360-degree tour are included. Re-crawl date-sensitive pages before using fee, scholarship, timetable, calendar, or notice answers. For pass/promotion rules, identify the student's program and admission batch first.

See `dataset/README.md`, `dataset/FOCUS_GUIDE.md`, `dataset/RAG_INGESTION_GUIDE.md`, and `dataset_sources/README.md` for scope, ingestion guidance, and limitations.
