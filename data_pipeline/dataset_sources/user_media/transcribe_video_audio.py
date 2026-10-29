"""Transcribe extracted video audio into timestamped RAG passages."""
import json
import wave
from pathlib import Path
import numpy as np
from transformers import pipeline

HERE = Path(__file__).resolve().parent
MODEL = "openai/whisper-small"
INPUTS = sorted((HERE / "extracted_audio").glob("*_16k_mono.wav"))
asr = pipeline("automatic-speech-recognition", model=MODEL, device=-1)
records = []
for path in INPUTS:
    with wave.open(str(path), "rb") as wav:
        sample_rate = wav.getframerate()
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        raw = wav.readframes(wav.getnframes())
    if channels != 1 or sample_width != 2:
        raise ValueError(f"Expected mono 16-bit PCM WAV: {path}")
    audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    result = asr({"array": audio, "sampling_rate": sample_rate},
                 return_timestamps=True,
                 generate_kwargs={"task": "transcribe"})
    chunks = result.get("chunks") or []
    if chunks:
        for i, chunk in enumerate(chunks):
            start, end = chunk.get("timestamp") or (None, None)
            records.append({
                "id": f"{path.stem}-seg-{i:04d}",
                "video_id": path.stem.replace("_16k_mono", ""),
                "source_video": f"keshavs_input/{path.stem.replace('_16k_mono', '')}.mp4",
                "audio_path": str(path.relative_to(HERE.parent.parent)).replace("\\", "/"),
                "start_seconds": start,
                "end_seconds": end,
                "text": (chunk.get("text") or "").strip(),
                "language": result.get("language"),
                "transcription_model": MODEL,
                "source_type": "video_audio_transcript",
            })
    elif (result.get("text") or "").strip():
        records.append({
            "id": f"{path.stem}-seg-0000",
            "video_id": path.stem.replace("_16k_mono", ""),
            "source_video": f"keshavs_input/{path.stem.replace('_16k_mono', '')}.mp4",
            "audio_path": str(path.relative_to(HERE.parent.parent)).replace("\\", "/"),
            "start_seconds": 0,
            "end_seconds": None,
            "text": result["text"].strip(),
            "language": result.get("language"),
            "transcription_model": MODEL,
            "source_type": "video_audio_transcript",
        })
    print(json.dumps({"audio": path.name, "transcribed_segments": len(chunks),
                      "text_preview": (result.get("text") or "")[:350]}, ensure_ascii=False), flush=True)

out = HERE / "video_audio_transcripts.jsonl"
out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
print(json.dumps({"model": MODEL, "audio_files": len(INPUTS), "transcript_records": len(records), "output": str(out)}, indent=2))
