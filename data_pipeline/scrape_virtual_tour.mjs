import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
const ROOT=path.resolve('dataset_sources/campus_virtual_tour');
const BASE='https://www.immersivetourz.com/presidencyuniversity/';
const VERSION='?v=1751605676358';
await fs.mkdir(ROOT,{recursive:true});
const sources=[['index.html',BASE+'index.html'],['script.js',BASE+'script.js'+VERSION],['script_general.js',BASE+'script_general.js'+VERSION],['locale_en.txt',BASE+'locale/en.txt'+VERSION]];
const saved={};
for(const [name,url] of sources){const r=await fetch(url,{headers:{'User-Agent':'PresidencyUniversityRAGResearch/1.0 (linked virtual tour inventory)'},signal:AbortSignal.timeout(30000)});if(!r.ok)throw new Error(`${r.status} ${url}`);const content=await r.text();await fs.writeFile(path.join(ROOT,name),content,'utf8');saved[name]={url,bytes:Buffer.byteLength(content)};}
const locale=await fs.readFile(path.join(ROOT,'locale_en.txt'),'utf8');
const general=await fs.readFile(path.join(ROOT,'script_general.js'),'utf8');
const scenes=[],hotspots=[],links=[];
for(const line of locale.split(/\r?\n/)){
 const m=line.match(/^([^=]+?)\s*=\s*(.*)$/);if(!m)continue;const key=m[1].trim(),value=m[2].trim();
 let x=key.match(/^panorama_([A-F0-9_]+)\.label$/i);if(x){scenes.push({scene_id:x[1],label:value,url:BASE+'index.html',source_file:'locale_en.txt'});continue;}
 x=key.match(/^(HotspotPanoramaOverlayArea|HotspotPanoramaOverlayTextImage|HotspotPanoramaOverlayImage)_([A-F0-9_]+)\.(toolTip|text|title)$/i);if(x)hotspots.push({hotspot_id:x[2],component:x[1],field:x[3],label:value,url:BASE+'index.html',source_file:'locale_en.txt'});
 x=key.match(/^LinkBehaviour_([A-F0-9_]+)\.source$/i);if(x)links.push({link_id:x[1],target:value,source:'virtual-tour-hotspot',url:BASE+'index.html'});
}
const thumbDir=path.join(ROOT,'thumbnails');await fs.mkdir(thumbDir,{recursive:true});
const uniqueScenes=[...new Map(scenes.map(s=>[s.scene_id,s])).values()];let thumbCursor=0,thumbDownloaded=0,thumbFailures=0;
async function thumbWorker(){while(true){const i=thumbCursor++;if(i>=uniqueScenes.length)return;const s=uniqueScenes[i],url=`${BASE}media/panorama_${s.scene_id}_t.webp${VERSION}`;try{const r=await fetch(url,{headers:{'User-Agent':'PresidencyUniversityRAGResearch/1.0 (linked virtual tour inventory)'},signal:AbortSignal.timeout(30000)});if(!r.ok){s.thumbnail_status=`http_${r.status}`;thumbFailures++;continue}const bytes=Buffer.from(await r.arrayBuffer()),file=`${createHash('sha256').update(s.scene_id).digest('hex').slice(0,20)}.webp`;await fs.writeFile(path.join(thumbDir,file),bytes);s.thumbnail_url=url;s.thumbnail_path=`thumbnails/${file}`;s.thumbnail_bytes=bytes.length;s.thumbnail_status='downloaded';thumbDownloaded++;}catch(e){s.thumbnail_status='failed';s.thumbnail_error=String(e?.message||e);thumbFailures++}}}
await Promise.all(Array.from({length:8},thumbWorker));
const assetPaths=[...new Set([...general.matchAll(/["']([^"']*?(?:media\/|\.(?:mp3|mp4|webm|ogg|wav|jpg|jpeg|png|webp|svg|pdf)(?:\?[^"']*)?)[^"']*)["']/gi)].map(m=>m[1]))];
const assets=assetPaths.map(p=>{const clean=p.split('?')[0];return{asset_path:p,url:new URL(clean,BASE).href,media_type:/\.mp3|\.ogg|\.wav/i.test(clean)?'audio':/\.mp4|\.webm/i.test(clean)?'video':/\.webp|\.png|\.jpe?g|\.svg/i.test(clean)?'image':'other',source:'virtual_tour_project_manifest'}});
await fs.writeFile(path.join(ROOT,'scenes.jsonl'),scenes.map(x=>JSON.stringify(x)).join('\n')+'\n','utf8');
await fs.writeFile(path.join(ROOT,'hotspots.jsonl'),hotspots.map(x=>JSON.stringify(x)).join('\n')+'\n','utf8');
await fs.writeFile(path.join(ROOT,'tour_links.jsonl'),links.map(x=>JSON.stringify(x)).join('\n')+'\n','utf8');
await fs.writeFile(path.join(ROOT,'assets_manifest.jsonl'),assets.map(x=>JSON.stringify(x)).join('\n')+'\n','utf8');
const tourChunks=[...scenes.map(s=>({id:`scene-${s.scene_id}`,text:`University campus virtual tour scene: ${s.label}. Use the linked interactive tour to view this location.`,metadata:{url:s.url,title:s.label,scene_id:s.scene_id,topic_tags:['campus_facilities_navigation'],source_type:'virtual_tour'}})),...hotspots.filter(h=>h.label&&h.label!=='Back to Menu').map(h=>({id:`hotspot-${h.hotspot_id}`,text:`University campus virtual tour hotspot: ${h.label}. Use the linked interactive tour to navigate visually to this point.`,metadata:{url:h.url,title:h.label,hotspot_id:h.hotspot_id,topic_tags:['campus_facilities_navigation'],source_type:'virtual_tour'}}))];
await fs.writeFile(path.join(ROOT,'chunks.jsonl'),tourChunks.map(x=>JSON.stringify(x)).join('\n')+'\n','utf8');
const summary={url:BASE+'index.html',retrieved_at:new Date().toISOString(),files:saved,scene_label_count:scenes.length,hotspot_label_count:hotspots.length,external_link_count:links.length,unique_scene_labels:[...new Set(scenes.map(x=>x.label))].length,unique_hotspot_labels:[...new Set(hotspots.map(x=>x.label))].length,tour_chunks:tourChunks.length,virtual_tour_assets_referenced:assets.length,scene_thumbnails_downloaded:thumbDownloaded,scene_thumbnail_failures:thumbFailures,limitations:'The tour is a third-party hosted 360-degree interactive viewer. Low-resolution scene thumbnails are downloaded and the project asset manifest is indexed. Full panorama tiles remain source references, not bulk-downloaded; the extraction does not claim a verified route graph or room-by-room indoor directions.'};
await fs.writeFile(path.join(ROOT,'summary.json'),JSON.stringify(summary,null,2));
await fs.writeFile(path.join(ROOT,'README.md'),`# Campus virtual tour source\n\nLinked by Presidency University at ${summary.url}. Contains ${scenes.length} panorama labels, ${hotspots.length} hotspot labels, ${assets.length} asset references, and ${thumbDownloaded} downloaded low-resolution scene thumbnails. Open the source URL for interactive 360-degree navigation.\n\n`+summary.limitations+'\n','utf8');
console.log(JSON.stringify(summary,null,2));
