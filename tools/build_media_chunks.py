"""Add teacher-recording chunks and V1/V2 people-count chunks to upload/pu_corpus.jsonl.gz (re-runnable).
Usage: python build_media_chunks.py <media_work_dir> <upload_dir>"""
import collections, gzip, json, os, re, sys

WORK, UPLOAD = sys.argv[1], sys.argv[2]
CORPUS = os.path.join(UPLOAD, "pu_corpus.jsonl.gz")
NEW_PREFIXES = ("teacher-", "people-")

def mmss(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"

with gzip.open(CORPUS, "rt", encoding="utf-8") as f:
    corpus = [json.loads(l) for l in f]
corpus = [r for r in corpus if not r["id"].startswith(NEW_PREFIXES)]          # re-runnable
new = []

# ------------------------------------------------------------------ teacher recording
tr = json.load(open(os.path.join(WORK, "teacher_transcript.json"), encoding="utf-8"))
FIXES = [(r"\bBTEC\b", "B.Tech"), (r"\battenants\b", "attendance"), (r"\blinways\b", "Linways"),
         (r"learning and developing department", "Learning and Development department"),
         (r"learning and development department", "Learning and Development department"),
         (r"\bmarks marks\b", "marks"), (r"\bone drive\b", "OneDrive"), (r"\bwhatsapp\b", "WhatsApp")]
def fix(text):
    for pat, rep in FIXES:
        text = re.sub(pat, rep, text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()

segs = tr["segments"]
# Whisper's 30 s windows overlapped once: segment 2 (28.3 -> 26.6 s) repeats the end of segment 1.
segs = [s for s in segs if s["end"] is None or s["end"] >= s["start"]]
# boundaries sit in the pauses between Whisper segments (40.0-41.48 s and the 127.02 s segment start)
windows = [(0, 41.0, "the department's services"), (41.0, 126.5, "frequent student questions, working hours and contact"),
           (126.5, tr["duration"], "where course documents are shared")]
for n, (a, b, topic) in enumerate(windows):
    text = " ".join(s["text"] for s in segs if a <= s["start"] < b)
    new.append({
        "id": f"teacher-seg-{n}",
        "text": (f"Teacher recording (Learning and Development department) at {mmss(a)}-{mmss(b)}, about {topic} "
                 f"(automatic transcription, lightly corrected, unverified): {fix(text)}"),
        "title": f"Teacher recording at {mmss(a)}", "source_class": "teacher_audio",
        "source_type": "user_provided_audio_transcript", "local_path": "keshavs_input/Teacher.m4a",
        "start_seconds": a, "end_seconds": round(b, 1),
        "topics": ["teacher_interview", "academic_student_support"], "unverified": True,
    })
new.append({
    "id": "teacher-summary",
    "text": ("Summary of a recorded interview with a teacher from the Learning and Development department, "
             "recorded by B.Tech students for this chatbot project (automatic transcription, unverified):\n"
             "- The Learning and Development department teaches students aptitude and soft skills and gives placement "
             "training to prepare for interviews, from the first to the seventh semester.\n"
             "- Questions students ask most in class: class timings, attendance and marks.\n"
             "- New students often struggle with how to plan their career across semesters 1 to 8.\n"
             "- Working hours: Monday to Friday, 8:50 to 4:15 (as spoken); the department also works on Saturdays. "
             "Faculty teach about 18 to 20 hours of classes per week.\n"
             "- How to contact the department: meet the staff directly in their cubicles, through the class WhatsApp "
             "groups, or by email.\n"
             "- Course materials: course details are uploaded on Linways (students download them with their Linways "
             "login); documents are also shared on WhatsApp and sometimes on OneDrive."),
    "title": "Teacher recording - Learning and Development department (summary)", "source_class": "teacher_audio",
    "source_type": "user_provided_audio_transcript", "local_path": "keshavs_input/Teacher.m4a",
    "start_seconds": 0, "end_seconds": round(tr["duration"], 1),
    "topics": ["teacher_interview", "academic_student_support", "placements"], "unverified": True,
})

# ------------------------------------------------------------------ people counts
FPS = 4                        # frames were extracted at 4 fps (1280x720; sideways blocks were re-counted upright)
# No "different people" total: a tracker on a moving phone camera re-counts the same people over and over
# (it said 213 for V2), so only per-moment counts are reported.

def load_people(video):
    """Per-frame people boxes, minus the camera holder's own hand/finger (boxes taller than 90% of the frame)."""
    frames = json.load(open(os.path.join(WORK, "people", f"{video}_frames.json")))
    for f in frames:
        h = f.get("frame_h", 720)
        keep = [(b, s) for b, s in zip(f["boxes"], f["scores"]) if b[3] - b[1] < 0.9 * h]
        f["boxes"], f["scores"], f["count"] = [b for b, _ in keep], [s for _, s in keep], len(keep)
    return frames

def people_stats(frames):
    counts = [f["count"] for f in frames]
    best = max(frames, key=lambda f: f["count"])
    return {"duration_s": round(len(frames) / FPS, 1), "max_visible": best["count"], "max_at_s": best["t"],
            "mean_visible": round(sum(counts) / len(counts), 2),
            "pct_time_with_people": round(100 * sum(c > 0 for c in counts) / len(counts))}

videos = sorted(f.split("_frames.json")[0] for f in os.listdir(os.path.join(WORK, "people")) if f.endswith("_frames.json"))
people_frames = {v: load_people(v) for v in videos}
summary = {v: people_stats(people_frames[v]) for v in videos}
print("people stats:", json.dumps(summary))
scenes = collections.defaultdict(list)            # existing scene captions, to say *where* the people are
for r in corpus:
    m = re.match(r"(V\d)_frame_", r["id"])
    if m and r.get("start_seconds") is not None:
        cap = re.search(r"Scene:\s*(.+?)(?:\s*Nearby automatic speech|$)", r["text"], re.S)
        if cap:
            scenes[m.group(1)].append((float(r["start_seconds"]), cap.group(1).strip()))

def scene_at(video, t):
    options = scenes.get(video)
    return min(options, key=lambda x: abs(x[0] - t))[1][:220] if options else ""

METHOD = ("Counted automatically with an RT-DETR person detector on 4 frames per second; people who are far away, "
          "hidden or blurred can be missed, so treat numbers as approximate.")

# Recording time from the phone's metadata (creation_time = end of recording, UTC); IST = UTC + 5:30
import datetime as dt
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
RECORDED_END_UTC = {"V1": "2026-10-29T05:58:06+00:00", "V2": "2026-10-29T05:56:24+00:00"}

def recorded(video, duration_s):
    end = dt.datetime.fromisoformat(RECORDED_END_UTC[video]).astimezone(IST)
    start = end - dt.timedelta(seconds=duration_s)
    fmt = lambda t: t.strftime("%I:%M %p").lstrip("0")
    return f"{start.strftime('%A %d %B %Y')}, {fmt(start)} to {fmt(end)} IST (late morning, weekday daytime)"

def crowd_level(mean, peak):
    """Plain-language foot-traffic level from people visible per moment."""
    if peak == 0:
        return "empty (no people seen)"
    if mean < 1:
        return "very light foot traffic (mostly empty, only occasional people)"
    if mean < 4:
        return "light foot traffic"
    if mean < 10:
        return "moderate foot traffic"
    return "busy / crowded"

overall = []
for video, s in summary.items():
    frames = people_frames[video]
    when = recorded(video, s["duration_s"])
    level = crowd_level(s["mean_visible"], s["max_visible"])
    overall.append((video, s, when, level))
    new.append({
        "id": f"people-{video}-summary",
        "text": (f"How many people / how much people traffic is in campus video {video}? Recorded {when}. "
                 f"Daytime foot traffic in this {s['duration_s']:.0f}-second user-provided campus video: {level}. "
                 f"At most {s['max_visible']} people are visible at the same time (at {mmss(s['max_at_s'])} into the video); "
                 f"on average about {s['mean_visible']:.1f} people are visible; people are visible in "
                 f"{s['pct_time_with_people']}% of the video. So at least {s['max_visible']} people appear in the video; "
                 f"more pass by over its full length, but the total number of different people cannot be counted "
                 f"reliably from a moving phone camera. {METHOD}"),
        "title": f"Campus video {video} - people count", "source_class": "user_video", "source_type": "people_count",
        "local_path": f"keshavs_input/{video}.mp4", "start_seconds": 0, "end_seconds": s["duration_s"],
        "topics": ["campus_video", "people_count", "people_traffic", "user_provided_media"], "unverified": True,
    })
    for a in range(0, int(s["duration_s"] + 0.999), 10):
        win = [f for f in frames if a <= f["t"] < a + 10]
        if not win:
            continue
        counts = [f["count"] for f in win]
        top = max(win, key=lambda f: f["count"])
        lo, hi = min(counts), max(counts)
        seen = f"{hi} {'person' if hi == 1 else 'people'}" if lo == hi else f"between {lo} and {hi} people"
        if hi == 0:
            seen = "no people"
        b = min(a + 10, s["duration_s"])
        new.append({
            "id": f"people-{video}-{a:03d}",
            "text": (f"Campus video {video} at {mmss(a)}-{mmss(b)} (recorded late morning on a weekday), people traffic: "
                     f"{seen} visible"
                     + (f" (most: {hi} at {mmss(top['t'])}; about {sum(counts) / len(counts):.1f} on average)" if hi else "")
                     + f". Scene: {scene_at(video, a)} {METHOD}"),
            "title": f"Campus video {video} at {mmss(a)} - people count", "source_class": "user_video",
            "source_type": "people_count", "local_path": f"keshavs_input/{video}.mp4",
            "start_seconds": a, "end_seconds": b,
            "topics": ["campus_video", "people_count", "people_traffic", "user_provided_media"], "unverified": True,
        })

parts = [f"video {v} ({when}): {level}, at most {s['max_visible']} people visible at once (at "
         f"{mmss(s['max_at_s'])}), about {s['mean_visible']:.1f} on average, people in view {s['pct_time_with_people']}% "
         f"of its {s['duration_s']:.0f} seconds" for v, s, when, level in overall]
new.append({
    "id": "people-all-videos",
    "text": ("How much people traffic / how crowded is the campus during the day? How many people are in the campus "
             "videos? Automatic people counts from two short user-recorded campus videos: " + "; ".join(parts) +
             ". Important: this is one snapshot of a few minutes "
             "on one weekday late morning along the filmed walkways and buildings; it does not show other times "
             f"(early morning, lunch hour, evenings, weekends, exam or event days) or other parts of campus. {METHOD}"),
    "title": "Campus daytime people traffic (videos V1 and V2)", "source_class": "user_video", "source_type": "people_count",
    "topics": ["campus_video", "people_count", "people_traffic", "user_provided_media"], "unverified": True,
})

# ------------------------------------------------------------------ write
final = corpus + new
with gzip.open(CORPUS, "wt", encoding="utf-8", compresslevel=6) as f:
    for r in final:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
stats_file = os.path.join(UPLOAD, "corpus_stats.json")
stats = json.load(open(stats_file)) if os.path.exists(stats_file) else {}
stats.update(records=len(final), by_source_class=dict(collections.Counter(r["source_class"] for r in final).most_common()),
             size_mb=round(os.path.getsize(CORPUS) / 1e6, 1), added_media_chunks=len(new))
json.dump(stats, open(stats_file, "w"), indent=2)
print(f"added {len(new)} chunks -> {len(final):,} total")
for r in new:
    print(f"\n[{r['id']}] {r['title']}\n  {r['text'][:400]}")
