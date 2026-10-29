import json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent/'dataset_sources'/'jspui'
items=[]; collections=Counter(); fields=Counter(); abstract_count=0; file_refs=0; makeup=[]; exams=[]
for line in (ROOT/'item_records.jsonl').open(encoding='utf-8'):
    try: r=json.loads(line)
    except Exception: continue
    items.append(r)
    path=' > '.join(r.get('collection_path',[]))
    if path: collections[path]+=1
    for m in r.get('metadata',[]): fields[m.get('field','')]+=1
    if r.get('abstract'): abstract_count+=1
    file_refs+=len(r.get('bitstreams',[]))
    hay=(r.get('title','')+' '+path+' '+' '.join(r.get('subjects',[]))).lower()
    if re.search(r'make.?up|makeup|re.?midterm',hay): makeup.append(r)
    if re.search(r'question paper|examination|mid.?term|end.?term|semester exam',hay): exams.append(r)
def light(r):
    return {'item_url':r.get('item_url'),'handle':r.get('handle'),'title':r.get('title'),'issue_date':r.get('issue_date'),'subjects':r.get('subjects',[]),'collection_path':r.get('collection_path',[]),'abstract':r.get('abstract',''),'bitstreams':r.get('bitstreams',[])}
(ROOT/'makeup_exam_items.jsonl').write_text(''.join(json.dumps(light(r),ensure_ascii=False)+'\n' for r in makeup),encoding='utf-8')
(ROOT/'exam_and_question_paper_items.jsonl').write_text(''.join(json.dumps(light(r),ensure_ascii=False)+'\n' for r in exams),encoding='utf-8')
(ROOT/'collection_counts.jsonl').write_text(''.join(json.dumps({'collection_path':k,'item_count':v},ensure_ascii=False)+'\n' for k,v in collections.most_common()),encoding='utf-8')
summary={'catalog_items':len(items),'metadata_records':len(items),'items_with_abstract':abstract_count,'bitstream_references':file_refs,'makeup_related_items':len(makeup),'exam_question_paper_related_items':len(exams),'collection_paths':len(collections),'top_collection_paths':[{'path':k,'item_count':v} for k,v in collections.most_common(100)],'metadata_field_counts':dict(fields),'files_not_downloaded':'Repository item pages state all rights reserved unless item says otherwise; these outputs keep source links and metadata only.'}
(ROOT/'item_content_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('top_collection_paths','metadata_field_counts')},ensure_ascii=False,indent=2))
