#!/usr/bin/env python3
"""Generate one static page per incident at /<id>/index.html, plus sitemap.xml and robots.txt.

Run after editing data.json:  python3 tools/build.py
"""
import json, html, re, shutil
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://warcrimes.planetarycouncil.org'
data = json.loads((ROOT / 'data.json').read_text())
incidents = data['incidents']
e = lambda s: html.escape(str(s or ''), quote=True)
is_fa = lambda u: 'forensic-architecture.org' in u
favicon = lambda u: f'https://www.google.com/s2/favicons?domain={urlparse(u).hostname}&sz=64'
host = lambda u: (urlparse(u).hostname or '').removeprefix('www.')

def labels():
    out, n = {}, 0
    for sec in ('main', 'closers'):
        for d in incidents:
            if d['section'] == sec: n += 1; out[d['id']] = f'{n:02d}'
    for sec, p in (('docket', 'D'), ('hamas', 'H')):
        for i, d in enumerate([d for d in incidents if d['section'] == sec]): out[d['id']] = f'{p}{i + 1}'
    return out
LABEL = labels()
ORDER = sorted(incidents, key=lambda d: (['main', 'closers', 'docket', 'hamas'].index(d['section']), incidents.index(d)))
SECTION_NAME = {'main': 'Incidents', 'closers': 'Closers', 'docket': 'The Docket', 'hamas': 'Hamas'}
SECTION_ANCHOR = {'main': '#top', 'closers': '#sec-closers', 'docket': '#sec-docket', 'hamas': '#sec-hamas'}

def plain(s): return re.sub(r'<[^>]+>', '', s)
def first_sentence(s):
    s = plain(s); m = re.match(r'(.{80,300}?[.!?])\s', s)
    return (m.group(1) if m else s[:297] + '…')

def row(i, l):
    head = l.get('headline') or ''
    gd = '<span class="host" title="Headline as indexed by the GDELT Project; the publisher blocked direct retrieval, so punctuation may differ from the original.">(GDELT)</span>' if l.get('headline_via') == 'gdelt' else ''
    h = (f'<a href="{e(l["url"])}" target="_blank" rel="noopener">{e(head)}</a>{gd}' if head
         else f'<a href="{e(l["url"])}" target="_blank" rel="noopener"><span class="nohead">headline not retrieved</span></a><span class="host">{e(host(l["url"]))}</span>')
    date = l.get('published') or '—'
    return (f'<tr class="{"fa" if is_fa(l["url"]) else ""}"><td class="d">{e(date)}</td>'
            f'<td class="p"><img src="{favicon(l["url"])}" alt="" loading="lazy">{e(l["source"])}</td><td class="h">{h}</td></tr>')

def page(d, prev, nxt):
    links = d['links']
    fa = [l for l in links if is_fa(l['url'])]
    rest = sorted([l for l in links if not is_fa(l['url'])], key=lambda l: (not l.get('published'), l.get('published') or ''))
    ordered = fa + rest
    dated = sum(1 for l in links if l.get('published'))
    url = f'{SITE}/{d["id"]}/'
    desc = first_sentence(d['summary'])
    title = f'{plain(d["title"])} — War Crimes Safari'
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': plain(d['title'])[:110], 'description': desc,
          'url': url, 'isPartOf': {'@type': 'WebSite', 'name': 'The War Crimes Safari', 'url': SITE + '/'},
          'citation': [l['url'] for l in ordered] + ([d['wikipedia']] if d.get('wikipedia') else [])}
    score = ''
    if d['section'] in ('main', 'closers'):
        score = f'''<div class="score" title="The scoreboard is satire. The facts in it are not.">
      <span>⚑ Excuse: {"on file" if d.get("official") else "none offered"}</span>
      <span>🕊 Response: condemnation &amp; concern</span><span>⚖ Sanctions: none</span><span>✈ Arms exports: uninterrupted</span></div>'''
    off = d.get('official')
    official = (f'<div class="official"><b>{off.get("flag", "🇮🇱")} Official response</b>'
                f'<a href="{e(off["url"])}" target="_blank" rel="noopener">{e(off["label"])}</a></div>') if off else ''
    wiki = (f'<div class="wiki"><b>Wikipedia</b><a href="{e(d["wikipedia"])}" target="_blank" rel="noopener">'
            f'{e(host(d["wikipedia"]))}{e(urlparse(d["wikipedia"]).path)}</a></div>') if d.get('wikipedia') else ''
    pager = '<nav class="pager">' + (f'<a href="/{prev["id"]}/">← {LABEL[prev["id"]]} {e(plain(prev["title"]))}</a>' if prev else '<span></span>') + \
            (f'<a href="/{nxt["id"]}/" style="text-align:right">{LABEL[nxt["id"]]} {e(plain(nxt["title"]))} →</a>' if nxt else '<span></span>') + '</nav>'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="The War Crimes Safari">
<meta property="og:title" content="{e(plain(d['title']))}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/site.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<nav id="topnav">
  <a class="brand" href="/" style="opacity:1">War Crimes Safari</a>
  <a href="/#top">Incidents</a>
  <a href="/#sec-closers">Closers</a>
  <a href="/#sec-docket">Docket</a>
  <a href="/#sec-hamas">Hamas</a>
  <a href="/al-ahli.html">Contested</a>
</nav>
<main class="page">
  <div class="crumbs"><a href="/">War Crimes Safari</a> › <a href="/{SECTION_ANCHOR[d['section']]}">{SECTION_NAME[d['section']]}</a> › {LABEL[d['id']]}</div>
  <h1><span class="num">{LABEL[d['id']]}</span>{d['title']}</h1>
  <div class="meta">{d['date']}</div>
  {'<ul class="why">' + ''.join(f'<li>{b}</li>' for b in d['bullets']) + '</ul>' if d.get('bullets') else ''}
  <p class="lede">{d['summary']}</p>
  {f'<div class="comment">{d["comment"]}</div>' if d.get('comment') else ''}
  {f'<div class="verify">⚠ {d["verify"]}</div>' if d.get('verify') else ''}
  {official}
  {wiki}
  {score}
  <section class="record">
    <h2>The record — {len(links)} sources</h2>
    <p class="sub">Date, publication and headline for each source, as the source itself published them. {"Forensic Architecture is pinned first; the rest" if fa else "Sorted"} by publication date. {dated} of {len(links)} dated; a blank means the publisher's page didn't expose it, and we don't guess.</p>
    <table class="sources">
      <thead><tr><th>Date</th><th>Publication</th><th>Headline</th></tr></thead>
      <tbody>
      {''.join(row(i, l) for i, l in enumerate(ordered))}
      </tbody>
    </table>
  </section>
  {pager}
  <footer>Permalink: <a href="{url}">{url}</a> · Data: <a href="/data.json">data.json</a> · Corrections: <a href="https://github.com/PlanetaryCouncil/warcrimes/issues" target="_blank" rel="noopener">open an issue</a></footer>
</main>
</body>
</html>
'''

def main():
    ids = {d['id'] for d in incidents}
    # remove pages for incidents that no longer exist (only dirs we generated: they contain a marker-free index.html next to nothing else)
    for p in ROOT.iterdir():
        if p.is_dir() and (p / 'index.html').exists() and p.name not in ids and p.name not in ('tools', '.git', '.claude'):
            if 'War Crimes Safari' in (p / 'index.html').read_text(): shutil.rmtree(p)
    for i, d in enumerate(ORDER):
        out = ROOT / d['id']; out.mkdir(exist_ok=True)
        (out / 'index.html').write_text(page(d, ORDER[i - 1] if i else None, ORDER[i + 1] if i + 1 < len(ORDER) else None))
    urls = [SITE + '/', SITE + '/al-ahli.html'] + [f'{SITE}/{d["id"]}/' for d in ORDER]
    (ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + ''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls) + '</urlset>\n')
    (ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
    print(f'built {len(ORDER)} pages')

if __name__ == '__main__':
    main()
