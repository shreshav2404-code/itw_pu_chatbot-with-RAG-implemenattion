import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const ORIGIN = 'https://presidencyuniversity.in';
const OUT = path.resolve('dataset');
const CONCURRENCY = 18;
const DELAY_MS = 100;

const decode = (s = '') => s
  .replace(/&nbsp;|&#160;/gi, ' ').replace(/&amp;/gi, '&').replace(/&quot;/gi, '"')
  .replace(/&#39;|&apos;/gi, "'").replace(/&lt;/gi, '<').replace(/&gt;/gi, '>')
  .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
  .replace(/&#x([\da-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)));
const clean = s => decode(s.replace(/<!--[\s\S]*?-->/g, ' ').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
  .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ').replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, ' ')
  .replace(/<svg\b[^>]*>[\s\S]*?<\/svg>/gi, ' ').replace(/<[^>]+>/g, ' '))
  .replace(/[\t\r\f\v ]+/g, ' ').replace(/\s*\n\s*/g, '\n').trim();
const attrs = tag => Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(m => [m[1].toLowerCase(), decode(m[2] ?? m[3] ?? m[4] ?? '')]));
const abs = (u, base) => { try { return new URL(u, base).href; } catch { return ''; } };
const sleep = ms => new Promise(r => setTimeout(r, ms));

function scope(url) {
  const p = new URL(url).pathname.toLowerCase();
  return p === '/' || /\/(program|programs|school|schools|academics|academic-regulations|examination-regulations|departments|faculty-staff|student-life|research|admissions|resources|accreditations-rankings|placements|about-us|life-at-presidency)(\/|$)/.test(p)
    || /\/(academic|examin|curriculum|syllabus|timetable|time-table|calendar|faculty|department|facility|facilities|campus|library|laborator|lab|research|disclos|ordinance|regulation|policy|handbook|prospectus)/.test(p);
}

function classify(url) {
  const p = new URL(url).pathname.toLowerCase();
  if (/\/program\//.test(p) || /\/programs?\//.test(p)) return 'program';
  if (/\/school\//.test(p)) return 'school';
  if (/faculty-staff|\/faculty\//.test(p)) return 'faculty';
  if (/department/.test(p)) return 'department';
  if (/academics|academic-regulations|examination-regulations|time-table/.test(p)) return 'academic_operations';
  if (/student-life|facility|facilities|campus|library|laborator|\/lab/.test(p)) return 'campus_facility';
  if (/research/.test(p)) return 'research';
  if (/admission/.test(p)) return 'admissions';
  if (/about-us|disclosure|policy|regulation/.test(p)) return 'governance';
  if (/placement/.test(p)) return 'placements';
  if (/accreditation/.test(p)) return 'accreditations';
  return 'general_academic_context';
}

await fs.mkdir(OUT, { recursive: true });
const sitemapRes = await fetch(`${ORIGIN}/sitemap.xml`);
if (!sitemapRes.ok) throw new Error(`Sitemap returned ${sitemapRes.status}`);
const sitemap = await sitemapRes.text();
const all = [...sitemap.matchAll(/<loc>\s*([^<]+)\s*<\/loc>/gi)].map(m => decode(m[1].trim()));
const urls = [...new Set(all.filter(u => { try { return ['presidencyuniversity.in','www.presidencyuniversity.in'].includes(new URL(u).hostname); } catch { return false; } }))];
await fs.writeFile(path.join(OUT, 'sitemap_urls.txt'), all.join('\n') + '\n');
await fs.writeFile(path.join(OUT, 'crawl_urls.txt'), urls.join('\n') + '\n');

const pageStream = fsSync.createWriteStream(path.join(OUT, 'pages.jsonl'), { encoding: 'utf8' });
const chunkStream = fsSync.createWriteStream(path.join(OUT, 'chunks.jsonl'), { encoding: 'utf8' });
const mediaStream = fsSync.createWriteStream(path.join(OUT, 'media_manifest.jsonl'), { encoding: 'utf8' });
const pages = { count: 0 }, chunks = { count: 0 }, media = { count: 0 };
const mediaSeen = new Set(), documents = new Map(), categoryCounts = {};
const failures = [];
const writeLine = (stream, value) => new Promise((resolve, reject) => stream.write(JSON.stringify(value) + '\n', 'utf8', e => e ? reject(e) : resolve()));
async function writeChunks(p) {
  const paras = p.text.split(/(?<=[.!?])\s{2,}|\n+/).map(s => s.trim()).filter(Boolean);
  let buf = '', idx = 0;
  const emit = async () => {
    if (!buf.trim()) return;
    await writeLine(chunkStream, { id: `page-${createHash('sha256').update(p.url).digest('hex').slice(0,24)}-${idx}`, text: buf.trim(), metadata: { url: p.url, title: p.title, category: p.category, headings: p.headings.map(h => h.text), chunk_index: idx, source_type: 'webpage' } });
    idx++; chunks.count++; buf = '';
  };
  for (const para of paras) {
    if (buf.length && buf.length + para.length > 1100) await emit();
    if (para.length > 1800) {
      for (let j=0;j<para.length;j+=1000) { if (buf) await emit(); buf = para.slice(j,j+1000); await emit(); }
    } else buf += (buf ? '\n' : '') + para;
  }
  await emit();
}
let cursor = 0;
async function worker() {
  while (true) {
    const i = cursor++;
    if (i >= urls.length) return;
    const url = urls[i];
    try {
      const response = await fetch(url, { headers: { 'User-Agent': 'PresidencyAcademicRAGResearch/1.0 (public website indexing)' }, signal: AbortSignal.timeout(25000) });
      const type = response.headers.get('content-type') || '';
      if (!response.ok) { failures.push({ url, status: response.status }); continue; }
      if (!type.includes('text/html')) {
        documents.set(url, { url, content_type: type, status: response.status, note: 'Sitemap resource; binary content available for download.' });
        continue;
      }
      const html = await response.text();
      const title = clean((html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i) || [,''])[1]);
      const desc = decode((html.match(/<meta\b[^>]*name=["']description["'][^>]*content=["']([^"']*)/i) || [,''])[1]);
      const canonical = abs((html.match(/<link\b[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)/i) || [,''])[1], url) || url;
      const bodyMatch = html.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i);
      const body = bodyMatch?.[1] || html;
      const contentHtml = body.replace(/<(header|nav|footer)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ');
      const text = clean(contentHtml);
      const headings = [...contentHtml.matchAll(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi)].map(m => ({ level: Number(m[1]), text: clean(m[2]) })).filter(x => x.text);
      const links = [...contentHtml.matchAll(/<a\b[^>]*>([\s\S]*?)<\/a>/gi)].map(m => {
        const a = attrs(m[0].slice(0, m[0].indexOf('>') + 1));
        return { text: clean(m[1]), url: abs(a.href || '', url), title: a.title || '', target: a.target || '' };
      }).filter(x => x.url);
      const pageMedia = [];
      for (const m of contentHtml.matchAll(/<(img|video|audio|source|iframe|embed)\b[^>]*>/gi)) {
        const tag = m[1].toLowerCase(), a = attrs(m[0]);
        const raw = tag === 'img' ? (a.src || a['data-src'] || a.srcset?.split(',')[0]?.trim().split(' ')[0]) : (a.src || a.href || a['data-src'] || a['data-video']);
        if (!raw) continue;
        const item = { page_url: url, page_title: title, tag, url: abs(raw, url), alt: a.alt || '', title: a.title || '', type: a.type || '', poster: abs(a.poster || '', url), caption: a['aria-label'] || '' };
        pageMedia.push(item);
      }
      const pageDocs = links.filter(x => /\.(pdf|docx?|xlsx?|pptx?)(?:[?#]|$)/i.test(x.url));
      for (const d of pageDocs) if (!documents.has(d.url)) documents.set(d.url, { ...d, page_url: url, content_type: 'linked_document' });
      for (const m of pageMedia) {
        const key = m.url + '|' + m.page_url;
        if (!mediaSeen.has(key)) { mediaSeen.add(key); await writeLine(mediaStream, m); media.count++; }
      }
      const p = { url, canonical, title, description: desc, category: classify(url), status: response.status, crawled_at: new Date().toISOString(), headings, text, links, media: pageMedia };
      await writeLine(pageStream, p); await writeChunks(p);
      pages.count++; categoryCounts[p.category] = (categoryCounts[p.category] || 0) + 1;
    } catch (e) { failures.push({ url, error: String(e?.message || e) }); }
    await sleep(DELAY_MS);
    if ((i + 1) % 100 === 0) console.log(`Fetched ${i + 1}/${urls.length}; pages=${pages.count}; failures=${failures.length}`);
  }
}
await Promise.all(Array.from({ length: CONCURRENCY }, worker));
for (const stream of [pageStream, chunkStream, mediaStream]) await new Promise(resolve => stream.end(resolve));
const uniqueDocs = [...documents.values()].filter(d => d.url && /^https?:/.test(d.url));
await fs.mkdir(path.join(OUT, 'documents'), { recursive: true });
const downloaded = [];
let docCursor = 0;
async function docWorker() {
  while (true) {
    const i = docCursor++;
    if (i >= uniqueDocs.length) return;
    const d = uniqueDocs[i];
    try {
      const u = new URL(d.url);
      if (!['presidencyuniversity.in','www.presidencyuniversity.in','presidencyuniversity.edu.in'].includes(u.hostname)) { downloaded.push({ ...d, download_status: 'external_reference_only' }); continue; }
      const response = await fetch(d.url, { headers: { 'User-Agent': 'PresidencyAcademicRAGResearch/1.0 (public website indexing)' }, signal: AbortSignal.timeout(45000) });
      const mime = response.headers.get('content-type') || '';
      const length = Number(response.headers.get('content-length') || 0);
      if (!response.ok) { downloaded.push({ ...d, download_status: `http_${response.status}`, content_type: mime }); continue; }
      if (length > 50 * 1024 * 1024) { downloaded.push({ ...d, download_status: 'skipped_over_50MB', content_type: mime, bytes: length }); continue; }
      const bytes = Buffer.from(await response.arrayBuffer());
      if (bytes.length > 50 * 1024 * 1024) { downloaded.push({ ...d, download_status: 'skipped_over_50MB', content_type: mime, bytes: bytes.length }); continue; }
      const ext = (new URL(d.url).pathname.match(/\.(pdf|docx?|xlsx?|pptx?)$/i) || [,'bin'])[1].toLowerCase();
      const name = `${createHash('sha256').update(d.url).digest('hex').slice(0, 24)}.${ext}`;
      await fs.writeFile(path.join(OUT, 'documents', name), bytes);
      downloaded.push({ ...d, local_path: `documents/${name}`, download_status: 'downloaded', content_type: mime, bytes: bytes.length });
    } catch (e) { downloaded.push({ ...d, download_status: 'failed', error: String(e?.message || e) }); }
  }
}
await Promise.all(Array.from({ length: 4 }, docWorker));
await fs.writeFile(path.join(OUT, 'documents_manifest.jsonl'), downloaded.map(x => JSON.stringify(x)).join('\n') + '\n');
await fs.writeFile(path.join(OUT, 'crawl_failures.json'), JSON.stringify(failures, null, 2));
const summary = { origin: ORIGIN, crawled_at: new Date().toISOString(), sitemap_url_count: all.length, selected_url_count: urls.length, successful_html_pages: pages.count, chunks: chunks.count, media_references: media.count, linked_document_references: uniqueDocs.length, documents_downloaded: downloaded.filter(d => d.download_status === 'downloaded').length, failures: failures.length, categories: categoryCounts, scope_note: 'Every first-party URL listed in the public sitemap was attempted. Linked documents up to 50 MB on the university domain were downloaded; media files are recorded as references rather than downloaded.' };
await fs.writeFile(path.join(OUT, 'crawl_summary.json'), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
