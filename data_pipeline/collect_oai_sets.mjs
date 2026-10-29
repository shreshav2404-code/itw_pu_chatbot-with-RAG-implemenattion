import fs from 'node:fs/promises';
const base='http://182.72.188.194:8080/oai/request?verb=ListSets';
let url=base,all=[];
for(let page=0;page<10;page++){
 const xml=await (await fetch(url)).text();
 for(const m of xml.matchAll(/<set>\s*<setSpec>([\s\S]*?)<\/setSpec>\s*<setName>([\s\S]*?)<\/setName>\s*<\/set>/g)) all.push({set_spec:m[1],name:m[2].replace(/&amp;/g,'&')});
 const token=(xml.match(/<resumptionToken[^>]*>([\s\S]*?)<\/resumptionToken>/)||[])[1];
 if(!token)break;
 url=base+'&resumptionToken='+encodeURIComponent(token);
}
await fs.writeFile('dataset_sources/jspui/oai_sets.jsonl',all.map(x=>JSON.stringify(x)).join('\n')+'\n');
console.log(JSON.stringify({oai_sets:all.length}));
