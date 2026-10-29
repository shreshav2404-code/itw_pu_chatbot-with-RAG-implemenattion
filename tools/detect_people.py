"""Count people in V1/V2 frames (4 fps) with RT-DETR, track them across frames for a 'different people' estimate,
and save annotated frames for a visual check.  Usage: python detect_people.py <frames_root> <out_dir>"""
import collections, glob, json, os, sys, time
import torch
from PIL import Image, ImageDraw
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

FRAMES, OUT = sys.argv[1], sys.argv[2]
FPS, THRESH, BATCH = 4, 0.5, 8
os.makedirs(OUT, exist_ok=True)
torch.set_num_threads(16)

proc = RTDetrImageProcessor.from_pretrained("PekingU/rtdetr_r50vd")
model = RTDetrForObjectDetection.from_pretrained("PekingU/rtdetr_r50vd").eval()
PERSON = next(i for i, name in model.config.id2label.items() if name == "person")
VEHICLES = {i: name for i, name in model.config.id2label.items()
            if name in ("bicycle", "car", "motorcycle", "bus", "truck")}


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def track(frames, iou_min=0.25, max_age=4, min_hits=3):
    """Greedy IoU tracker. A track counts as a person once seen in >= min_hits frames (~0.75 s)."""
    tracks, next_id, confirmed = [], 0, set()
    for f in frames:
        dets = f["boxes"]
        pairs = sorted(((iou(t["box"], d), ti, di) for ti, t in enumerate(tracks) for di, d in enumerate(dets)),
                       reverse=True)
        used_t, used_d = set(), set()
        for score, ti, di in pairs:
            if score < iou_min or ti in used_t or di in used_d:
                continue
            used_t.add(ti); used_d.add(di)
            tracks[ti].update(box=dets[di], hits=tracks[ti]["hits"] + 1, misses=0)
            if tracks[ti]["hits"] >= min_hits:
                confirmed.add(tracks[ti]["id"])
        for ti, t in enumerate(tracks):
            if ti not in used_t:
                t["misses"] += 1
        tracks = [t for t in tracks if t["misses"] <= max_age]
        for di, d in enumerate(dets):
            if di not in used_d:
                tracks.append({"id": next_id, "box": d, "hits": 1, "misses": 0})
                next_id += 1
    return len(confirmed)


summary = {}
for video in sorted(os.listdir(FRAMES)):
    paths = sorted(glob.glob(os.path.join(FRAMES, video, "*.jpg")))
    frames, t0 = [], time.time()
    for start in range(0, len(paths), BATCH):
        imgs = [Image.open(p).convert("RGB") for p in paths[start:start + BATCH]]
        with torch.inference_mode():
            out = model(**proc(images=imgs, return_tensors="pt"))
        res = proc.post_process_object_detection(out, threshold=THRESH,
                                                 target_sizes=torch.tensor([im.size[::-1] for im in imgs]))
        for k, r in enumerate(res):
            dets = list(zip(r["boxes"], r["scores"], r["labels"]))
            keep = [(b.tolist(), float(s)) for b, s, l in dets if int(l) == PERSON]
            veh = [(b.tolist(), float(s), VEHICLES[int(l)]) for b, s, l in dets if int(l) in VEHICLES]
            frames.append({"t": round((start + k) / FPS, 2), "path": paths[start + k],
                           "count": len(keep), "boxes": [b for b, _ in keep], "scores": [round(s, 2) for _, s in keep],
                           "vehicles": dict(collections.Counter(n for _, _, n in veh)),
                           "vehicle_boxes": [b for b, _, _ in veh], "vehicle_labels": [n for _, _, n in veh]})
    counts = [f["count"] for f in frames]
    vcounts = [len(f["vehicle_boxes"]) for f in frames]
    best = max(frames, key=lambda f: f["count"])
    vbest = max(frames, key=lambda f: len(f["vehicle_boxes"]))
    by_type = {n: max(f["vehicles"].get(n, 0) for f in frames) for n in VEHICLES.values()}
    summary[video] = {
        "frames": len(frames), "duration_s": round(len(frames) / FPS, 1),
        "max_visible": best["count"], "max_at_s": best["t"],
        "mean_visible": round(sum(counts) / len(counts), 2),
        "pct_time_with_people": round(100 * sum(c > 0 for c in counts) / len(counts)),
        "different_people_estimate": track(frames),
        "max_vehicles_visible": len(vbest["vehicle_boxes"]), "max_vehicles_at_s": vbest["t"],
        "mean_vehicles_visible": round(sum(vcounts) / len(vcounts), 2),
        "pct_time_with_vehicles": round(100 * sum(c > 0 for c in vcounts) / len(vcounts)),
        "max_visible_by_vehicle_type": {n: c for n, c in by_type.items() if c},
        "different_vehicles_estimate": track([{"boxes": f["vehicle_boxes"]} for f in frames]),
        "seconds_per_frame_cpu": round((time.time() - t0) / len(frames), 2),
    }
    json.dump(frames, open(os.path.join(OUT, f"{video}_frames.json"), "w"))
    # annotated frames for checking: the busiest frame + 3 spread through the video
    picks = {id(best): best, id(vbest): vbest,
             **{id(frames[i]): frames[i] for i in (len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4)}}
    for f in picks.values():
        im = Image.open(f["path"]).convert("RGB")
        d = ImageDraw.Draw(im)
        for b, s in zip(f["boxes"], f["scores"]):                       # people: red
            d.rectangle(b, outline=(255, 0, 0), width=4)
            d.text((b[0] + 4, b[1] + 4), f"{s:.2f}", fill=(255, 255, 0))
        for b, n in zip(f["vehicle_boxes"], f["vehicle_labels"]):       # vehicles: blue
            d.rectangle(b, outline=(0, 120, 255), width=4)
            d.text((b[0] + 4, b[1] + 4), n, fill=(0, 200, 255))
        d.text((12, 12), f"{video} t={f['t']}s  people={f['count']}  vehicles={len(f['vehicle_boxes'])}", fill=(255, 255, 0))
        im.save(os.path.join(OUT, f"check_{video}_{f['t']:06.2f}s_{f['count']}p_{len(f['vehicle_boxes'])}v.jpg"), quality=85)
    print(video, json.dumps(summary[video]))

json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
