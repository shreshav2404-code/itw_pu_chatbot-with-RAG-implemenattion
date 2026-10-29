"""Create high-quality compressed copies of images in keshavs_input."""
import json
from pathlib import Path
from PIL import Image, ImageOps, ImageSequence

BASE = Path(__file__).resolve().parents[2]
SOURCE = BASE / "keshavs_input"
OUT = Path(__file__).resolve().parent / "compressed"
MANIFEST = Path(__file__).resolve().parent / "image_processing_manifest.jsonl"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
MAX_EDGE = 3072
records, errors = [], []

def oriented(frame):
    return ImageOps.exif_transpose(frame)

for path in sorted(p for p in SOURCE.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS):
    rel = path.relative_to(SOURCE)
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(path) as image:
            original_size = path.stat().st_size
            original_dimensions = list(image.size)
            fmt = (image.format or path.suffix.lstrip(".")).upper()
            icc = image.info.get("icc_profile")
            count = getattr(image, "n_frames", 1)
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(image):
                frame = oriented(frame.copy())
                frame.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
                frames.append(frame)
                durations.append(frame.info.get("duration", image.info.get("duration", 100)))
            if not frames:
                raise ValueError("No image frames")
            save_args = {}
            if fmt in {"JPEG", "JPG"}:
                # Flatten only if the source unexpectedly has alpha; retain a
                # neutral white background instead of losing transparency.
                if frames[0].mode in {"RGBA", "LA"}:
                    rgba = frames[0].convert("RGBA")
                    background = Image.new("RGB", rgba.size, "white")
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    frames[0] = background
                else:
                    frames = [f.convert("RGB") for f in frames]
                save_args = {"quality": 88, "optimize": True, "progressive": True}
                if icc: save_args["icc_profile"] = icc
            elif fmt == "PNG":
                save_args = {"optimize": True, "compress_level": 9}
                if icc: save_args["icc_profile"] = icc
            elif fmt == "WEBP":
                save_args = {"quality": 88, "method": 6, "lossless": False}
                if icc: save_args["icc_profile"] = icc
            elif fmt == "GIF":
                save_args = {"save_all": count > 1, "optimize": True}
                if count > 1:
                    save_args["append_images"] = frames[1:]
                    save_args["duration"] = durations
                    save_args["loop"] = image.info.get("loop", 0)
            elif fmt in {"BMP", "TIFF", "TIF"}:
                # Convert losslessly into PNG so this copy is smaller and has
                # a widely supported format; never alter the source file.
                dest = dest.with_suffix(".png")
                dest.parent.mkdir(parents=True, exist_ok=True)
                save_args = {"optimize": True, "compress_level": 9}
                if icc: save_args["icc_profile"] = icc
            frames[0].save(dest, **save_args)
            final_dimensions = list(frames[0].size)
        records.append({
            "original_path": str(path.resolve()),
            "original_relative_path": str(rel).replace("\\", "/"),
            "derivative_relative_path": str(dest.relative_to(Path(__file__).resolve().parent)).replace("\\", "/"),
            "source_format": fmt,
            "derivative_format": dest.suffix.lstrip(".").upper(),
            "frame_count": count,
            "original_dimensions": original_dimensions,
            "derivative_dimensions": final_dimensions,
            "original_bytes": original_size,
            "derivative_bytes": dest.stat().st_size,
            "settings": {"max_edge_px": MAX_EDGE, "jpeg_quality": 88, "webp_quality": 88, "png_compression": "lossless optimize, level 9", "exif_orientation_applied": True, "icc_profile_preserved_when_supported": True}
        })
    except Exception as exc:
        errors.append({"original_path": str(path.resolve()), "error": repr(exc)})

MANIFEST.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
summary = {
    "image_files_found": len(records) + len(errors),
    "processed": len(records),
    "errors": errors,
    "original_bytes": sum(r["original_bytes"] for r in records),
    "derivative_bytes": sum(r["derivative_bytes"] for r in records),
    "saved_bytes": sum(r["original_bytes"] - r["derivative_bytes"] for r in records),
    "output_directory": str(OUT.resolve()),
    "manifest": str(MANIFEST.resolve()),
}
print(json.dumps(summary, indent=2))
