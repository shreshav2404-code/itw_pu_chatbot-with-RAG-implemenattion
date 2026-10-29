# Presidency University DSpace repository crawl

Source: `http://182.72.188.194:8080/jspui/` (DSpace 6.3).

## Files

- `communities_collections.jsonl`: public community/collection links from the repository's hierarchy page.
- `oai_sets.jsonl` and `oai_listsets_initial.xml`: all 242 set names/specs exposed by the repository's OAI-PMH endpoint; the XML file is the initial response page.
- `item_catalog.jsonl`: all items exposed by the public title browse index (issue date, title, author, handle URL).
- `item_records.jsonl`: item-level Dublin Core fields, abstract/description when present, collection breadcrumb, and bitstream references.
- `item_chunks.jsonl`: RAG-ready text passages assembled from item metadata, with the item handle as source.
- `collection_counts.jsonl`: item counts for every observed collection breadcrumb.
- `exam_and_question_paper_items.jsonl`, `makeup_exam_items.jsonl`, `item_content_summary.json`: useful exam, question paper, and makeup subsets and coverage counts.
- `bitstreams_manifest.jsonl`: file URL, filename, item title, and collection path for each attached repository file.
- `item_failures.json`: item detail pages that failed.
- `crawl_summary.json`: item/page counts and endpoint limitations.

The repository's item pages state that items are copyright protected and all rights are reserved unless otherwise indicated. This crawl captures public metadata and file URLs; it does not bulk-download bitstreams. Check each item's rights/license before downloading or redistributing files. The OAI endpoint lists collection sets but `ListRecords` returns `noRecordsMatch`; the REST API redirects to an unreachable HTTPS port, and sitemap paths advertised by `robots.txt` return 404. The public JSPUI browse and item pages were used instead.
