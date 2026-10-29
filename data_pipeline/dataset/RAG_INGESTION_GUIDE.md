# JupyterHub multimodal RAG ingestion guide

This crawl is a source corpus for the planned text-and-image chatbot. It is not a trained model or a ready vector index. Keep the original records and source folders unchanged; build derived embeddings/index files in a separate output directory.

## Corpus routing

- Official university pages and their extracted linked documents: `chunks.jsonl` and `document_chunks.jsonl`.
- Topic-focused subset: `focused_chunks.jsonl` (useful for a first prototype; it is not a replacement for the full corpus).
- Supplied B.Tech CSE 2023–27 regulations: `../dataset_sources/user_pdf/chunks.jsonl`.
- Repository and library metadata: `../dataset_sources/jspui/item_chunks.jsonl` and `../dataset_sources/library_site/catalog_items_chunks.jsonl`.
- Wikipedia and regulator research: `../dataset_sources/external_research/chunks.jsonl`; index separately and retain the source class.
- Campus tour labels: `../dataset_sources/campus_virtual_tour/chunks.jsonl`; thumbnails and live tour pointer are in that folder.
- Supplied campus map: `../dataset_sources/campus_map/chunks.jsonl`; original PDF and a page preview are retained in that folder.
- User-photo captions: `../dataset_sources/user_media/image_chunks.jsonl`; caption embeddings and row metadata are beside the source photos in that folder.
- User-provided video scenes and nearby speech: `../dataset_sources/user_media/video_chunks.jsonl`; timestamps link to the sampled frame and extracted audio/transcript records. The compressed videos, frames, captions, audio and manifests are in that folder.
- User-provided student interview speech: `../dataset_sources/user_media/student_interview_chunks.jsonl`; timestamps link to the original audio and normalized WAV. Treat the transcript as unverified user-provided material, not university policy.
- Website media pointers: `media_manifest.jsonl`. These are references and captions, not a downloaded visual corpus.

## Suggested record fields

Keep each passage's text and its existing metadata, then add derived fields such as `embedding_model`, `index_version`, and `indexed_at`. Preserve, whenever present:

- source URL or local path, title, source type/class, and retrieval date;
- academic program, admission cohort, document issue/effective date, and page number when known;
- topic tags and any original heading/collection/department context.

Do not merge different program regulations or cohorts into an unlabelled source. Cite the retrieved URL and identify a document/page or section when available. Keep external sources separate from university-issued policy.

## Prototype workflow

1. In the Data Lab JupyterHub session, inspect the assigned GPU, available disk/RAM, Python version, and installed versions of Transformers, PyTorch, and the model's processor before loading Qwen3-VL. Do not assume that the 30B model fits a particular GPU; use the environment's approved quantization/runtime only after checking its support.
2. Start with `focused_chunks.jsonl` plus the CSE PDF and the official handbook/regulation document chunks. Add the full corpus after checking retrieval quality and storage needs.
3. Use an embedding model for text passages and a vector store (FAISS for a local prototype, or Qdrant if the notebook deployment supports a service). Store source metadata beside each vector; chunking should respect page/section boundaries and the model's context limits.
4. At query time, let the vision-language model interpret an uploaded notice/timetable/photo, turn the relevant details into a retrieval query, retrieve university passages, and answer with citations. A photo can supply query context without being added to the permanent knowledge index.
5. For university images intended as corpus knowledge, resolve selected `media_manifest.jsonl` references to local assets and retain page URL, alt text, caption, and asset URL. The supplied photos already have reviewed captions and 384-D text embeddings in `dataset_sources/user_media/`; these support text-to-image-caption retrieval. For true image-to-image similarity, generate embeddings with a compatible vision encoder in JupyterHub. The supplied V1/V2 videos have compressed H.264 copies, 96 frames sampled every 2 seconds, broad scene captions, 16 kHz mono WAV tracks, and 40 timestamped Whisper small transcript segments. The transcript is automatic and unverified; source names and directions need review. The website crawl has not run OCR on all website images or transcription on website audio/video.
6. Evaluate citation correctness and cohort/program-specific questions against the relevant official documents before exposing the prototype to students. Refresh date-sensitive policies and calendars on a schedule.

## User-provided media

Place local images, videos, and audio under `D:\pu_bot\keshavs_input` (or tell the operator if using another folder). They should be inventoried separately from university-published material and never treated as official policy solely because a student uploaded them. The 80 photos currently present have high-quality compressed derivatives in `../dataset_sources/user_media/compressed/`; originals are preserved. The campus map PDF has been copied unchanged, inspected, and extracted as its own navigation source. V1 and V2 video derivatives and their preprocessing outputs are documented in `../dataset_sources/user_media/README.md`.

## Current corpus limits

The website media manifest records references, not all media bytes. The public repository and library catalog expose metadata but have separate access/copyright limits documented in `../dataset_sources/README.md`. Scanned PDFs or legacy formats may yield no text; images, audio, and video require their own OCR/vision/transcription processing. Consult `README.md` and `FOCUS_GUIDE.md` for crawl scope and policy cautions.
