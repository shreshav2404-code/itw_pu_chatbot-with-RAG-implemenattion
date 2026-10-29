"""Embed reviewed image captions for text-to-image retrieval in the prototype."""
import json
import os
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

HERE = Path(__file__).resolve().parent
ROWS = [json.loads(line) for line in (HERE / "image_captions.jsonl").open(encoding="utf-8")]
hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface" / "hub"))
snapshots = hub / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
models = sorted(snapshots.glob("*")) if snapshots.exists() else []
model_path = str(models[-1]) if models else "sentence-transformers/all-MiniLM-L6-v2"
model = SentenceTransformer(model_path, device="cpu")
texts = [row["caption_text"] for row in ROWS]
vectors = model.encode(texts, batch_size=16, normalize_embeddings=True,
                       convert_to_numpy=True, show_progress_bar=True)
np.save(HERE / "image_caption_embeddings.npy", vectors.astype("float32"))
with (HERE / "image_vector_metadata.jsonl").open("w", encoding="utf-8") as out:
    for i, row in enumerate(ROWS):
        out.write(json.dumps({
            "vector_row": i,
            "image_id": row["original_relative_path"],
            "local_path": f"dataset_sources/user_media/{row['derivative_relative_path']}",
            "caption": row["caption"],
            "visible_text": row["visible_text"],
            "tags": row["tags"],
            "source_class": row["source_class"],
        }, ensure_ascii=False) + "\n")
info = {
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "dimensions": int(vectors.shape[1]),
    "vectors": int(vectors.shape[0]),
    "normalized": True,
    "input": "caption_text from visually reviewed image_captions.jsonl",
    "retrieval_mode": "text-to-image-caption semantic retrieval; not raw-image embeddings",
    "matrix_file": "image_caption_embeddings.npy",
    "metadata_file": "image_vector_metadata.jsonl",
    "device": "cpu",
}
(HERE / "image_embedding_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print(json.dumps(info, indent=2))
