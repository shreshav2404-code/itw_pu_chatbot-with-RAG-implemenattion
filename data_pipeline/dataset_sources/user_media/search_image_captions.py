"""Find supplied photos by text against their normalized caption vectors."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("query", help="Text describing the campus place or photo")
parser.add_argument("--top-k", type=int, default=5)
args = parser.parse_args()
hub = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface" / "hub"))
snapshots = hub / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
models = sorted(snapshots.glob("*")) if snapshots.exists() else []
model = SentenceTransformer(str(models[-1]) if models else "sentence-transformers/all-MiniLM-L6-v2", device="cpu")
query = model.encode([args.query], normalize_embeddings=True, convert_to_numpy=True)[0]
vectors = np.load(HERE / "image_caption_embeddings.npy")
metadata = [json.loads(line) for line in (HERE / "image_vector_metadata.jsonl").open(encoding="utf-8")]
order = np.argsort(vectors @ query)[::-1][:max(1, args.top_k)]
print(json.dumps([{
    "score": float(vectors[i] @ query),
    "image_id": metadata[i]["image_id"],
    "local_path": metadata[i]["local_path"],
    "caption": metadata[i]["caption"],
    "visible_text": metadata[i]["visible_text"],
} for i in order], ensure_ascii=False, indent=2))
