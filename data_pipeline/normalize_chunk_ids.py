"""Ensure every main-site RAG chunk ID is deterministic and unique by source+index."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent/'dataset'
targets=[ROOT/'chunks.jsonl',ROOT/'document_chunks.jsonl']
for target in targets:
    if not target.exists():continue
    temp=target.with_suffix(target.suffix+'.tmp');count=0;seen=set()
    with target.open(encoding='utf-8') as src,temp.open('w',encoding='utf-8') as dst:
        for line in src:
            try:row=json.loads(line)
            except Exception:continue
            meta=row.get('metadata',{});source=meta.get('url') or meta.get('local_path') or row.get('id','');idx=meta.get('chunk_index',0)
            prefix='doc' if meta.get('source_type')=='document' or target.name=='document_chunks.jsonl' else 'page'
            digest=hashlib.sha256(source.encode('utf-8')).hexdigest()[:24]
            row['id']=f'{prefix}-{digest}-{idx}'
            meta.setdefault('source_type','document' if prefix=='doc' else 'webpage');row['metadata']=meta
            if row['id'] in seen:raise RuntimeError(f'Duplicate chunk ID: {row["id"]}')
            seen.add(row['id']);dst.write(json.dumps(row,ensure_ascii=False)+'\n');count+=1
    temp.replace(target)
    print(json.dumps({'file':str(target),'chunks':count,'unique_ids':len(seen)}))
