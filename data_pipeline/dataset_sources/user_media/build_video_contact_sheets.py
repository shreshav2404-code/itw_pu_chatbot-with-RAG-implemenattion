"""Make frame review sheets labelled with video IDs and timestamps."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROWS = [json.loads(line) for line in (HERE / "video_frames.jsonl").open(encoding="utf-8")]
OUT = HERE.parent.parent / "tmp" / "video_contact_sheets"
OUT.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()
tile_w, tile_h, label_h, cols, rows = 480, 320, 32, 4, 3
for start in range(0, len(ROWS), cols * rows):
    batch = ROWS[start:start + cols * rows]
    canvas = Image.new("RGB", (cols * tile_w, rows * (tile_h + label_h)), "white")
    draw = ImageDraw.Draw(canvas)
    for off, item in enumerate(batch):
        n = start + off
        x, y = (off % cols) * tile_w, (off // cols) * (tile_h + label_h)
        p = HERE.parent.parent / item["frame_path"]
        with Image.open(p) as source:
            im = ImageOps.contain(source.convert("RGB"), (tile_w - 10, tile_h - 10))
        canvas.paste(im, (x + (tile_w - im.width) // 2, y + (tile_h - im.height) // 2))
        draw.text((x + 5, y + tile_h + 4), f"{item['video_id']} {item['timestamp']}  {item['frame_path'].split('/')[-1]}", fill="black", font=font)
    canvas.save(OUT / f"sheet_{start // (cols * rows) + 1:02d}.jpg", "JPEG", quality=90, optimize=True)
print(json.dumps({"frames": len(ROWS), "sheets": (len(ROWS) + cols * rows - 1) // (cols * rows), "output": str(OUT)}, indent=2))
