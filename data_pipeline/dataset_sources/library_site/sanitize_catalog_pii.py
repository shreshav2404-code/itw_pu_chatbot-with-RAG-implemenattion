"""Replace OPAC item detail page/chunk text with safe structured metadata."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
items=[json.loads(x) for x in (ROOT/'catalog_items.jsonl').open(encoding='utf-8')]
by_url={x.get('detail_url','').split('#')[0]:x for x in items if x.get('detail_url')}
def safe_summary(x):
    parts=[x.get('title','')]
    if x.get('author'):parts.append('By: '+x['author'])
    if x.get('isbn'):parts.append('ISBN: '+x['isbn'])
    if x.get('subjects'):parts.append('Subjects: '+', '.join(x['subjects']))
    if x.get('holdings'):
        holdings=[]
        for h in x['holdings']:
            bits=[h.get('Current library',''),h.get('Collection',''),h.get('Shelving location',''),h.get('Call number',''),h.get('Status','')]
            holdings.append(' / '.join(b for b in bits if b))
        parts.append('Holdings: '+'; '.join(holdings))
    return '. '.join(p for p in parts if p)

pages=ROOT/'pages.jsonl'; tmp=ROOT/'pages.jsonl.tmp'
with pages.open(encoding='utf-8') as src, tmp.open('w',encoding='utf-8') as dst:
    for line in src:
        p=json.loads(line)
        if p.get('category')=='catalog_record':
            b=p.get('url','').split('biblionumber=')[-1].split('&')[0].split('#')[0]
            item=next((x for x in items if x.get('biblionumber')==b),None)
            if item:p['text']=safe_summary(item)
        dst.write(json.dumps(p,ensure_ascii=False)+'\n')
tmp.replace(pages)

chunks=ROOT/'catalog_items_chunks.jsonl'
with chunks.open('w',encoding='utf-8') as dst:
    for item in items:
        dst.write(json.dumps({'id':f"catalog-{item['biblionumber']}-0",'text':safe_summary(item),'metadata':{'url':item.get('detail_url'),'title':item.get('title'),'category':'catalog_record','source_type':'catalog_item','chunk_index':0}},ensure_ascii=False)+'\n')
print(json.dumps({'catalog_pages_sanitized':len(by_url),'catalog_item_chunks':len(items),'patron_names_ids_barcodes_due_dates':'removed from item content'},ensure_ascii=False))
