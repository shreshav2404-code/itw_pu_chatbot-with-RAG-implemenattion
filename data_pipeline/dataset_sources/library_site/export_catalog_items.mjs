import fs from 'node:fs/promises';
import path from 'node:path';
const ROOT=path.dirname(new URL(import.meta.url).pathname).replace(/^\//,'');
const BASE='http://182.72.188.195/cgi-bin/koha';
const decode=s=>(s||'').replace(/&nbsp;|&#160;/gi,' ').replace(/&amp;/gi,'&').replace(/&quot;/gi,'"').replace(/&#39;|&apos;/gi,"'").replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(+n)).replace(/&#x([\da-f]+);/gi,(_,n)=>String.fromCodePoint(parseInt(n,16)));
const strip=s=>decode(s.replace(/<(script|style|noscript|svg)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]+>/g,' ')).replace(/\s+/g,' ').trim();
const cell=s=>strip(s.replace(/<a\b[^>]*>[\s\S]*?<\/a>/gi,' '));

const reportUrl=`${BASE}/svc/report?id=180&public=1`;
const reportResponse=await fetch(reportUrl,{headers:{'User-Agent':'PresidencyLibraryRAGResearch/1.0 (public-site metadata indexing)'},signal:AbortSignal.timeout(20000)});
if(!reportResponse.ok)throw new Error(`Public report request failed: ${reportResponse.status}`);
const reportRows=await reportResponse.json();
const byId=new Map();
for(const row of reportRows){if(!Array.isArray(row)||!/^\d+$/.test(String(row[0])))continue;const [id,title,author,isbn,issues]=row;byId.set(String(id),{biblionumber:String(id),title:String(title||''),author:String(author||''),isbn:String(isbn||''),total_issues:Number(issues)||0,discovery_source:'public report 180 (most checked out)'});}
for(const line of (await fs.readFile(path.join(ROOT,'pages.jsonl'),'utf8')).split(/\r?\n/)){if(!line)continue;try{const p=JSON.parse(line);if(p.category!=='catalog_record')continue;const m=p.url.match(/[?&]biblionumber=(\d+)/i);if(m&&!byId.has(m[1]))byId.set(m[1],{biblionumber:m[1],title:p.title||'',author:'',isbn:'',discovery_source:'public item detail linked from OPAC'});}catch{}}

const rows=[];let detailFailures=0, cursor=0;
async function detailWorker(){while(cursor<byId.size){const item=[...byId.values()][cursor++];
 const url=`${BASE}/opac-detail.pl?biblionumber=${encodeURIComponent(item.biblionumber)}`;
 try{
  const res=await fetch(url,{headers:{'User-Agent':'PresidencyLibraryRAGResearch/1.0 (public-site metadata indexing)'},signal:AbortSignal.timeout(20000)});
  if(!res.ok)throw new Error(`HTTP ${res.status}`);
  const html=await res.text();
  const biblioblock=html.match(/<div\b[^>]*id=["']catalogue_detail_biblio["'][^>]*>([\s\S]*?)<\/div>\s*<div\b[^>]*class=["'](?:tab-content|tabs-container)/i)?.[1]||html;
  const title=strip((html.match(/<h1\b[^>]*property=["']name["'][^>]*>([\s\S]*?)<\/h1>/i)||[,''])[1])||item.title||strip((html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)||[,''])[1]);
  const authors=[...html.matchAll(/<span\b[^>]*property=["']author["'][^>]*>[\s\S]*?<span\b[^>]*property=["']name["'][^>]*>([\s\S]*?)<\/span>/gi)].map(m=>strip(m[1])).filter(Boolean);
  const detailIsbn=[...html.matchAll(/<span\b[^>]*property=["']isbn["'][^>]*>([\s\S]*?)<\/span>/gi)].map(m=>strip(m[1])).filter(Boolean);
  const subjects=[...html.matchAll(/<a\b[^>]*class=["'][^"']*\bsubject\b[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi)].map(m=>strip(m[1])).filter(Boolean);
  const table=(html.match(/<table\b[^>]*id=["']holdingst["'][^>]*>([\s\S]*?)<\/table>/i)||[,''])[1];
  const headers=[...table.matchAll(/<th\b[^>]*>([\s\S]*?)<\/th>/gi)].map(m=>strip(m[1])).filter(Boolean);
  const holdings=[];
  for(const tr of table.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)){
    const cells=[...tr[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map(m=>cell(m[1]));
    if(!cells.length)continue;
    const obj={};headers.forEach((h,i)=>{if(cells[i]&&!['Barcode','Date due'].includes(h))obj[h]=cells[i]});
    if(obj.Status)obj.Status=/^checked out/i.test(obj.Status)?'Checked out':obj.Status;
    if(obj['Call number'])obj['Call number']=obj['Call number'].replace(/\s*\(\s*Browse shelf.*$/i,'').trim();
    if(Object.values(obj).some(Boolean))holdings.push(obj);
  }
  rows.push({...item,title,authors:[...new Set(authors)],isbn:detailIsbn.join(' ; ')||item.isbn,subjects:[...new Set(subjects)],holdings,detail_url:url,detail_status:res.status});
 }catch(e){detailFailures++;rows.push({...item,authors:[],subjects:[],holdings:[],detail_url:url,detail_error:String(e?.message||e)});}
}}
await Promise.all(Array.from({length:4},detailWorker));
const output=path.join(ROOT,'catalog_items.jsonl');
await fs.writeFile(output,rows.map(r=>JSON.stringify(r)).join('\n')+'\n');
const summary={source:'Koha public OPAC at http://182.72.188.195',public_report_url:reportUrl,public_report_rows:reportRows.length,unique_public_records_exported:rows.length,records_with_item_holdings:rows.filter(r=>r.holdings?.length).length,records_with_subjects:rows.filter(r=>r.subjects?.length).length,detail_fetch_failures:detailFailures,fields:['biblionumber','title','author','authors','isbn','subjects','total_issues','holdings (item type, current library, collection, shelving location, call number, sanitized status)','source URLs'],privacy_note:'Patron names/IDs, barcodes, and due dates are omitted.',catalog_exhaustive:false,exhaustiveness_reason:'The OPAC browse hierarchy page reports that it is empty/not configured; free-text/ISBN/title search requests returned a 54-byte “No search result found” response; /api/v1/biblios requires authentication (401); the only confirmed anonymous record-list API is public report 180, which exposes a small most-checked-out sample. No public full-catalog export or pagination was exposed.',book_files_downloaded:0,output:'catalog_items.jsonl'};
await fs.writeFile(path.join(ROOT,'catalog_items_summary.json'),JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,2));
