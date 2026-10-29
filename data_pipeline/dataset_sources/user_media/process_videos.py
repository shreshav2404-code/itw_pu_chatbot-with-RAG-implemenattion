"""Create compressed video copies, ASR audio, and sampled timestamped frames."""
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent.parent / "keshavs_input"     # original 4K V1.mp4 / V2.mp4 go here
FFMPEG = Path(shutil.which("ffmpeg") or "ffmpeg")
FFPROBE = Path(shutil.which("ffprobe") or "ffprobe")
VIDEO_OUT = HERE / "compressed_videos"
AUDIO_OUT = HERE / "extracted_audio"
FRAME_ROOT = HERE / "video_frames"
for folder in (VIDEO_OUT, AUDIO_OUT, FRAME_ROOT):
    folder.mkdir(parents=True, exist_ok=True)

inventory = []
frames = []
for name in ("V1.mp4", "V2.mp4"):
    source = INPUT / name
    if not source.exists():
        continue
    probe = json.loads(subprocess.check_output([
        str(FFPROBE), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)
    ], text=True))
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(probe.get("format", {}).get("duration", 0))
    compressed = VIDEO_OUT / f"{source.stem}_1080p.mp4"
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(source), "-vf", "scale='min(1920,iw)':-2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(compressed)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    audio_path = None
    if audio:
        audio_path = AUDIO_OUT / f"{source.stem}_16k_mono.wav"
        subprocess.run([
            str(FFMPEG), "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(audio_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    frame_dir = FRAME_ROOT / source.stem
    frame_dir.mkdir(parents=True, exist_ok=True)
    pattern = frame_dir / "frame_%04d.jpg"
    subprocess.run([
        str(FFMPEG), "-y", "-i", str(source), "-vf", "fps=0.5,scale='min(2560,iw)':-2",
        "-q:v", "2", str(pattern)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    extracted = sorted(frame_dir.glob("frame_*.jpg"))
    for i, frame_path in enumerate(extracted):
        ts = i * 2.0
        frames.append({
            "video_id": source.stem,
            "source_path": f"keshavs_input/{source.name}",
            "timestamp_seconds": ts,
            "timestamp": f"{int(ts // 60):02d}:{int(ts % 60):02d}",
            "frame_path": str(frame_path.relative_to(HERE.parent.parent)).replace("\\", "/"),
            "frame_width": 2560 if int(video.get("width", 0)) > 2560 else int(video.get("width", 0)),
            "sample_fps": 0.5,
        })
    inventory.append({
        "video_id": source.stem,
        "source_path": str(source),
        "source_bytes": source.stat().st_size,
        "duration_seconds": duration,
        "source_video_codec": video.get("codec_name"),
        "source_width": video.get("width"),
        "source_height": video.get("height"),
        "source_frame_rate": video.get("avg_frame_rate"),
        "source_audio_codec": audio.get("codec_name") if audio else None,
        "source_audio_sample_rate": audio.get("sample_rate") if audio else None,
        "compressed_path": str(compressed.relative_to(HERE.parent.parent)).replace("\\", "/"),
        "compressed_bytes": compressed.stat().st_size,
        "compressed_video_codec": "h264",
        "compressed_height_limit": 1080,
        "audio_wav_path": str(audio_path.relative_to(HERE.parent.parent)).replace("\\", "/") if audio_path else None,
        "audio_wav_bytes": audio_path.stat().st_size if audio_path else 0,
        "frame_count_sampled": len(extracted),
        "frame_interval_seconds": 2,
        "frame_directory": str(frame_dir.relative_to(HERE.parent.parent)).replace("\\", "/"),
        "original_preserved": True,
    })

(HERE / "video_inventory.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in inventory), encoding="utf-8")
(HERE / "video_frames.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in frames), encoding="utf-8")
summary = {
    "videos_processed": len(inventory),
    "source_bytes": sum(r["source_bytes"] for r in inventory),
    "compressed_bytes": sum(r["compressed_bytes"] for r in inventory),
    "frames_sampled": len(frames),
    "frame_interval_seconds": 2,
    "audio_tracks_extracted": sum(bool(r["audio_wav_path"]) for r in inventory),
    "inventory": "video_inventory.jsonl",
    "frames_manifest": "video_frames.jsonl",
    "source_files_preserved": True,
}
(HERE / "video_processing_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
