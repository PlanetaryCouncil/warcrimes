#!/usr/bin/env python3
"""Harvest headline + publication date for every source link in data.json.

Nothing is invented: values come from the page's own metadata (og:title,
article:published_time, JSON-LD datePublished, <time>), the GDELT corpus
(press-articles.json), a Wayback Machine snapshot of the page, YouTube
oEmbed, or a date embedded in the URL path. Unknowns stay empty.
Results are cached in tools/meta_cache.json; merge writes them into data.json
as link.headline / link.published.
"""
import json, re, sys, html, time, urllib.request, urllib.parse, concurrent.futures as cf
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'tools' / 'meta_cache.json'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'

def get(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(8_000_000).decode('utf-8', 'replace')

def meta(doc, *names):
    for n in names:
        for pat in (rf'<meta[^>]+(?:property|name|itemprop)=["\']{n}["\'][^>]*content=["\']([^"\']+)',
                    rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name|itemprop)=["\']{n}["\']'):
            m = re.search(pat, doc, re.I)
            if m: return html.unescape(m.group(1)).strip()
    return ''

def norm_date(s):
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s or '')
    if m: return '-'.join(m.groups())
    m = re.search(r'^(\d{4})(\d{2})(\d{2})', s or '')
    return '-'.join(m.groups()) if m else ''

def url_date(u):
    m = re.search(r'/(20[12]\d)[/-](\d{1,2})[/-](\d{1,2})(?:/|-|$)', u)
    if m: return f'{m[1]}-{int(m[2]):02d}-{int(m[3]):02d}'
    m = re.search(r'/(20[12]\d)(\d{2})(\d{2})[-/]', u)
    return f'{m[1]}-{m[2]}-{m[3]}' if m else ''

def parse(doc):
    t = meta(doc, 'og:title', 'twitter:title')
    if t.strip().lower() in ('forensic architecture',):
        m = re.search(r'<h1[^>]*>(.*?)</h1>', doc, re.I | re.S)
        if m: t = html.unescape(re.sub(r'<[^>]+>|\s+', ' ', m.group(1))).strip()
    if not t:
        m = re.search(r'<title[^>]*>(.*?)</title>', doc, re.I | re.S)
        t = html.unescape(re.sub(r'\s+', ' ', m.group(1))).strip() if m else ''
    d = norm_date(meta(doc, 'article:published_time', 'datePublished', 'uploadDate', 'parsely-pub-date',
                       'pubdate', 'publish-date', 'date', 'dc.date', 'DC.date.issued', 'sailthru.date', 'og:article:published_time'))
    if not d:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', doc)
        d = norm_date(m.group(1)) if m else ''
    if not d:
        m = re.search(r'<time[^>]+datetime=["\']([^"\']+)', doc, re.I)
        d = norm_date(m.group(1)) if m else ''
    return t, d

BAD_TITLE = re.compile(r'^(access restricted|client challenge|forensic architecture$|just a moment|access denied|attention required|403|404|page not found|robot|are you a robot|subscribe to read|log in|x$|youtube$)', re.I)

_FA = None
def fa_index():
    # forensic-architecture.org is a JS app; its public API carries title + publication date
    global _FA
    if _FA is None:
        j = json.loads(get('https://forensic-architecture.org/api/fa/v1/investigations', 40))
        _FA = {i['slug']: i for i in (j['investigations'] if isinstance(j, dict) else j)}
    return _FA

def harvest(url, gdelt):
    out = {'headline': '', 'published': '', 'via': ''}
    host = urllib.parse.urlparse(url).hostname or ''
    try:
        if host.endswith('forensic-architecture.org') and '/investigation/' in url:
            i = fa_index().get(url.rstrip('/').rsplit('/', 1)[-1])
            if i:
                out.update(headline=html.unescape(i['title']), published=norm_date(i['publication_date'].replace('/', '-')), via='fa-api')
                return out
        if 'youtube.com' in host or 'youtu.be' in host:
            j = json.loads(get('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote(url, safe='')))
            out.update(headline=j.get('title', ''), via='youtube-oembed')
            try:
                _, d = parse(get(url)); out['published'] = d
            except Exception: pass
            return out
        if 'wikipedia.org' in host:
            out.update(headline=urllib.parse.unquote(url.rsplit('/', 1)[-1]).replace('_', ' ').split('#')[0] + ' — Wikipedia', via='url')
            return out
        t, d = parse(get(url))
        if t and not BAD_TITLE.search(t): out.update(headline=t, published=d, via='page')
    except Exception:
        pass
    if not out['headline']:
        try:
            j = json.loads(get('https://archive.org/wayback/available?url=' + urllib.parse.quote(url, safe=''), 30))
            snap = j.get('archived_snapshots', {}).get('closest', {})
            if snap.get('available'):
                raw = re.sub(r'/web/(\d+)/', r'/web/\1id_/', snap['url'], count=1)
                t, d = parse(get(raw, 40))
                if t and not BAD_TITLE.search(t): out.update(headline=t, published=d, via='wayback')
        except Exception:
            pass
    if not out['headline'] and url in gdelt:
        g = gdelt[url]
        t = re.sub(r'\s+([,.:;!?%)])', r'\1', g.get('title', '')).strip()
        out.update(headline=t, published=norm_date(g.get('seendate', '')), via='gdelt')
    if not out['published']:
        out['published'] = url_date(url)
    return out

def main():
    data = json.loads((ROOT / 'data.json').read_text())
    gdelt = {}
    pa = json.loads((ROOT / 'press-articles.json').read_text())
    for arts in pa.values():
        for a in (arts if isinstance(arts, list) else arts.get('articles', [])):
            if isinstance(a, dict) and a.get('url'): gdelt[a['url']] = a
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    urls = {l['url'] for d in data['incidents'] for l in d['links']}
    urls |= {d['official']['url'] for d in data['incidents'] if d.get('official')}
    todo = [u for u in urls if u not in cache or ('--retry' in sys.argv and (not cache[u]['headline'] or cache[u]['via'] == 'gdelt' or BAD_TITLE.search(cache[u]['headline'])))]
    print(f'{len(urls)} urls, {len(todo)} to fetch', flush=True)
    with cf.ThreadPoolExecutor(4 if '--retry' in sys.argv else 12) as ex:
        for i, (u, r) in enumerate(zip(todo, ex.map(lambda u: harvest(u, gdelt), todo))):
            cache[u] = r
            if i % 25 == 0:
                CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False)); print(i, flush=True)
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    got = sum(1 for u in urls if cache[u]['headline']); dated = sum(1 for u in urls if cache[u]['published'])
    print(f'headlines {got}/{len(urls)}, dates {dated}/{len(urls)}')

if __name__ == '__main__':
    main()
