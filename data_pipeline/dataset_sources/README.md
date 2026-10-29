# Additional source datasets

These sources are kept separate from the first-party Presidency University website crawl in `..\dataset`.

- `external_research/`: the Bengaluru Wikipedia article (secondary), the UGC private-university directory (official regulator), and a legal-transcription source record. Use the official university site or regulator before answering current student-policy questions. Similar-name Presidency Universities in Kolkata and Bangladesh are excluded.
- `jspui/`: full public DSpace metadata crawl at the user-provided repository, including all 14,145 item records, exam/question-paper subsets, makeup-exam subset, and bitstream links. The repository states all rights reserved unless otherwise indicated, so attached binaries were not bulk-downloaded.
- `library_site/`: public Koha OPAC navigation and pages, search options, branch information, borrowing rules, holdings fields, media references, and 26 public catalog records. The interface does not expose the full catalog anonymously; the API requires authentication and the only public list is a 20-record popular-items report.
- `user_pdf/`: the PDF found in `D:\pu_bot\keshavs_input`, preserved and extracted into page text/chunks/topic matches. It is specific to B.Tech CSE 2023–27.
- `campus_map/`: the user-supplied CampusMap PDF, copied unchanged, with a rendered page preview and source-linked page text/chunks. It is a campus/site plan, not a verified turn-by-turn indoor route graph.
- `user_media/`: 80 compressed user-supplied campus images, reviewed captions/sign text, normalized caption embeddings, and a retrieval helper; originals remain under `keshavs_input`. No video or audio files were present in the folder at the time it was inventoried.
- `campus_virtual_tour/`: the third-party 360-degree tour linked by the university. Includes scene/hotspot labels, thumbnails, asset references, and a live-tour URL.

All crawls are snapshots. Keep the source URL, source class, issue date/batch, and retrieval date attached to each RAG result. Do not combine regulations for different programs or cohorts without checking applicability.
