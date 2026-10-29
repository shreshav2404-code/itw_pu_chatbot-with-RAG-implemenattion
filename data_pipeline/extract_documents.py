"""Extract text from downloaded university documents into a source-linked JSONL file."""
import json
import logging
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent / "dataset"
MANIFEST = ROOT / "documents_manifest.jsonl"
OUT = ROOT / "documents_text.jsonl"
CHUNKS_OUT = ROOT / "document_chunks.jsonl"
logging.getLogger("pypdf").setLevel(logging.ERROR)

def extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    if ext in {".docx", ".pptx", ".xlsx"}:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            xml_names = [n for n in names if (n.startswith("word/document") if ext == ".docx" else n.startswith("ppt/slides/slide") if ext == ".pptx" else n == "xl/sharedStrings.xml" or re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)) and n.endswith(".xml")]
            texts = []
            for name in sorted(xml_names):
                root = ET.fromstring(zf.read(name))
                texts.extend(t.text or "" for t in root.iter() if t.tag.endswith("}t"))
            return "\n".join(texts)
    if ext == ".doc":
        return ""
    return ""

def process_item(item):
    local=item.get("local_path")
    if not local:return None
    file_path=ROOT/local
    try:
        text=re.sub(r"\s+"," ",extract(file_path)).strip().encode("utf-8","replace").decode("utf-8")
        title=(item.get("text") or file_path.name).encode("utf-8","replace").decode("utf-8")
        row={"url":item.get("url"),"page_url":item.get("page_url"),"title":title,"local_path":local,"characters":len(text),"text":text}
        pieces=[]
        for i in range(0,len(text),1000):
            piece=text[i:i+1000]
            if piece.strip():
                pieces.append({"id":f"doc-{Path(local).stem}-{i//1000}","text":piece,"metadata":{"url":item.get("url"),"page_url":item.get("page_url"),"title":title,"local_path":local,"chunk_index":i//1000,"source_type":"document"}})
        return row,pieces
    except Exception as exc:
        return {"url":item.get("url"),"page_url":item.get("page_url"),"local_path":local,"error":str(exc),"text":""},[]

def main():
    from multiprocessing import Pool
    processed=with_text=empty_or_failed=chunk_count=0
    items=[]
    if MANIFEST.exists():
        for line in MANIFEST.open(encoding="utf-8"):
            try:items.append(json.loads(line))
            except json.JSONDecodeError:continue
    done=set()
    if OUT.exists():
        for line in OUT.open(encoding="utf-8"):
            try:
                row=json.loads(line)
                if row.get("local_path"):done.add(row["local_path"])
            except Exception:pass
    items=[item for item in items if item.get("local_path") not in done]
    processed=len(done)
    if OUT.exists():
        for line in OUT.open(encoding="utf-8"):
            try:with_text+=int(json.loads(line).get("characters",0)>0)
            except Exception:pass
    empty_or_failed=processed-with_text
    chunk_count=sum(1 for _ in CHUNKS_OUT.open(encoding="utf-8")) if CHUNKS_OUT.exists() else 0
    # Four worker processes parallelize CPU-bound PDF parsing. Results are
    # streamed to disk in the parent so a multi-GB corpus is never held at once.
    workers=min(4,max(1,__import__('os').cpu_count() or 1))
    with OUT.open("a",encoding="utf-8") as out, CHUNKS_OUT.open("a",encoding="utf-8") as chunk_out, Pool(workers) as pool:
        for result in pool.imap_unordered(process_item,items,chunksize=1):
            if result is None:continue
            row,pieces=result
            out.write(json.dumps(row,ensure_ascii=False)+"\n")
            if row.get("text"):with_text+=1
            else:empty_or_failed+=1
            for piece in pieces:
                chunk_out.write(json.dumps(piece,ensure_ascii=False)+"\n");chunk_count+=1
            processed+=1
            if processed%25==0:
                out.flush();chunk_out.flush()
                print(json.dumps({"processed":processed,"remaining":len(items),"total":len(done)+len(items),"with_text":with_text,"empty_or_failed":empty_or_failed,"chunks":chunk_count}),flush=True)
    print(json.dumps({"documents_processed":processed,"with_text":with_text,"empty_or_failed":empty_or_failed,"document_chunks":chunk_count,"output":str(OUT),"chunks_output":str(CHUNKS_OUT)},indent=2))

if __name__=="__main__":main()
