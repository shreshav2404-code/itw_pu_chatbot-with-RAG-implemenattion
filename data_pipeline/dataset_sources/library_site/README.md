# Presidency University Library OPAC crawl

Source: http://182.72.188.195/ (Koha online public access catalog).

- pages.jsonl: source-linked readable page text, headings, links, and media references.
- catalog_items.jsonl: structured metadata for publicly surfaced catalog records, with item-level holding locations and sanitized status values.
- catalog_items_chunks.jsonl: one RAG-ready text passage per exported catalog record.
- catalog_items_summary.json: API coverage and exhaustiveness notes.
- media_manifest.jsonl: image/audio/video/embed URLs and page context; binary media not downloaded.
- documents_manifest.jsonl: linked document references, with no binary download in this pass.
- crawl_summary.json and crawl_failures.json: counts, scope, and errors.

This crawl covers public catalog navigation and linked pages. The only confirmed anonymous list endpoint is Koha public report 180 (most checked out), which exposed 20 rows; the export also includes public item-detail records linked on the OPAC. The hierarchy browse page says it is empty/not configured, ordinary search queries return a 54-byte “No search result found” response, and the bibliographic REST endpoint requires authentication. Therefore the full catalog cannot be exhausted from the available public interface. No book files were downloaded. Patron names/IDs, due dates, and barcodes are omitted from exported item holdings. External links to DSpace, Drive, commercial databases, and other providers are recorded on page records but not crawled.
