"""Reconcile the sitemap crawl with linked non-sitemap pages and write inventory counts."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent/'dataset'
pages=ROOT/'pages.jsonl'; urls=set(); cats=Counter(); title_hits=[]; line_count=0
for line in pages.open(encoding='utf-8'):
    try:p=json.loads(line)
    except Exception:continue
    line_count+=1;urls.add(p.get('url',''));cats[p.get('category','unknown')]+=1
    title=(p.get('title') or '').lower(); url=p.get('url','')
    if any(k in title+' '+url.lower() for k in ['academic-regulation','examination','academic-calendar','fee-refund','financial-assistance','scholarship','launchpad','incubation','course','program','time-table']):
        title_hits.append({'url':url,'title':p.get('title'),'category':p.get('category')})
def count_lines(file):
    try:
        with file.open('rb') as f:return sum(1 for _ in f)
    except FileNotFoundError:return 0
base=json.loads((ROOT/'crawl_summary.json').read_text(encoding='utf-8'))
extra=json.loads((ROOT/'unindexed_crawl_summary.json').read_text(encoding='utf-8'))
fail=[]
for fn in ['crawl_failures.json','unindexed_crawl_failures.json']:
    try:fail.extend(json.loads((ROOT/fn).read_text(encoding='utf-8')))
    except FileNotFoundError:pass
statuses=Counter(str(x.get('status',x.get('error','unknown'))) for x in fail)
manifest=[]
for line in (ROOT/'documents_manifest.jsonl').open(encoding='utf-8'):
    try:manifest.append(json.loads(line))
    except Exception:pass
summary={
 'origin':'https://presidencyuniversity.in',
 'generated_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
 'sitemap_url_count':base.get('sitemap_url_count'),
 'sitemap_html_pages':None,
 'additional_first_party_paths_discovered':extra.get('discovered_urls'),
 'additional_first_party_html_pages':extra.get('successful_html_pages'),
 'unique_html_pages_saved':len(urls),
 'page_records':line_count,
 'text_chunks':count_lines(ROOT/'chunks.jsonl'),
 'media_reference_records':count_lines(ROOT/'media_manifest.jsonl'),
 'document_references':len(manifest),
 'documents_downloaded':sum(x.get('download_status')=='downloaded' for x in manifest),
 'document_bytes_downloaded':sum(x.get('bytes',0) for x in manifest if x.get('download_status')=='downloaded'),
 'document_text_records':count_lines(ROOT/'documents_text.jsonl'),
 'document_chunks':count_lines(ROOT/'document_chunks.jsonl'),
 'focused_chunks':count_lines(ROOT/'focused_chunks.jsonl'),
 'failures_total':len(fail),
 'failure_statuses':dict(statuses),
 'categories':dict(cats),
 'media_tag_counts':{},
 'notes':['The full public sitemap was attempted, plus first-party page links not listed in the sitemap.', 'Date-sensitive pages such as fees, notices, calendars, and schedules should be refreshed regularly.', 'Images/audio/video are inventoried as source references; binaries are not bulk downloaded.']
}
sitemap_urls=set(x.strip() for x in (ROOT/'sitemap_urls.txt').open(encoding='utf-8') if x.strip())
summary['sitemap_html_pages']=sum(url in sitemap_urls for url in urls)
for line in (ROOT/'media_manifest.jsonl').open(encoding='utf-8'):
    try:m=json.loads(line);summary['media_tag_counts'][m.get('tag','unknown')]=summary['media_tag_counts'].get(m.get('tag','unknown'),0)+1
    except Exception:pass
(ROOT/'crawl_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(ROOT/'all_crawl_failures.json').write_text(json.dumps(fail,indent=2),encoding='utf-8')
(ROOT/'priority_pages.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in title_hits),encoding='utf-8')
all_urls=[];seen_urls=set()
for fn in ['sitemap_urls.txt','unindexed_first_party_pages.txt']:
    for line in (ROOT/fn).open(encoding='utf-8'):
        item=line.strip()
        if item and item not in seen_urls:all_urls.append(item);seen_urls.add(item)
(ROOT/'crawl_urls.txt').write_text('\n'.join(all_urls)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
