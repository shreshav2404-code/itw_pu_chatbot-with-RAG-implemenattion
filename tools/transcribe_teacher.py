"""Transcribe Teacher.m4a with Whisper large-v3-turbo (same model as the notebook), keeping timestamps."""
import json, sys, time
import av, numpy as np, torch
from transformers import pipeline

SRC, OUT = sys.argv[1], sys.argv[2]

def load_audio(src, sr=16_000):
    resampler, chunks = av.AudioResampler(format="flt", layout="mono", rate=sr), []
    with av.open(src) as container:
        for frame in container.decode(audio=0):
            chunks += [f.to_ndarray().reshape(-1) for f in resampler.resample(frame)]
    chunks += [f.to_ndarray().reshape(-1) for f in resampler.resample(None)]
    return np.concatenate(chunks)

torch.set_num_threads(12)
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device="cpu",
               dtype=torch.float32, chunk_length_s=30)
wav = load_audio(SRC)
t = time.time()
out = asr({"raw": wav, "sampling_rate": 16_000}, return_timestamps=True, batch_size=4)
print(f"transcribed {len(wav) / 16000:.0f}s in {time.time() - t:.0f}s")
segs = [{"start": c["timestamp"][0], "end": c["timestamp"][1], "text": c["text"].strip()} for c in out["chunks"]]
json.dump({"text": out["text"].strip(), "segments": segs, "model": "openai/whisper-large-v3-turbo",
           "duration": len(wav) / 16000}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(out["text"])
