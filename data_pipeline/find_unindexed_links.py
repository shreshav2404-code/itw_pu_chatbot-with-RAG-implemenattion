import json, re
from urllib.parse import urlparse, urlunparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent/'dataset'
norm=lambda u: urlunparse(urlparse(u)._replace(query='',fragment='')).rstrip('/')
known={norm(x.strip()) for x in (ROOT/'crawl_urls.txt').open(encoding='utf-8') if x.strip()}
extra=set()
for line in (ROOT/'pages.jsonl').open(encoding='utf-8'):
    try: p=json.loads(line)
    except Exception: continue
    for l in p.get('links',[]):
        u=l.get('url','')
        try: parsed=urlparse(u)
        except Exception: continue
        if parsed.hostname not in ('presidencyuniversity.in','www.presidencyuniversity.in') or norm(u) in known: continue
        if re.search(r'\.(pdf|docx?|xlsx?|pptx?|jpe?g|png|webp|svg|mp4|mp3|zip|css|js|woff2?)$',parsed.path,re.I): continue
        if any(c in u for c in ('$', '{','}')): continue
        extra.add(norm(u))
out=ROOT/'unindexed_first_party_pages.txt'
out.write_text('\n'.join(sorted(extra))+'\n',encoding='utf-8')
print(json.dumps({'unindexed_first_party_page_urls':len(extra),'output':str(out)}))
