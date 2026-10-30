# Presidency University 360° Tour Dataset

Extracted from the university's [360° view page](https://presidencyuniversity.in/360-view/) and its embedded [ImmersiveTourz virtual tour](https://www.immersivetourz.com/presidencyuniversity/).

- Scene records: 141
- Files: scene records (`dataset.csv`, `dataset.json`); tour labels (`tour_label_info.csv`, `tour_label_info.jsonl`); navigation graph (`navigation_graph.json`, `navigation_edges.csv`, `navigation_info.jsonl`); user landmark note (`user_annotations.jsonl`); video-derived frames (`video_frame_index.csv`, `video_frame_index.jsonl`, `video_observations.jsonl`, `video_extract/`); and `images/` (tour preview thumbnails)
- Scene records include provider IDs and labels, preview paths, and source links. The navigation files preserve direct scene-to-scene links and the provider's yaw/distance values; their units are unspecified. The label files preserve additional tour labels and matching scene IDs. The user annotation records the fountain landmark note and is separate from provider-supplied data.
- `images/` contains tour preview thumbnails. `video_extract/` contains 113 screen-recording frames sampled every 3 seconds (768 px wide) plus contact sheets; `video_observations.jsonl` stores timestamped visual summaries. These are screen captures, not source panoramas. The full-resolution tour tiles are not all publicly retrievable, so the panoramas were not reconstructed.
- Labels are copied from the public tour manifest; numeric labels are retained as published. `user_annotations.jsonl` includes the user-identified fountain landmark, corroborated by the aerial video frame at 00:24.
- Run `python extract_dataset.py` to refresh the metadata and previews. Uses only the Python standard library.

Source content belongs to Presidency University / ImmersiveTourz. This extraction preserves source attribution; check their terms before redistribution or model training.
