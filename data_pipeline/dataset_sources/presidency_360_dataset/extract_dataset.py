from __future__ import annotations
import csv, json, re
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://www.immersivetourz.com/presidencyuniversity/"
OUT = Path(__file__).resolve().parent
IMAGES = OUT / "images"
IMAGES.mkdir(parents=True, exist_ok=True)

req = Request(BASE + "script_general.js?v=1751605676358", headers={"User-Agent": "Mozilla/5.0 (compatible; PUAssistDataset/1.0)"})
with urlopen(req, timeout=60) as response:
    script = response.read().decode("utf-8", errors="replace")
pattern = re.compile(r'"id":"(panorama_[A-F0-9_]+)","class":"Panorama","data":\{"label":"([^"]*)"\}')
scenes = pattern.findall(script)
if not scenes:
    raise RuntimeError("No scenes found; the tour manifest format may have changed")

rows = []
for i, (scene_id, label) in enumerate(scenes, start=1):
    asset_name = scene_id.removeprefix("panorama_")
    image_rel = f"images/{asset_name}.webp"
    image_url = f"{BASE}media/{scene_id}_t.webp"
    image_path = OUT / image_rel
    status = "downloaded"
    try:
        if not image_path.exists():
            img_req = Request(image_url, headers={"User-Agent": "Mozilla/5.0 (compatible; PUAssistDataset/1.0)"})
            with urlopen(img_req, timeout=30) as response:
                image_path.write_bytes(response.read())
        if image_path.stat().st_size < 100:
            raise ValueError("unexpectedly small image")
    except Exception as exc:
        status = f"download_failed: {exc}"
        image_rel = ""
    rows.append({
        "scene_index": i,
        "scene_id": scene_id,
        "label": label,
        "preview_file": image_rel,
        "preview_status": status,
        "preview_url": image_url,
        "tour_url": BASE + "index.html",
        "source_page": "https://presidencyuniversity.in/360-view/",
        "source_provider": "ImmersiveTourz",
    })
    if i % 20 == 0:
        print(f"processed {i}/{len(scenes)}")

# The tour manifest also exposes labels on scenes and interactive hotspots.
label_matches = re.findall(r'"label":"([^"\\]*(?:\\.[^"\\]*)*)"', script)
label_counts: dict[str, int] = {}
for raw_label in label_matches:
    try:
        label = json.loads('"' + raw_label + '"')
    except json.JSONDecodeError:
        continue
    label = re.sub(r"\\s+", " ", label).strip()
    if not label or re.match(r"^(?:GoTo|Button|Back$|back |Audio$|Text$|Collaps|Expand|---|[0-9]+$|footer_logo$|blue line$|Copy of)", label, re.I):
        continue
    label_counts[label] = label_counts.get(label, 0) + 1
scene_labels: dict[str, list[str]] = {}
for row in rows:
    scene_labels.setdefault(row["label"].casefold(), []).append(row["scene_id"])
info_rows = []
for label, count in sorted(label_counts.items(), key=lambda item: item[0].casefold()):
    info_rows.append({
        "label": label,
        "manifest_occurrences": count,
        "matching_scene_ids": scene_labels.get(label.casefold(), []),
        "information": f'The Presidency University 360 tour manifest uses the label "{label}".',
        "source_page": "https://presidencyuniversity.in/360-view/",
        "source_tour": BASE + "index.html",
        "source_provider": "ImmersiveTourz",
    })
(OUT / "tour_label_info.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in info_rows), encoding="utf-8")
with (OUT / "tour_label_info.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(info_rows[0].keys()))
    writer.writeheader()
    writer.writerows({**row, "matching_scene_ids": ";".join(row["matching_scene_ids"])} for row in info_rows)
# Preserve all panorama nodes, even those without outgoing links, and extract the tour's direct transitions.
scene_by_id = {row["scene_id"]: row for row in rows}
edge_pattern = re.compile(r'\{"data":\{"overlayID":"([^"]+)"\},(?:"backwardYaw":(-?[0-9.]+),)?"yaw":(-?[0-9.]+),"distance":(-?[0-9.]+),"panorama":"this\.(panorama_[A-F0-9_]+)","select":"[^"]*","class":"AdjacentPanorama"\}')
adjacency_pattern = re.compile(r'"adjacentPanoramas":\[(.*?)\],"id":"(panorama_[A-F0-9_]+)","class":"Panorama","data":\{"label":"([^"]*)"\}', re.S)
edges = []
for match in adjacency_pattern.finditer(script):
    source_id = match.group(2)
    for link in edge_pattern.finditer(match.group(1)):
        destination_id = link.group(5)
        edges.append({
            "from_scene_id": source_id,
            "from_label": scene_by_id.get(source_id, {}).get("label", ""),
            "to_scene_id": destination_id,
            "to_label": scene_by_id.get(destination_id, {}).get("label", ""),
            "overlay_id": link.group(1),
            "yaw": float(link.group(3)),
            "backward_yaw": float(link.group(2)) if link.group(2) is not None else None,
            "distance": float(link.group(4)),
            "source_page": "https://presidencyuniversity.in/360-view/",
            "source_tour": BASE + "index.html",
            "source_provider": "ImmersiveTourz",
        })
adjacency: dict[str, list[dict]] = {scene_id: [] for scene_id in scene_by_id}
for edge in edges:
    if edge["from_scene_id"] in adjacency:
        adjacency[edge["from_scene_id"]].append({"scene_id": edge["to_scene_id"], "label": edge["to_label"], "yaw": edge["yaw"], "distance": edge["distance"]})
nodes = [{"scene_id": row["scene_id"], "label": row["label"], "neighbors": adjacency[row["scene_id"]]} for row in rows]
(OUT / "navigation_graph.json").write_text(json.dumps({"nodes": nodes, "edges": edges, "angle_distance_units": "as published by tour; units not specified", "source_tour": BASE + "index.html"}, ensure_ascii=False, indent=2), encoding="utf-8")
with (OUT / "navigation_edges.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(edges[0].keys()))
    writer.writeheader()
    writer.writerows(edges)
with (OUT / "navigation_info.jsonl").open("w", encoding="utf-8") as f:
    for edge in edges:
        sentence = f'The 360 tour links {edge["from_label"] or edge["from_scene_id"]} directly to {edge["to_label"] or edge["to_scene_id"]}.'
        record = {**edge, "information": sentence}
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
water_fountain = next((row for row in rows if "water fountain area" in row["label"].casefold()), None)
annotation = {
    "annotation_type": "user_supplied_landmark",
    "label": "Water Fountain Area" if water_fountain else "fountain",
    "scene_id": water_fountain["scene_id"] if water_fountain else None,
    "information": "User identifies the middle part as the fountain.",
    "source": "user",
}
(OUT / "user_annotations.jsonl").write_text(json.dumps(annotation, ensure_ascii=False) + "\n", encoding="utf-8")
(OUT / "dataset.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
with (OUT / "dataset.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
(OUT / "README.md").write_text(f"""# Presidency University 360° Tour Dataset\n\nExtracted from the university's [360° view page](https://presidencyuniversity.in/360-view/) and its embedded [ImmersiveTourz virtual tour]({BASE}).\n\n- Scene records: {len(rows)}\n- Files: scene records (`dataset.csv`, `dataset.json`); tour labels (`tour_label_info.csv`, `tour_label_info.jsonl`); navigation graph (`navigation_graph.json`, `navigation_edges.csv`, `navigation_info.jsonl`); user landmark note (`user_annotations.jsonl`); and `images/` (preview thumbnails)\n- Scene records include provider IDs and labels, preview paths, and source links. The navigation files preserve direct scene-to-scene links and the provider's yaw/distance values; their units are unspecified. The label files preserve additional tour labels and matching scene IDs. The user annotation records the fountain landmark note and is separate from provider-supplied data.\n- `images/` contains preview thumbnails only. The tour's full panorama imagery is served as cube-map tiles at multiple resolutions and was not downloaded or reconstructed here.\n- Labels are copied from the public tour manifest; numeric labels are retained as published.\n- Run `python extract_dataset.py` to refresh the metadata and previews. Uses only the Python standard library.\n\nSource content belongs to Presidency University / ImmersiveTourz. This extraction preserves source attribution; check their terms before redistribution or model training.\n""", encoding="utf-8")
print(f"wrote {len(rows)} scenes; {sum(r['preview_status']=='downloaded' for r in rows)} previews to {OUT}")

