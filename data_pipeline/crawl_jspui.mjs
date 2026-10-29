import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const BASE = 'http://182.72.188.194:8080';
const ROOT = path.resolve('dataset_sources/jspui');
const CONCURRENCY = 8;
const delay = ms => new Promise(r => setTimeout(r, ms));
const decode = (s='') => s.replace(/&nbsp;|&#160;/gi,' ').replace(/&amp;/gi,'&').replace(/&quot;/gi,'"').replace(/&#39;|&apos;/gi,"'").replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&#x([0-9a-f]+);/gi,(_,x)=>String.fromCodePoint(parseInt(x,16))).replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(+n));
const clean = s => decode(s.replace(/<!--[\s\S]*?-->/g,' ').replace(/<(script|style|noscript|svg)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]+>/g,' ')).replace(/[\t\r\f\v ]+/g,' ').trim();
const attrs = tag => Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m=>[m[1].toLowerCase(),decode(m[2]??m[3]??m[4]??'')]));
const abs = u => { try { return new URL(u,BASE).href; } catch { return ''; } };
const write = (s,v) => new Promise((resolve,reject)=>s.write(JSON.stringify(v)+'\n','utf8',e=>e?reject(e):resolve()));
await fs.mkdir(ROOT,{recursive:true});

// Capture the root community/collection hierarchy and DSpace OAI-PMH set names.
const comm = await (await fetch(`${BASE}/jspui/community-list`)).text();
const hierarchy=[];
for(const m of comm.matchAll(/<a\b([^>]*)href=["']([^"']*\/handle\/123456789\/\d+)["']([^>]*)>([\s\S]*?)<\/a>/gi)){
 const link=abs(decode(m[2])); const label=clean(m[4]); hierarchy.push({url:link,label});
}
await fs.writeFile(path.join(ROOT,'communities_collections.jsonl'),[...new Map(hierarchy.map(x=>[x.url,x])).values()].map(x=>JSON.stringify(x)).join('\n')+'\n');
const setsXml = await (await fetch(`${BASE}/oai/request?verb=ListSets`)).text();
await fs.writeFile(path.join(ROOT,'oai_listsets_initial.xml'),setsXml);
const setRows=[...setsXml.matchAll(/<set>\s*<setSpec>([\s\S]*?)<\/setSpec>\s*<setName>([\s\S]*?)<\/setName>\s*<\/set>/g)].map(m=>({set_spec:clean(m[1]),name:clean(m[2])}));
await fs.writeFile(path.join(ROOT,'oai_sets.jsonl'),setRows.map(x=>JSON.stringify(x)).join('\n')+'\n');

// Use DSpace's public title browse index to enumerate all items (14k+ currently).
const browseBase = `${BASE}/jspui/browse?type=title&sort_by=1&order=ASC&rpp=1000&offset=`;
const first=await (await fetch(browseBase+'0')).text();
const total=Number((first.match(/of\s+([\d,]+)/i)||[])[1]?.replace(/,/g,''))||14145;
const offsets=[]; for(let n=0;n<total;n+=1000) offsets.push(n);
const items=new Map();
function parseBrowse(html){
 for(const row of html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)){
  const s=row[1]; const href=(s.match(/href=["']([^"']*\/jspui\/handle\/123456789\/\d+)["']/i)||[])[1]; if(!href) continue;
  const cells=[...s.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map(m=>clean(m[1]));
  items.set(abs(decode(href)),{item_url:abs(decode(href)),issue_date:cells[0]||'',title:cells[1]||'',authors:cells[2]||''});
 }
}
parseBrowse(first);
for(let i=1;i<offsets.length;i++){
 try{const html=await (await fetch(browseBase+offsets[i],{signal:AbortSignal.timeout(30000)})).text();parseBrowse(html)}catch(e){console.log(`browse offset ${offsets[i]} failed: ${e.message}`)}
 if(i%3===0) console.log(`Browse pages ${i+1}/${offsets.length}; listed items=${items.size}`);
 await delay(180);
}
await fs.writeFile(path.join(ROOT,'item_catalog.jsonl'),[...items.values()].map(x=>JSON.stringify(x)).join('\n')+'\n');

const detailsOut=fsSync.createWriteStream(path.join(ROOT,'item_records.jsonl'),{encoding:'utf8'});
const chunksOut=fsSync.createWriteStream(path.join(ROOT,'item_chunks.jsonl'),{encoding:'utf8'});
const filesOut=fsSync.createWriteStream(path.join(ROOT,'bitstreams_manifest.jsonl'),{encoding:'utf8'});
const failures=[];let cursor=0,done=0,chunkCount=0,fileCount=0;
const list=[...items.values()];
function parseDetails(html,url,basic){
 const title=clean((html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)||[])[1]||basic.title);
 const metadata=[];
 for(const row of html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)){
  const body=row[1];
  const label=(body.match(/<td\b[^>]*class=["'][^"']*metadataFieldLabel[^"']*["'][^>]*>([\s\S]*?)<\/td>/i)||[])[1];
  if(!label) continue;
  const val=(body.match(/<td\b[^>]*class=["'][^"']*metadataFieldValue[^"']*["'][^>]*>([\s\S]*?)<\/td>/i)||[])[1]||'';
  const field=clean(label).replace(/:\s*$/,''); const value=clean(val);
  if(field && value && value!=='-') metadata.push({field,value});
 }
 const breadcrumb=(html.match(/<ol\b[^>]*class=["'][^"']*breadcrumb[^"']*["'][^>]*>([\s\S]*?)<\/ol>/i)||[])[1]||'';
 const collection_path=[...breadcrumb.matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/gi)].map(m=>clean(m[1])).filter(Boolean);
 const bitstreams=[];
 for(const m of html.matchAll(/<a\b[^>]*href=["']([^"']*\/jspui\/bitstream\/[^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)){
  const href=decode(m[1]); const label=clean(m[2]);
  if(!bitstreams.some(b=>b.url===abs(href))) bitstreams.push({url:abs(href),filename:label});
 }
 const abstract=metadata.filter(x=>/abstract/i.test(x.field)).map(x=>x.value).join('\n');
 const subject=metadata.filter(x=>/subject/i.test(x.field)).map(x=>x.value);
 return {item_url:url,handle:url.match(/handle\/(123456789\/\d+)/)?.[1]||'',title,issue_date:basic.issue_date,browse_authors:basic.authors,collection_path,metadata,abstract,subjects:subject,bitstreams};
}
async function worker(){while(true){const i=cursor++;if(i>=list.length)return;const basic=list[i],url=basic.item_url+'?mode=full';try{
 const res=await fetch(url,{signal:AbortSignal.timeout(25000)});if(!res.ok)throw new Error(`HTTP ${res.status}`);const html=await res.text();const rec=parseDetails(html,basic.item_url,basic);await write(detailsOut,rec);done++;
 const text=[rec.title,...rec.collection_path,...rec.metadata.map(m=>`${m.field}: ${m.value}`)].filter(Boolean).join('\n');
 if(text.trim()){await write(chunksOut,{id:`item-${createHash('sha256').update(rec.item_url).digest('hex').slice(0,24)}`,text,metadata:{url:rec.item_url,title:rec.title,collection_path:rec.collection_path,handle:rec.handle,source_type:'repository_item_metadata'}});chunkCount++}
 for(const b of rec.bitstreams){await write(filesOut,{item_url:rec.item_url,item_title:rec.title,collection_path:rec.collection_path,...b});fileCount++}
 }catch(e){failures.push({url:basic.item_url,error:String(e?.message||e)})}
 if((i+1)%500===0)console.log(`Item details ${i+1}/${list.length}; success=${done}; fail=${failures.length}; bitstreams=${fileCount}`);await delay(120)}}
await Promise.all(Array.from({length:CONCURRENCY},worker));
for(const s of [detailsOut,chunksOut,filesOut])await new Promise(r=>s.end(r));
await fs.writeFile(path.join(ROOT,'item_failures.json'),JSON.stringify(failures,null,2));
const summary={source:BASE+'/jspui',dspace_version:'6.3',sitemap:'not accessible (advertised sitemap paths resolve to 404)',rest_api:'redirects to unreachable HTTPS port 8443',oai_pmh:{identify_available:true,list_sets_available:true,list_records:'noRecordsMatch for all advertised prefixes tested'},browse_total_reported:total,catalog_items:list.length,item_detail_pages:done,item_detail_failures:failures.length,bitstream_references:fileCount,item_metadata_chunks:chunkCount,communities_collections:hierarchy.length,oai_sets:setRows.length,content_note:'Item metadata and public bitstream URLs captured. Repository item files are copyrighted/all rights reserved unless their own item says otherwise; binary files were not bulk-downloaded.'};
await fs.writeFile(path.join(ROOT,'crawl_summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
