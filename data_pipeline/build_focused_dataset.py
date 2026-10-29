"""Tag page/document passages for the user's priority RAG topics."""
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent/'dataset'
OUT=ROOT/'focused_chunks.jsonl'
RULES={
 'examinations_pass_makeup_year_back': re.compile(r'\b(examin|assessment|pass(?:ing)?|fail(?:ure|ing)?|backlog|make[ -]?up|supplementary|repeat|re-?register|year[ -]?back|arrear|revaluation|retake|minimum marks|attendance requirement)\b',re.I),
 'fees_financial_assistance': re.compile(r'\b(fee structure|tuition fee|fees?|financial assistance|scholarship|concession|instalment|installment|emi|loan|fee refund|fee waiver)\b',re.I),
 'programs_courses_curriculum': re.compile(r'\b(programme|program|course|curriculum|syllabus|credit|speciali[sz]ation|elective|degree|duration)\b',re.I),
 'academic_calendar_timetable': re.compile(r'\b(academic calendar|academic year|semester dates|commencement|term dates|timetable|time table|exam schedule|holiday)\b',re.I),
 'academic_student_support': re.compile(r'\b(academic support|learning and development|remedial|bridge course|mentoring|mentor|tutoring|helpdesk|student wellness|counselling|counseling|student support|writing centre|learning centre)\b',re.I),
 'launchpad_incubation': re.compile(r'\b(launch ?pad|incubat|entrepreneur|start-?up|presidency launchpad association|PLA)\b',re.I),
 'campus_facilities_navigation': re.compile(r'\b(campus map|floor plan|wayfinding|directions|route|building|floor|room number|laborator|laboratory|library|facility|facilities|hostel|transport|virtual tour|campus)\b',re.I),
}
def tags(text,meta):
    hits=[name for name,pattern in RULES.items() if pattern.search(text)]
    category=meta.get('category','')
    if category=='program' and 'programs_courses_curriculum' not in hits:hits.append('programs_courses_curriculum')
    if category=='academic_operations' and 'academic_calendar_timetable' not in hits:hits.append('academic_calendar_timetable')
    title=(meta.get('title') or '').lower()
    if any(x in title for x in ['examination','academic regulation','student handbook']):
        for topic in ['examinations_pass_makeup_year_back','academic_calendar_timetable']:
            if topic not in hits:hits.append(topic)
    return hits
count=0;topic_counts={k:0 for k in RULES}
with OUT.open('w',encoding='utf-8') as out:
    for file,kind in [(ROOT/'chunks.jsonl','webpage'),(ROOT/'document_chunks.jsonl','document'),(ROOT.parent/'dataset_sources'/'user_pdf'/'chunks.jsonl','user_provided_pdf'),(ROOT.parent/'dataset_sources'/'campus_map'/'chunks.jsonl','user_provided_campus_map'),(ROOT.parent/'dataset_sources'/'user_media'/'image_chunks.jsonl','user_provided_image_caption'),(ROOT.parent/'dataset_sources'/'user_media'/'video_chunks.jsonl','user_provided_video'),(ROOT.parent/'dataset_sources'/'user_media'/'student_interview_chunks.jsonl','student_interview'),(ROOT.parent/'dataset_sources'/'jspui'/'item_chunks.jsonl','repository_item_metadata'),(ROOT.parent/'dataset_sources'/'library_site'/'catalog_items_chunks.jsonl','library_catalog_metadata'),(ROOT.parent/'dataset_sources'/'campus_virtual_tour'/'chunks.jsonl','virtual_tour')]:
        if not file.exists(): continue
        for line in file.open(encoding='utf-8'):
            try: row=json.loads(line)
            except Exception: continue
            meta=row.get('metadata',{})
            rowtags=tags(row.get('text',''),meta)
            if kind=='student_interview':rowtags=['student_interview','audio_transcript']
            if kind=='user_provided_campus_map' and 'campus_facilities_navigation' not in rowtags:rowtags.append('campus_facilities_navigation')
            image_tags=meta.get('topic_tags',[]) if kind=='user_provided_image_caption' else []
            if kind=='user_provided_image_caption':rowtags=['campus_facilities_navigation']
            if kind=='user_provided_video':rowtags=['campus_facilities_navigation']
            if not rowtags:continue
            row['metadata']={**meta,'source_type':meta.get('source_type',kind),'topic_tags':rowtags,**({'image_tags':image_tags} if image_tags else {})}
            out.write(json.dumps(row,ensure_ascii=False)+'\n');count+=1
            for tag in rowtags:topic_counts[tag]=topic_counts.get(tag,0)+1
print(json.dumps({'focused_chunks':count,'topic_counts':topic_counts,'output':str(OUT)},indent=2))
