"""Some frames were filmed with the phone sideways, so people lie horizontally and the detector misses them.
For each 2-second block, test the middle frame rotated 90° both ways; if people are found much more confidently
when rotated, re-count the whole block rotated upright.  Usage: python fix_rotation.py <media_work_dir>"""
import json, os, shutil, sys, time
import torch
from PIL import Image, ImageDraw
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

WORK = sys.argv[1]
PEOPLE = os.path.join(WORK, "people")
BLOCK, THRESH = 8, 0.5                      # 8 frames = 2 s at 4 fps
torch.set_num_threads(16)
proc = RTDetrImageProcessor.from_pretrained("PekingU/rtdetr_r50vd")
model = RTDetrForObjectDetection.from_pretrained("PekingU/rtdetr_r50vd").eval()
PERSON = next(i for i, n in model.config.id2label.items() if n == "person")

def detect(imgs):
    with torch.inference_mode():
        out = model(**proc(images=imgs, return_tensors="pt"))
    res = proc.post_process_object_detection(out, threshold=THRESH, target_sizes=torch.tensor([im.size[::-1] for im in imgs]))
    return [([b.tolist() for b, l in zip(r["boxes"], r["labels"]) if int(l) == PERSON],
             [round(float(s), 2) for s, l in zip(r["scores"], r["labels"]) if int(l) == PERSON]) for r in res]

for video in ("V1", "V2"):
    path = os.path.join(PEOPLE, f"{video}_frames.json")
    backup = path.replace(".json", ".upright_only.json")
    if not os.path.exists(backup):
        shutil.copy(path, backup)
    frames = json.load(open(backup))
    t0, rotated, example = time.time(), [], None
    for s in range(0, len(frames), BLOCK):
        block = frames[s:s + BLOCK]
        mid = block[len(block) // 2]
        im = Image.open(mid["path"]).convert("RGB")
        base = sum(mid["scores"])
        tries = {angle: detect([im.rotate(angle, expand=True)])[0] for angle in (-90, 90)}   # -90 = clockwise
        angle, (boxes, scores) = max(tries.items(), key=lambda kv: sum(kv[1][1]))
        if sum(scores) > max(1.5 * base, base + 0.8):
            imgs = [Image.open(f["path"]).convert("RGB").rotate(angle, expand=True) for f in block]
            for f, (b, sc), img in zip(block, detect(imgs), imgs):
                f.update(boxes=b, scores=sc, count=len(b), rotated=angle, frame_h=img.size[1])
            rotated.append((block[0]["t"], block[-1]["t"], angle))
            if example is None or max(f["count"] for f in block) > example[1]["count"]:
                best = max(block, key=lambda f: f["count"])
                example = (imgs[block.index(best)], best)
    json.dump(frames, open(path, "w"))
    print(f"{video}: {len(rotated)} of {(len(frames) + BLOCK - 1) // BLOCK} blocks re-counted upright "
          f"({time.time() - t0:.0f}s): {[(a, b, ang) for a, b, ang in rotated]}")
    if example:
        img, f = example
        d = ImageDraw.Draw(img)
        for b, sc in zip(f["boxes"], f["scores"]):
            d.rectangle(b, outline=(255, 0, 0), width=4)
        d.text((12, 12), f"{video} t={f['t']}s rotated {f['rotated']} people={f['count']}", fill=(255, 255, 0))
        img.save(os.path.join(PEOPLE, f"check_rotated_{video}_{f['t']:06.2f}s_{f['count']}p.jpg"), quality=85)
