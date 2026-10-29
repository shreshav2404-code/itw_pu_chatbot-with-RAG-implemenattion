import fs from 'node:fs/promises';
import path from 'node:path';

const OUT=path.resolve('dataset_sources/external_research');
await fs.mkdir(OUT,{recursive:true});
const crawlAt=new Date().toISOString();
const sources=[];
const decode=s=>(s||'').replace(/&nbsp;|&#160;/gi,' ').replace(/&amp;/gi,'&').replace(/&quot;/gi,'"').replace(/&#39;|&apos;/gi,"'").replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(+n));
const textFromHtml=s=>decode(s.replace(/<!--[\s\S]*?-->/g,' ').replace(/<(script|style|noscript|svg)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]+>/g,' ')).replace(/[\t\r\f\v ]+/g,' ').replace(/\s*\n\s*/g,'\n').trim();
async function fetchJson(url){const r=await fetch(url,{headers:{'User-Agent':'PresidencyUniversityRAGResearch/1.0 (source inventory)'},signal:AbortSignal.timeout(30000)});if(!r.ok)throw new Error(`${r.status} ${url}`);return r.json()}
// User-requested secondary source. MediaWiki API returns plain article text and revision ID.
try{
 const api='https://en.wikipedia.org/w/api.php?action=query&prop=extracts%7Crevisions&explaintext=1&rvprop=ids&titles=Presidency_University%2C_Bengaluru&format=json&formatversion=2';
 const data=await fetchJson(api),page=data.query.pages[0];
 sources.push({source_id:'wikipedia-bengaluru',source_class:'secondary',institution_match:'Presidency University, Bengaluru, India',title:page.title,url:'https://en.wikipedia.org/wiki/Presidency_University,_Bengaluru',retrieved_at:crawlAt,revision_id:page.revisions?.[0]?.revid,license:'CC BY-SA 4.0 (verify article attribution/terms before redistribution)',text:page.extract||''});
}catch(e){sources.push({source_id:'wikipedia-bengaluru',source_class:'secondary',url:'https://en.wikipedia.org/wiki/Presidency_University,_Bengaluru',retrieved_at:crawlAt,error:String(e)})}
// Independent regulator source; this helps distinguish the Bengaluru university from similarly named institutions.
try{
 const url='https://www.ugc.gov.in/universitydetails/Private_university_other?id=713',r=await fetch(url,{headers:{'User-Agent':'PresidencyUniversityRAGResearch/1.0 (source inventory)'},signal:AbortSignal.timeout(30000)});
 if(!r.ok)throw new Error(`${r.status} ${url}`);const html=await r.text();
 sources.push({source_id:'ugc-private-university-entry',source_class:'official_regulator',institution_match:'Presidency University, Karnataka/Bengaluru (verify address on current official page)',title:'UGC State Private University listing',url,retrieved_at:crawlAt,text:textFromHtml(html)});
}catch(e){sources.push({source_id:'ugc-private-university-entry',source_class:'official_regulator',url:'https://www.ugc.gov.in/universitydetails/Private_university_other?id=713',retrieved_at:crawlAt,error:String(e)})}
// Legal background source; retained as an external transcription source, not treated as the official Gazette.
try{
 const url='https://indiacode.ecourtsindia.com/presidency-university-act-2013/',r=await fetch(url,{headers:{'User-Agent':'PresidencyUniversityRAGResearch/1.0 (source inventory)'},signal:AbortSignal.timeout(30000)});
 if(!r.ok)throw new Error(`${r.status} ${url}`);const html=await r.text();
 sources.push({source_id:'presidency-university-act-2013-transcription',source_class:'secondary_legal_transcription',institution_match:'Karnataka Act No. 41 of 2013; Bengaluru university',title:'Presidency University Act, 2013 transcription',url,retrieved_at:crawlAt,text:textFromHtml(html),note:'The publisher says the statutory text is transcribed from the Gazette; use the official Gazette for authoritative legal interpretation.'});
}catch(e){sources.push({source_id:'presidency-university-act-2013-transcription',source_class:'secondary_legal_transcription',url:'https://indiacode.ecourtsindia.com/presidency-university-act-2013/',retrieved_at:crawlAt,error:String(e)})}
await fs.writeFile(path.join(OUT,'source_pages.jsonl'),sources.map(s=>JSON.stringify(s)).join('\n')+'\n','utf8');
const chunks=[];
for(const s of sources){if(!s.text)continue;const paras=s.text.split(/\n+/).map(x=>x.trim()).filter(Boolean);let buf='',i=0;for(const para of paras){if(buf&&buf.length+para.length>1000){chunks.push({id:`ext-${s.source_id}-${i++}`,text:buf,metadata:{url:s.url,title:s.title,source_class:s.source_class,institution_match:s.institution_match,source_type:'external'}});buf=''}buf+=(buf?'\n':'')+para}if(buf)chunks.push({id:`ext-${s.source_id}-${i}`,text:buf,metadata:{url:s.url,title:s.title,source_class:s.source_class,institution_match:s.institution_match,source_type:'external'}})}
await fs.writeFile(path.join(OUT,'chunks.jsonl'),chunks.map(x=>JSON.stringify(x)).join('\n')+'\n','utf8');
await fs.writeFile(path.join(OUT,'README.md'),`# External source set\n\nThis folder contains sources outside the university's first-party website, kept separately from the official site crawl. Retrieved at ${crawlAt}.\n\n- Wikipedia is a secondary source; its claims should be checked against Presidency University or regulators. The article is about Bengaluru, not Presidency University Kolkata or Presidency University Bangladesh.\n- UGC is an official regulator source.\n- IndiaCode/eCourtsIndia is a legal transcription source, not the official Gazette.\n- `+'`source_pages.jsonl`'+` stores source text with provenance; `+'`chunks.jsonl`'+` contains source-linked passages.\n- Re-crawl before relying on changing facts such as leadership, programs, rankings, or campus details.\n`,'utf8');
console.log(JSON.stringify({source_count:sources.length,successful:sources.filter(s=>s.text).length,chunks:chunks.length,output:OUT},null,2));
