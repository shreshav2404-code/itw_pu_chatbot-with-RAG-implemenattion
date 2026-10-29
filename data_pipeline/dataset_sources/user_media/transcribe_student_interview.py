"""Transcribe the user-provided student interview into timestamped RAG rows."""
import json
import wave
from pathlib import Path

import numpy as np
from transformers import pipeline

HERE = Path(__file__).resolve().parent
INPUT = HERE / "extracted_audio" / "student_interview_16k_mono.wav"
MODEL = "openai/whisper-small"

with wave.open(str(INPUT), "rb") as wav:
    sample_rate = wav.getframerate()
    channels = wav.getnchannels()
    width = wav.getsampwidth()
    raw = wav.readframes(wav.getnframes())
if channels != 1 or width != 2:
    raise ValueError("Expected 16-bit mono PCM WAV")

audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
asr = pipeline("automatic-speech-recognition", model=MODEL, device=-1)
result = asr(
    {"array": audio, "sampling_rate": sample_rate},
    return_timestamps=True,
    generate_kwargs={"task": "transcribe"},
)

chunks = result.get("chunks") or []
duration = len(audio) / sample_rate
rows = []
if chunks:
    for i, chunk in enumerate(chunks):
        start, end = chunk.get("timestamp") or (None, None)
        rows.append({
            "id": f"student_interview-seg-{i:04d}",
            "source_type": "user_provided_audio_transcript",
            "source_audio": "keshavs_input/Interview student.m4a",
            "audio_path": "dataset_sources/user_media/extracted_audio/student_interview_16k_mono.wav",
            "start_seconds": start,
            "end_seconds": end,
            "text": (chunk.get("text") or "").strip(),
            "language": result.get("language"),
            "transcription_model": MODEL,
            "transcription_status": "automatic_unverified",
        })
elif (result.get("text") or "").strip():
    rows.append({
        "id": "student_interview-seg-0000",
        "source_type": "user_provided_audio_transcript",
        "source_audio": "keshavs_input/Interview student.m4a",
        "audio_path": "dataset_sources/user_media/extracted_audio/student_interview_16k_mono.wav",
        "start_seconds": 0.0,
        "end_seconds": duration,
        "text": result["text"].strip(),
        "language": result.get("language"),
        "transcription_model": MODEL,
        "transcription_status": "automatic_unverified",
    })

transcript_path = HERE / "student_interview_transcript.jsonl"
transcript_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
rag_rows = [{
    "id": row["id"],
    "text": f"User-provided student interview speech at {row['start_seconds']}-{row['end_seconds']} seconds (automatic, unverified transcription): {row['text']}",
    "metadata": {
        **row,
        "source_type": "user_provided_audio_transcript",
        "source_class": "student_interview",
        "topic_tags": ["student_interview", "user_provided_media", "audio_transcript"],
    },
} for row in rows if row.get("text")]
chunks_path = HERE / "student_interview_chunks.jsonl"
chunks_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rag_rows), encoding="utf-8")
summary = {
    "source_audio": "keshavs_input/Interview student.m4a",
    "source_duration_seconds": round(duration, 2),
    "sample_rate_hz": sample_rate,
    "channels": channels,
    "transcription_model": MODEL,
    "transcript_segments": len(rows),
    "rag_chunks": len(rag_rows),
    "transcript_file": str(transcript_path),
    "chunk_file": str(chunks_path),
    "limitations": ["ASR output is automatic and unverified; check student names, quotations and any factual claim against the recording before reuse."],
}
(HERE / "student_interview_processing_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({**summary, "text_preview": (result.get("text") or "")[:600]}, ensure_ascii=False, indent=2))
