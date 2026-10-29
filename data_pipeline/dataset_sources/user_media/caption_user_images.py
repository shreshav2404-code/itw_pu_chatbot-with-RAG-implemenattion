"""Create RAG-ready captions for the 80 supplied campus photos.

Captions are based on visual review of the compressed derivatives. Text is
transcribed only when legible; uploaded filenames are preserved as labels.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "image_processing_manifest.jsonl"
CAPTIONS = HERE / "image_captions.jsonl"
CHUNKS = HERE / "image_chunks.jsonl"

# basename -> (caption, confidently readable text in image, tags)
REVIEW = {
"admissionoffice.jpg": ("Covered ground-floor service and event area with a long public-facing counter, information displays and waiting chairs. The uploaded filename labels this as the admission office.", "International Teaching Week; Presidency University", ["admissions", "service_counter", "campus_building"]),
"auditorium.jpg": ("Exterior view of a large university building beside a landscaped path. The uploaded filename labels it auditorium; no auditorium sign is legible in this view.", "", ["auditorium_filename_label", "building_exterior"]),
"cafeteria.jpg": ("Indoor cafeteria or food-court seating area with tables, service counters and menu displays.", "", ["cafeteria", "food_court"]),
"canopy.jpg": ("Large covered entrance canopy with a steel roof, pedestrian approach and students walking through the entrance area.", "", ["entrance", "canopy", "wayfinding"]),
"cricket net.jpg": ("Outdoor cricket practice nets beside the sports ground; the net-side sign reads Cricket Nets.", "Cricket Nets", ["cricket", "sports_ground", "wayfinding"]),
"DSA.jpg": ("Tree-shaded outdoor seating and gathering area beside a campus walkway. DSA is retained as the uploaded filename label; its expansion is not confirmed.", "", ["outdoor_seating", "courtyard", "DSA_filename_label"]),
"engineering block.jpg": ("Multi-storey academic block photographed from the landscaped approach, with the covered entrance and student access area in view.", "", ["engineering_block_filename_label", "academic_building", "entrance"]),
"entrance.jpg": ("Tree-lined pedestrian approach through the campus grounds, with a paved path and seating along the route.", "", ["pathway", "campus_exterior", "wayfinding"]),
"fountain.jpg": ("Landscaped campus fountain with water jets, circular planting beds and a pedestrian plaza.", "", ["fountain", "landscape", "wayfinding"]),
"ground.jpg": ("Outdoor sports ground beside a netted cricket practice area, photographed from the field edge.", "", ["sports_ground", "cricket", "outdoor"]),
"IAO.jpg": ("Glass-fronted campus entrance and lobby under the main covered canopy. IAO is preserved as the uploaded filename label; the acronym is not expanded.", "", ["entrance", "canopy", "IAO_filename_label"]),
"IMG20261029103332.jpg": ("Covered university frontage with information stands, a display screen and rows of blue waiting chairs; an event information banner is visible.", "International Teaching Week; Presidency University", ["entrance", "event_display", "waiting_area"]),
"IMG20261029103333.jpg": ("Front-facing view of the covered campus information and service area, with event stands, a screen and waiting chairs.", "Presidency University", ["service_counter", "entrance", "waiting_area"]),
"IMG20261029103422.jpg": ("Upward view of the Office of the Registrar frontage and the School of Engineering sign on the same academic building.", "Office of the Registrar; School of Engineering", ["registrar", "school_of_engineering", "building_sign"]),
"IMG20261029103426.jpg": ("Campus frontage showing the Office of the Registrar and School of Engineering signs, an NVIDIA AI Centre of Excellence / School of Artificial Intelligence and Advanced Computing panel, and a freestanding campus map.", "Office of the Registrar; School of Engineering; NVIDIA AI Centre of Excellence; School of Artificial Intelligence and Advanced Computing; Presidency University", ["registrar", "school_of_engineering", "AI_centre", "campus_map", "wayfinding"]),
"IMG20261029103452.jpg": ("Busy covered entrance area beside the Office of the Registrar and School of Engineering frontage, with students and event displays.", "Office of the Registrar; School of Engineering", ["registrar", "school_of_engineering", "entrance"]),
"IMG20261029103453.jpg": ("Another view of the covered Registrar and School of Engineering entrance, with visitors, event displays and the public service area.", "Office of the Registrar; School of Engineering", ["registrar", "school_of_engineering", "entrance"]),
"IMG20261029103531.jpg": ("Long indoor corridor with a large H marker above the passage; students walk toward the far end. The image does not identify what H denotes.", "H", ["corridor", "H_marker", "wayfinding"]),
"IMG20261029103534.jpg": ("Second view down the same corridor, with the H marker overhead, noticeboards along the wall and a display screen at the end.", "H", ["corridor", "H_marker", "wayfinding"]),
"IMG20261029103647.jpg": ("Covered ground-floor service area beneath the Office of the Registrar sign, with a waiting and information counter.", "Office of the Registrar", ["registrar", "service_counter", "wayfinding"]),
"IMG20261029103649.jpg": ("Closer view of the Office of the Registrar entrance and public-facing counter under the covered frontage.", "Office of the Registrar", ["registrar", "service_counter", "wayfinding"]),
"IMG20261029103655.jpg": ("View from the campus walkway toward a covered academic-building entrance, with landscaping and visitors approaching.", "", ["pathway", "building_entrance", "wayfinding"]),
"IMG20261029103713.jpg": ("Wide view of the Registrar and School of Engineering frontage, including event displays, the covered approach and visitors.", "Office of the Registrar; School of Engineering", ["registrar", "school_of_engineering", "entrance"]),
"IMG20261029110108.jpg": ("Exterior campus view with the Presidency University name mounted on the building facade.", "Presidency University", ["university_sign", "building_exterior"]),
"IMG20261029110121.jpg": ("Academic building approach beside the large entrance canopy, photographed from the open campus plaza.", "", ["building_exterior", "canopy", "wayfinding"]),
"IMG20261029110154.jpg": ("Main entrance canopy and university facade, with the Presidency University name displayed on the wall.", "Presidency University", ["entrance", "canopy", "university_sign"]),
"IMG20261029110224.jpg": ("Covered entrance and pedestrian plaza photographed from the approach side; the canopy structure and campus frontage are prominent.", "", ["entrance", "canopy", "wayfinding"]),
"IMG20261029110228.jpg": ("Wide side view of the main entrance canopy, columns and adjoining university facade.", "", ["entrance", "canopy", "building_exterior"]),
"IMG20261029110248.jpg": ("Interior view beneath the large entrance canopy, showing roof structure, lobby glazing and the approach to the building.", "", ["entrance", "canopy", "lobby"]),
"IMG20261029110300.jpg": ("View from under the main canopy toward the university entrance and surrounding landscaping.", "", ["entrance", "canopy", "landscape"]),
"IMG20261029110304.jpg": ("Covered campus entrance with the university facade and landscaped grounds visible beyond the columns.", "", ["entrance", "canopy", "building_exterior"]),
"IMG20261029110404.jpg": ("Glass-fronted entrance area beneath the canopy, with event signage visible inside the lobby.", "Confluence", ["entrance", "event_signage", "canopy"]),
"IMG20261029110425.jpg": ("Lobby entrance with a prominent Confluence event banner; the banner includes the phrase Where Global Minds Meet.", "Confluence; Where Global Minds Meet", ["confluence_event", "entrance", "banner"]),
"IMG20261029110555.jpg": ("Canopy-side entrance area with a large blue information or service counter and event displays.", "", ["entrance", "service_counter", "canopy"]),
"IMG20261029110602.jpg": ("Closer view of the blue reception or information counter beneath the main entrance canopy.", "", ["service_counter", "entrance", "canopy"]),
"IMG20261029110843.jpg": ("Interior library reading and browsing area with bookshelves, tables and study seating.", "", ["library", "study_area", "bookshelves"]),
"IMG20261029110849.jpg": ("Library interior with shelving, a service desk and study tables.", "", ["library", "service_desk", "bookshelves"]),
"IMG20261029110858.jpg": ("Exterior view of a distinctive angular campus building from the landscaped approach; no building-name sign is readable.", "", ["building_exterior", "landscape"]),
"IMG20261029111044.jpg": ("Ground-floor side of a university building, seen past two trimmed shrubs and a paved approach.", "", ["building_exterior", "landscape", "pathway"]),
"IMG20261029111109.jpg": ("Spacious indoor lobby with tall white columns and a pink-framed doorway; no room name is legible.", "", ["lobby", "interior", "doorway"]),
"IMG20261029111239.jpg": ("Tree-shaded campus courtyard with people sitting and gathering beside the pedestrian route.", "", ["courtyard", "outdoor_seating", "wayfinding"]),
"IMG20261029111436.jpg": ("Academic-building entrance with steps, a campus map board beside the approach and students entering.", "Presidency University", ["entrance", "campus_map", "wayfinding"]),
"IMG20261029111438.jpg": ("Second view of the same building entrance and freestanding campus map board near the steps.", "Presidency University", ["entrance", "campus_map", "wayfinding"]),
"IMG20261029111607.jpg": ("Outdoor path between university buildings, with a sloping facade and boundary wall alongside the route.", "", ["pathway", "building_exterior", "wayfinding"]),
"IMG20261029111708.jpg": ("Exterior of a large angular campus building with deep entrance canopy and pink-framed ground-floor doorway; file sequence suggests the auditorium area but no auditorium sign is legible.", "", ["building_exterior", "canopy", "auditorium_sequence"]),
"IMG20261029111716.jpg": ("Closer exterior view of the angular building facade and covered entrance, photographed from below.", "", ["building_exterior", "entrance", "auditorium_sequence"]),
"IMG20261029111718.jpg": ("Side view of the same angular campus block and its covered ground-floor entrance.", "", ["building_exterior", "entrance", "auditorium_sequence"]),
"IMG20261029111922.jpg": ("Tall tropical plants beside a campus building wall and louvered window.", "", ["landscape", "building_exterior"]),
"IMG20261029111927.jpg": ("Outdoor seating area with tables and large umbrellas under trees beside the campus pathway.", "", ["outdoor_seating", "food_area", "landscape"]),
"IMG20261029111948.jpg": ("Indoor cafeteria seating with tables, a serving counter and student dining area.", "", ["cafeteria", "food_court"]),
"IMG20261029111954.jpg": ("Cafeteria counter and display area with menu boards and a queue barrier.", "", ["cafeteria", "food_counter", "menu_board"]),
"IMG20261029111959.jpg": ("Wide view of the campus food-court seating and vendor counters; the sign reads Foodcourt Flavours.", "Foodcourt Flavours", ["food_court", "cafeteria", "vendor_counter"]),
"IMG20261029112323.jpg": ("Shaded pedestrian walkway through landscaped campus gardens.", "", ["pathway", "landscape", "wayfinding"]),
"IMG20261029112352.jpg": ("Wide view of the landscaped fountain plaza with the main entrance canopy and academic block behind it.", "", ["fountain", "entrance", "landscape"]),
"IMG20261029112354.jpg": ("Fountain and planted plaza in front of the large covered university entrance.", "", ["fountain", "entrance", "landscape"]),
"IMG20261029112527.jpg": ("Outdoor sports practice area with cricket nets and a field-side seating area.", "", ["sports_ground", "cricket", "outdoor_seating"]),
"IMG20261029112529.jpg": ("Cricket practice nets and open sports field, photographed from the shaded edge of the ground.", "", ["sports_ground", "cricket"]),
"IMG20261029112538.jpg": ("Shaded side view of the netted cricket practice area with trees and campus buildings beyond.", "", ["sports_ground", "cricket", "landscape"]),
"IMG20261029112547.jpg": ("Students using the netted cricket practice ground beside the campus sports field.", "", ["sports_ground", "cricket"]),
"IMG20261029112707.jpg": ("Side of a multi-storey campus block next to the netted sports area and a temporary service container.", "", ["building_exterior", "sports_ground"]),
"IMG20261029112709.jpg": ("Wide exterior view of a multi-storey academic building with the cricket-net area alongside it.", "", ["building_exterior", "sports_ground", "cricket"]),
"IMG20261029112715.jpg": ("Courtyard-side view of the campus block with outdoor seating and landscaped plants.", "", ["courtyard", "building_exterior", "outdoor_seating"]),
"IMG20261029112725.jpg": ("Umbrella-covered outdoor tables and seating beneath trees in a campus courtyard.", "", ["outdoor_seating", "courtyard", "landscape"]),
"IMG20261029112830.jpg": ("Ground-floor corridor with noticeboards and people gathered near a campus service or display area.", "", ["corridor", "noticeboards", "service_area"]),
"IMG20261029112840.jpg": ("Stationery shop counter inside a campus corridor, with supplies on display and students at the counter.", "", ["stationery_shop", "service_counter", "wayfinding"]),
"IMG_5f9db504-3e1f-4588-9727-eec768a3965d.jpg": ("Presidency University entrance sign set behind landscaped shrubs and a paved approach.", "Presidency University", ["main_entrance", "university_sign", "wayfinding"]),
"IMG_a20b9107-49d0-4c63-82c2-fb6b5ee5db87.webp": ("Tiered lecture room with rows of students facing the front; the room layout is suitable for classroom teaching.", "", ["classroom", "lecture_hall"]),
"IOA.jpg": ("Main covered entrance and lobby with a Confluence event banner visible through the glass; IOA is retained as the uploaded filename label.", "Confluence", ["entrance", "event_banner", "IOA_filename_label"]),
"lab.jpg": ("Computer or study laboratory with rows of individual workstations separated by colored desk dividers.", "", ["laboratory", "computer_lab", "study_area"]),
"lawn.jpg": ("Open campus lawn and sports field with a paved perimeter and trees in the distance.", "", ["lawn", "sports_ground", "outdoor"]),
"logo.jpg": ("Presidency University name and emblem mounted on an exterior wall beside the main covered entrance.", "Presidency University", ["university_sign", "entrance", "wayfinding"]),
"management library.jpg": ("Management library interior with book stacks, reading tables and study seating.", "", ["library", "management_library", "bookshelves"]),
"MBA class room.jpg": ("Tiered MBA classroom with students seated facing the front of the teaching space.", "", ["classroom", "MBA", "lecture_hall"]),
"office of registration.jpg": ("Registrar or registration service counter beneath the campus building frontage, photographed with the Office of the Registrar above.", "Office of the Registrar", ["registrar", "registration", "service_counter"]),
"OIA.jpg": ("Main covered entrance with a blue reception or information counter and landscaped foreground; OIA is preserved as the uploaded filename label.", "", ["entrance", "service_counter", "OIA_filename_label"]),
"school of engineering.jpg": ("School of Engineering frontage with public service counters, blue waiting chairs and the covered campus approach.", "School of Engineering", ["school_of_engineering", "entrance", "service_counter"]),
"SOE class room.png": ("Teaching session in a tiered School of Engineering classroom, with an instructor and students seated at desks.", "", ["school_of_engineering", "classroom", "lecture_hall"]),
"SOE library.jpg": ("School of Engineering library entrance and adjoining reading area, with blue carpet and room signs near the doorway.", "", ["school_of_engineering", "library", "wayfinding"]),
"stationary.jpg": ("Campus stationery shop with supplies displayed at the counter and students making purchases; filename spelling is preserved.", "", ["stationery_shop", "service_counter"]),
"University entrance.jpg": ("Main university gate with the Presidency University name mounted above the entrance drive.", "Presidency University", ["main_entrance", "university_sign", "wayfinding"]),
}

manifest = [json.loads(line) for line in INPUT.open(encoding="utf-8")]
captions, chunks = [], []
for asset in manifest:
    name = Path(asset["original_relative_path"]).name
    if name not in REVIEW:
        raise ValueError(f"No reviewed caption for {name}")
    caption, visible_text, tags = REVIEW[name]
    caption_text = f"{name}. {caption}"
    if visible_text:
        caption_text += f" Visible text: {visible_text}."
    row = {
        **asset,
        "title": name,
        "caption": caption,
        "visible_text": visible_text,
        "tags": tags,
        "caption_method": "visual_review",
        "caption_notes": "Descriptions are based on visual inspection; only clearly legible sign text is transcribed. Filename labels are not assumed to be official room names unless the image also shows the sign.",
        "source_type": "user_provided_image",
        "source_class": "user_provided_unverified",
        "caption_text": caption_text,
    }
    captions.append(row)
    chunks.append({
        "id": f"image-{asset['original_relative_path'].replace('/', '_').replace(' ', '_')}",
        "text": caption_text,
        "metadata": {
            "title": name,
            "local_path": f"dataset_sources/user_media/{asset['derivative_relative_path']}",
            "original_path": asset["original_relative_path"],
            "original_absolute_path": asset["original_path"],
            "source_type": "user_provided_image_caption",
            "source_class": "user_provided_unverified",
            "topic_tags": tags,
            "visible_text": visible_text,
            "caption_method": "visual_review",
        },
    })

if len(captions) != len(REVIEW):
    missing = sorted(set(REVIEW) - {Path(x["original_relative_path"]).name for x in manifest})
    if missing:
        raise ValueError(f"Captions not present in current input: {missing}")
CAPTIONS.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in captions), encoding="utf-8")
CHUNKS.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in chunks), encoding="utf-8")
print(json.dumps({"images_captioned": len(captions), "caption_chunks": len(chunks),
                  "output": str(CAPTIONS), "chunks_output": str(CHUNKS)}, indent=2))
