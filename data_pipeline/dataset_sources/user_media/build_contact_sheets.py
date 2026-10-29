"""Build small review sheets for the user-supplied campus photographs."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "compressed"
OUTPUT = Path(__file__).resolve().parents[2] / "tmp" / "user_media_contact_sheets"
OUTPUT.mkdir(parents=True, exist_ok=True)
files = sorted(p for p in SOURCE.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
font = ImageFont.load_default()
tile_w, tile_h, label_h = 480, 320, 32
cols, rows = 4, 3
index = []
for start in range(0, len(files), cols * rows):
    batch = files[start:start + cols * rows]
    canvas = Image.new("RGB", (cols * tile_w, rows * (tile_h + label_h)), "white")
    draw = ImageDraw.Draw(canvas)
    for offset, path in enumerate(batch):
        n = start + offset + 1
        x = (offset % cols) * tile_w
        y = (offset // cols) * (tile_h + label_h)
        rel = path.relative_to(SOURCE).as_posix()
        try:
            with Image.open(path) as source:
                im = ImageOps.contain(source.convert("RGB"), (tile_w - 12, tile_h - 12))
            canvas.paste(im, (x + (tile_w - im.width) // 2, y + (tile_h - im.height) // 2))
            draw.text((x + 5, y + tile_h + 4), f"{n:02d}  {rel[:58]}", fill="black", font=font)
        except Exception as exc:
            draw.text((x + 5, y + tile_h + 4), f"{n:02d} ERROR {rel[:45]} {exc}", fill="red", font=font)
        index.append({"index": n, "derivative_relative_path": f"compressed/{rel}"})
    out = OUTPUT / f"sheet_{start // (cols * rows) + 1:02d}.jpg"
    canvas.save(out, "JPEG", quality=90, optimize=True)
(OUTPUT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
print(json.dumps({"images": len(files), "sheets": (len(files) + cols * rows - 1) // (cols * rows), "output": str(OUTPUT)}, indent=2))
