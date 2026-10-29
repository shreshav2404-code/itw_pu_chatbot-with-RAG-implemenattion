import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
pages=[json.loads(line) for line in (ROOT/'pages.jsonl').open(encoding='utf-8')]
ext={}
for p in pages:
    for link in p.get('links',[]):
        u=link.get('url','')
        if not u.startswith('http://182.72.188.195/'):
            key=(u,link.get('text',''))
            ext[key]={'page_url':p['url'],'page_title':p.get('title',''),'text':link.get('text',''),'url':u}
with (ROOT/'external_links.jsonl').open('w',encoding='utf-8') as f:
    for item in ext.values():f.write(json.dumps(item,ensure_ascii=False)+'\n')
home=next((p for p in pages if p['url']=='http://182.72.188.195/'),None)
overview={
 'source':'Presidency University Library public Koha OPAC',
 'source_url':'http://182.72.188.195/',
 'catalog_features':['Search by title','Search by author','Search by subject','Search by ISBN','Search by ISSN','Search by series','Search by call number','Advanced search','Course reserves','Browse by hierarchy','Authority search','Tag cloud'],
 'library_filters':['All libraries','Engineering Library','Law Library','Library and Knowledge Resource Centre','Management Library'],
 'borrowing_privileges':[{'user_group':'Faculty Members','books':10,'period':'1 Month'},{'user_group':'Staff','books':2,'period':'1 Month'},{'user_group':'Research Scholars','books':5,'period':'1 Month'},{'user_group':'UG & PG Students','books':3,'period':'14 Days'}],
 'contact_email':'library.services@presidencyuniversity.in',
 'opening_hours':'No opening hours found in the crawled public OPAC pages.',
 'physical_wayfinding':'No building floor plan, room directory, or indoor route instructions found in the crawled public OPAC pages.',
 'e_resources_visible':['Subscribed databases','Open access databases','National initiatives','Research tools','Petroleum e-books','Remote access','IRINS faculty profiles'],
 'facts_source_page':home['url'] if home else None,
 'limitations':'The OPAC provides search/browse entry points and sample public item records. This crawl does not enumerate every bibliographic record or private patron data.'
}
(ROOT/'library_overview.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(pages),'external_links':len(ext),'overview':str(ROOT/'library_overview.json')},ensure_ascii=False))
