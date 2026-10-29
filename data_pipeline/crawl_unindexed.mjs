import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
const ROOT=path.resolve('dataset'), CONCURRENCY=10;
const decode=s=>(s||'').replace(/&nbsp;|&#160;/gi,' ').replace(/&amp;/gi,'&').replace(/&quot;/gi,'"').replace(/&#39;|&apos;/gi,"'").replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(+n));
const clean=s=>decode(s.replace(/<!--[\s\S]*?-->/g,' ').replace(/<(script|style|noscript|svg)\b[^>]*>[\s\S]*?<\/\1>/gi,' ').replace(/<[^>]+>/g,' ')).replace(/[\t\r\f\v ]+/g,' ').trim();
const attrs=tag=>Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m=>[m[1].toLowerCase(),decode(m[2]??m[3]??m[4]??'')]));
const abs=(u,b)=>{try{return new URL(u,b).href}catch{return ''}};
const urls=(await fs.readFile(path.join(ROOT,'unindexed_first_party_pages.txt'),'utf8')).split(/\r?\n/).filter(Boolean);
const known=new Set();
for(const line of (await fs.readFile(path.join(ROOT,'crawl_urls.txt'),'utf8')).split(/\r?\n/)) if(line) try{known.add(new URL(line).pathname.replace(/\/$/,''))}catch{}
const todo=urls.filter(u=>!known.has(new URL(u).pathname.replace(/\/$/,'')));
const pageOut=fsSync.createWriteStream(path.join(ROOT,'pages.jsonl'),{flags:'a',encoding:'utf8'}), chunkOut=fsSync.createWriteStream(path.join(ROOT,'chunks.jsonl'),{flags:'a',encoding:'utf8'}), mediaOut=fsSync.createWriteStream(path.join(ROOT,'media_manifest.jsonl'),{flags:'a',encoding:'utf8'});
const write=(s,v)=>new Promise((resolve,reject)=>s.write(JSON.stringify(v)+'\n','utf8',e=>e?reject(e):resolve()));
const failures=[];let cursor=0,success=0,chunks=0,media=0;
function category(url){const p=new URL(url).pathname.toLowerCase();if(/\/program\//.test(p))return'program';if(/\/school\//.test(p))return'school';if(/faculty|department/.test(p))return'faculty_department';if(/student-life|facility|library/.test(p))return'campus_facility';if(/dsa|club/.test(p))return'student_life';return'general_academic_context'}
async function worker(){while(true){const i=cursor++;if(i>=todo.length)return;const url=todo[i];try{
 const res=await fetch(url,{headers:{'User-Agent':'PresidencyAcademicRAGResearch/1.0 (public website indexing)'},signal:AbortSignal.timeout(25000)});if(!res.ok){failures.push({url,status:res.status});continue}const type=res.headers.get('content-type')||'';if(!type.includes('text/html')){failures.push({url,status:'non_html',content_type:type});continue}
 const html=await res.text(),title=clean((html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)||[,''])[1]),desc=decode((html.match(/<meta\b[^>]*name=["']description["'][^>]*content=["']([^"']*)/i)||[,''])[1]),body=(html.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i)||[,''])[1],content=body.replace(/<(header|nav|footer)\b[^>]*>[\s\S]*?<\/\1>/gi,' '),text=clean(content);
 const headings=[...content.matchAll(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi)].map(m=>({level:+m[1],text:clean(m[2])})).filter(x=>x.text);
 const links=[...content.matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/gi)].map(m=>{const a=attrs(m[0].slice(0,m[0].indexOf('>')+1));return{text:clean(m[1]),url:abs(a.href||'',url),title:a.title||'',target:a.target||''}}).filter(x=>x.url);
 const pageMedia=[];for(const m of content.matchAll(/<(img|video|audio|source|iframe|embed)\b[^>]*>/gi)){const tag=m[1].toLowerCase(),a=attrs(m[0]),raw=tag==='img'?(a.src||a['data-src']||a.srcset?.split(',')[0]?.trim().split(' ')[0]):(a.src||a.href||a['data-src']||a['data-video']);if(raw)pageMedia.push({page_url:url,page_title:title,tag,url:abs(raw,url),alt:a.alt||'',title:a.title||'',type:a.type||'',poster:abs(a.poster||'',url),caption:a['aria-label']||''})}
 const page={url,canonical:url,title,description:desc,category:category(url),status:res.status,crawled_at:new Date().toISOString(),headings,text,links,media:pageMedia};await write(pageOut,page);success++;
 for(const m of pageMedia){await write(mediaOut,m);media++}
 const paras=text.split(/(?<=[.!?])\s{2,}|\n+/).map(s=>s.trim()).filter(Boolean);let buf='',idx=0;async function emit(){if(!buf.trim())return;await write(chunkOut,{id:`page-${createHash('sha256').update(url).digest('hex').slice(0,24)}-${idx}`,text:buf,metadata:{url,title,category:page.category,headings:headings.map(h=>h.text),chunk_index:idx,source_type:'webpage'}});idx++;chunks++;buf=''}
 for(const para of paras){if(buf&&buf.length+para.length>1100)await emit();if(para.length>1800){for(let j=0;j<para.length;j+=1000){if(buf)await emit();buf=para.slice(j,j+1000);await emit()}}else buf+=(buf?'\n':'')+para}await emit();
 }catch(e){failures.push({url,error:String(e?.message||e)})}if((i+1)%100===0)console.log(`Unindexed URLs ${i+1}/${todo.length}; pages=${success}; failures=${failures.length}`)}}
await Promise.all(Array.from({length:CONCURRENCY},worker));for(const s of [pageOut,chunkOut,mediaOut])await new Promise(r=>s.end(r));
await fs.writeFile(path.join(ROOT,'unindexed_crawl_failures.json'),JSON.stringify(failures,null,2));const summary={discovered_urls:urls.length,not_in_sitemap:todo.length,successful_html_pages:success,chunks,media_references:media,failures:failures.length};await fs.writeFile(path.join(ROOT,'unindexed_crawl_summary.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
