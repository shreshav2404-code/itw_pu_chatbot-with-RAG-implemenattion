"""Create timestamped scene text and RAG chunks for the supplied campus videos."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRAME_MANIFEST = ROOT / "video_frames.jsonl"
TRANSCRIPTS = ROOT / "video_audio_transcripts.jsonl"
CAPTIONS = ROOT / "video_scene_captions.jsonl"
CHUNKS = ROOT / "video_chunks.jsonl"


def scene(video_id, seconds):
    if video_id == "V1":
        if seconds < 8:
            return "Outdoor campus approach: a multi-storey academic building, nearby sports fencing/ground, a purple directional sign, and a yellow temporary container are visible. The camera moves toward a covered outdoor seating area."
        if seconds < 24:
            return "The video continues beside the academic building and covered outdoor seating. Some extracted frames are rotated sideways because the camera changes orientation. No exact building or room name is verified from these frames."
        if seconds < 44:
            return "Covered campus walkway and courtyard seating beside an academic building; the camera moves past people and a small counter/shop frontage. Frames in this interval are rotated sideways in the source recording."
        return "Campus interior/service area: the camera passes a counter with people, then shows corridor/lift areas and a food or retail counter. Exact room and building names are not legible."
    if seconds < 4:
        return "Campus cafeteria/food-court interior with seating, food counters and menu boards."
    if seconds < 18:
        return "The camera leaves the food-court area and moves through a shaded landscaped campus walkway. Some extracted frames are rotated sideways as the camera turns."
    if seconds < 40:
        return "Outdoor campus walk past landscaped paths, academic buildings and open green/sports areas. A purple directional sign appears in this section; frame orientation varies during the walk."
    if seconds < 52:
        return "A purple campus wayfinding sign is shown near a landscaped path. Readable text includes ‘ENTRY/EXIT PATHWAY FOR SCHOOLS’ and names including Law, Commerce, Management, Liberal Arts, Media, Computer Science, Engineering, and AI & AC. Treat initials and arrows as sign transcription, not a verified route description."
    if seconds < 116:
        return "The camera proceeds outdoors across campus paths and open grounds toward sports facilities. Trees, landscaped areas and the sports ground are visible."
    if seconds < 132:
        return "Sports area with practice nets; a sign reads ‘CRICKET NETS’."
    return "The final section continues around the outdoor sports ground and cricket practice-net area."


def read_jsonl(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


frames = read_jsonl(FRAME_MANIFEST)
transcripts = read_jsonl(TRANSCRIPTS)
transcripts_by_video = {}
for row in transcripts:
    transcripts_by_video.setdefault(row["video_id"], []).append(row)

captions, chunks = [], []
for f in frames:
    vid = f["video_id"]
    t = float(f["timestamp_seconds"])
    cap = scene(vid, t)
    adjacent_speech = [
        tr for tr in transcripts_by_video.get(vid, [])
        if tr["start_seconds"] <= t + 4 and tr["end_seconds"] >= t - 2
    ]
    caption_row = {
        "id": f"{vid}_frame_{int(t):04d}",
        **f,
        "caption": cap,
        "caption_method": "reviewed_contact_sheet_scene_summary",
        "caption_confidence": "medium",
        "orientation_note": "Orientation varies in this source recording; use the frame image for visual inspection.",
    }
    captions.append(caption_row)
    speech = " ".join(tr["text"].strip() for tr in adjacent_speech if tr.get("text", "").strip())
    text = f"Campus video {vid} at {f['timestamp']} ({t:.1f} seconds). Scene: {cap}"
    if speech:
        text += f" Nearby automatic speech recognition transcript (unverified): {speech}"
    chunks.append({
        "id": caption_row["id"],
        "text": text,
        "metadata": {
            "source_type": "user_provided_video",
            "source_class": "campus_navigation_media",
            "source_video": f["source_path"],
            "video_id": vid,
            "start_seconds": t,
            "end_seconds": t + 2,
            "timestamp": f["timestamp"],
            "frame_path": f["frame_path"],
            "audio_path": f"dataset_sources/user_media/extracted_audio/{vid}_16k_mono.wav",
            "transcription_model": "openai/whisper-small" if adjacent_speech else None,
            "speech_text_is_automatic_and_unverified": bool(speech),
            "topic_tags": ["campus_facilities_navigation", "campus_video", "user_provided_media"],
        },
    })

# Preserve every ASR segment as its own retrievable row as well as including
# nearby speech in frame-time chunks. This avoids losing speech between samples.
for tr in transcripts:
    start = float(tr["start_seconds"])
    end = float(tr["end_seconds"])
    chunks.append({
        "id": tr["id"],
        "text": f"Campus video {tr['video_id']} speech at {start:.1f}-{end:.1f} seconds (automatic, unverified transcription): {tr['text']}",
        "metadata": {
            "source_type": "user_provided_video_transcript",
            "source_class": "campus_navigation_media",
            "source_video": tr["source_video"],
            "video_id": tr["video_id"],
            "start_seconds": start,
            "end_seconds": end,
            "audio_path": tr["audio_path"],
            "transcription_model": tr["transcription_model"],
            "language": tr.get("language"),
            "speech_text_is_automatic_and_unverified": True,
            "topic_tags": ["campus_facilities_navigation", "campus_video", "audio_transcript", "user_provided_media"],
        },
    })

for path, rows in ((CAPTIONS, captions), (CHUNKS, chunks)):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

summary = {
    "scene_caption_rows": len(captions),
    "rag_video_chunks": len(chunks),
    "transcript_segments": len(transcripts),
    "caption_file": str(CAPTIONS),
    "chunk_file": str(CHUNKS),
    "limitations": [
        "Scene captions are broad descriptions reviewed from sampled contact sheets, not a frame-by-frame visual model output.",
        "Whisper speech text is automatic and may be inaccurate; verify names, directions and academic facts before relying on it.",
        "A 2-second frame sampling interval can miss short-lived signs or events.",
    ],
}
(ROOT / "video_dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
