import json, logging, re, shutil
from pathlib import Path
from pypdf import PdfReader

logging.getLogger('pypdf').setLevel(logging.ERROR)
base=Path(__file__).resolve().parent
source=base/'keshavs_input'/'680f36b2a7f201745827506.pdf'
out=base/'dataset_sources'/'user_pdf'
out.mkdir(parents=True,exist_ok=True)
copy=out/source.name
shutil.copy2(source,copy)
reader=PdfReader(str(source))
pages=[]; chunks=[]
for i,page in enumerate(reader.pages,1):
    text=re.sub(r'\s+',' ',page.extract_text() or '').strip()
    pages.append({'source_file':source.name,'source_path':str(copy),'page':i,'text':text})
    for j in range(0,len(text),1100):
        piece=text[j:j+1100]
        if piece.strip(): chunks.append({'id':f'userpdf-{i}-{j//1100}','text':piece,'metadata':{'source_type':'user_uploaded_pdf','source_file':source.name,'source_path':str(copy),'page':i,'chunk_index':j//1100}})
(out/'pages.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in pages),encoding='utf-8')
(out/'chunks.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in chunks),encoding='utf-8')
meta={'source_file':source.name,'original_path':str(source),'copy_path':str(copy),'bytes':source.stat().st_size,'pages':len(reader.pages),'metadata':{str(k):str(v) for k,v in (reader.metadata or {}).items()},'characters':sum(len(x['text']) for x in pages),'text_pages':sum(bool(x['text']) for x in pages),'rag_chunks':len(chunks)}
(out/'metadata.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
terms=['passing','pass mark','pass marks','minimum marks','make-up','make up','makeup','supplementary','backlog','repeat','re-examination','re-exam','attendance','fee','scholarship','financial assistance','launchpad','remedial','academic support','evaluation','assessment','credit']
matches=[]
for p in pages:
    found=[t for t in terms if t in p['text'].lower()]
    if found: matches.append({'page':p['page'],'terms':found,'excerpt':p['text'][:950]})
(out/'topic_matches.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in matches),encoding='utf-8')
print(json.dumps({**meta,'topic_match_pages':len(matches),'outputs':[str(out/'pages.jsonl'),str(out/'chunks.jsonl'),str(out/'topic_matches.jsonl')]},ensure_ascii=False,indent=2))
