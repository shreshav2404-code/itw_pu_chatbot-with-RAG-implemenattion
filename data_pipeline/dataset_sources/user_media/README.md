# User-provided image data

The compressed copies under `compressed/` were derived from raster images in `D:\pu_bot\keshavs_input`. Original files were left unchanged. Images larger than 3072 pixels on the long edge were resized; JPEGs use quality 88, WebP copies use quality 88, and PNG copies use lossless optimization. EXIF orientation was applied before saving; ICC profiles were retained when supported.

`image_processing_manifest.jsonl` maps each original absolute/relative path to its compressed derivative and records dimensions, byte sizes, and settings. The 80 image derivatives total about 109 MB compared with about 3.07 GB of originals. PDF files, including `CampusMap.pdf`, were excluded from image processing.

`image_captions.jsonl` contains reviewed visual captions and confidently legible sign text for all 80 photos. `image_chunks.jsonl` is the RAG-ready text form, with each caption linked to its compressed image and original path. Captions use user-provided filenames as search labels but do not treat uncertain filename labels as verified office names. `image_caption_embeddings.npy` contains 80 normalized 384-dimensional caption vectors produced by `sentence-transformers/all-MiniLM-L6-v2`; `image_vector_metadata.jsonl` maps vector rows back to photos, and `image_embedding_info.json` documents the embedding model and intended text-to-image-caption retrieval mode. These are caption embeddings, not raw image embeddings; an uploaded image query should first be interpreted by the vision model or embedded with a compatible vision encoder.

Run `python search_image_captions.py "Office of the Registrar" --top-k 5` to try text-to-photo retrieval on this local set. It uses cosine similarity over the 80 normalized vectors. The workspace has no FAISS or Qdrant package installed; for a set this small, the flat matrix search is sufficient, and the notebook can load these vectors or recreate them before building a larger FAISS/Qdrant index.

To regenerate captions and vectors after adding photos, run `python caption_user_images.py` after extending the reviewed caption map in that script, then run `python embed_image_captions.py`. `build_contact_sheets.py` produces temporary review sheets for new images.

## User-provided campus videos

`V1.mp4` and `V2.mp4` are preserved in `D:\pu_bot\keshavs_input`. H.264 1080p derivatives are in `compressed_videos/`; these are about 671.8 MB combined, versus 1,215.4 MB for the originals (44.7% smaller). Mono 16 kHz audio tracks are in `extracted_audio/`. The original HEVC videos remain unchanged.

Frames sampled every 2 seconds are in `video_frames/` (96 frames total). `video_frames.jsonl` maps frames to source timestamps; `video_scene_captions.jsonl` contains broad reviewed scene captions; and `video_chunks.jsonl` is the RAG-ready timestamped text. `video_audio_transcripts.jsonl` contains 40 timestamped Whisper small ASR segments. ASR wording is unverified and can be noisy, so validate names, directions and any factual claim against the visible source or an official university source. Captions summarize scene intervals from reviewed contact sheets, not frame-by-frame model output. Sampling can miss signs or events between frames. Some source frames change orientation during filming; the extracted frame files retain their sampled orientation, and the manifest notes this limitation.

Run `python build_video_dataset.py` to regenerate the scene-caption and RAG chunk JSONL files from the current frame and transcript manifests. Run `python process_videos.py` only if you need to regenerate derivatives from the preserved originals.

## Student interview audio

The user-provided `Interview student.m4a` remains in `D:\pu_bot\keshavs_input`. A 16 kHz mono WAV derivative is in `extracted_audio/student_interview_16k_mono.wav`; `student_interview_transcript.jsonl` contains timestamped Whisper small output, and `student_interview_chunks.jsonl` is its RAG-ready form. The original is AAC mono at 48 kHz and about 4 minutes 18 seconds. The transcript is automatic and unverified. Confirm student names, quoted speech and factual claims against the recording before using or presenting them. Run `python transcribe_student_interview.py` to regenerate the transcript and chunks.
