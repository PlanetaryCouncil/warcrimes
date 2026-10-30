#!/usr/bin/env python3
"""Generate one static page per incident at /<id>/index.html, plus sitemap.xml and robots.txt.

Run after editing data.json:  python3 tools/build.py
"""
import json, html, re, shutil, subprocess, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://warcrimes.planetarycouncil.org'
data = json.loads((ROOT / 'data.json').read_text())
incidents = data['incidents']
e = lambda s: html.escape(str(s or ''), quote=True)
path = lambda d: d.get('slug') or d['id']
is_fa = lambda u: 'forensic-architecture.org' in u
favicon = lambda u: f'https://www.google.com/s2/favicons?domain={urlparse(u).hostname}&sz=64'
host = lambda u: (urlparse(u).hostname or '').removeprefix('www.')

def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True).stdout

def last_updated():
    """Date each incident's entry last changed: the oldest run of commits, counting back from HEAD, in which
    the entry equals what is in data.json now. Uncommitted edits count as today."""
    today = datetime.date.today().isoformat()
    want = {d['id']: json.dumps(d, sort_keys=True) for d in incidents}
    out, open_ids = {i: today for i in want}, set(want)
    for line in git('log', '--format=%H %cs', '--', 'data.json').split('\n'):
        if not line or not open_ids: break
        sha, date = line.split()
        try: then = {d['id']: json.dumps(d, sort_keys=True) for d in json.loads(git('show', f'{sha}:data.json'))['incidents']}
        except ValueError: continue
        for i in list(open_ids):
            if then.get(i) == want[i]: out[i] = date
            else: open_ids.discard(i)
    return out
UPDATED = last_updated()
import hashlib
CSS = '/site.css?v=' + hashlib.sha256((ROOT / 'site.css').read_bytes()).hexdigest()[:8]  # cache-bust on every stylesheet change
file_updated = lambda f: (git('log', '-1', '--format=%cs', '--', f).strip() if not git('status', '--porcelain', '--', f).strip() else '') or datetime.date.today().isoformat()
nice_date = lambda iso: datetime.date.fromisoformat(iso).strftime('%-d %b %Y')

def labels():
    out, n = {}, 0
    for sec in ('main', 'closers'):
        for d in incidents:
            if d['section'] == sec: n += 1; out[d['id']] = f'{n:02d}'
    for sec, p in (('docket', 'D'), ('hamas', 'H'), ('propaganda', 'P')):
        for i, d in enumerate([d for d in incidents if d['section'] == sec]): out[d['id']] = f'{p}{i + 1}'
    return out
LABEL = labels()
ORDER = sorted(incidents, key=lambda d: (['main', 'closers', 'docket', 'hamas', 'propaganda'].index(d['section']), incidents.index(d)))
SECTION_NAME = {'main': 'Incidents', 'closers': 'Closers', 'docket': 'The Docket', 'hamas': 'Hamas', 'propaganda': 'Propaganda desk'}
SECTION_ANCHOR = {'main': '#top', 'closers': '#sec-closers', 'docket': '#sec-docket', 'hamas': '#sec-hamas', 'propaganda': '#sec-propaganda'}

def plain(s): return re.sub(r'<[^>]+>', '', s)
def first_sentence(s):
    s = plain(s); m = re.match(r'(.{80,300}?[.!?])\s', s)
    return (m.group(1) if m else s[:297] + '…')


# X handles for outlets we're confident about; anything else falls back to the outlet name
HANDLES = {
    'aljazeera.com': '@AJEnglish', 'cnn.com': '@CNN', 'bbc.co.uk': '@BBCWorld', 'bbc.com': '@BBCWorld',
    'nytimes.com': '@nytimes', 'washingtonpost.com': '@washingtonpost', 'theguardian.com': '@guardian',
    'reuters.com': '@Reuters', 'apnews.com': '@AP', 'nbcnews.com': '@NBCNews', 'cbsnews.com': '@CBSNews',
    'abcnews.go.com': '@ABC', 'npr.org': '@NPR', 'latimes.com': '@latimes', 'wsj.com': '@WSJ', 'time.com': '@TIME',
    'axios.com': '@axios', 'politico.com': '@politico', 'ft.com': '@FT', 'economist.com': '@TheEconomist',
    'middleeasteye.net': '@MiddleEastEye', 'independent.co.uk': '@Independent', 'telegraph.co.uk': '@Telegraph',
    'news.sky.com': '@SkyNews', 'haaretz.com': '@haaretzcom', 'timesofisrael.com': '@TimesofIsrael',
    'ynetnews.com': '@ynetnews', 'jpost.com': '@Jerusalem_Post', 'thejc.com': '@JewishChron', '972mag.com': '@972mag',
    'france24.com': '@France24_en', 'dw.com': '@dwnews', 'cbc.ca': '@CBCNews', 'thedailybeast.com': '@thedailybeast',
    'foxnews.com': '@FoxNews', 'theintercept.com': '@theintercept', 'propublica.org': '@ProPublica',
    'electronicintifada.net': '@intifada', 'mondoweiss.net': '@Mondoweiss', 'dropsitenews.com': '@DropSiteNews',
    'trtworld.com': '@trtworld', 'newarab.com': '@The_NewArab', 'commondreams.org': '@commondreams',
    'forensic-architecture.org': '@ForensicArchi', 'volkskrant.nl': '@volkskrant', 'forward.com': '@jdforward',
    'jta.org': '@JTAnews', 'cjr.org': '@CJR', 'hrw.org': '@hrw', 'amnesty.org': '@amnesty', 'ohchr.org': '@UNHumanRights',
    'icrc.org': '@ICRC', 'msf.org': '@MSF', 'who.int': '@WHO', 'unrwa.org': '@UNRWA', 'cpj.org': '@pressfreedom',
    'rsf.org': '@RSF_inter', 'honestreporting.com': '@HonestReporting',
}
def handle(l):
    u = urlparse(l['url']); h = (u.hostname or '').removeprefix('www.').removeprefix('edition.').removeprefix('m.')
    if h in ('x.com', 'twitter.com'):
        seg = u.path.strip('/').split('/')[0]
        if seg: return '@' + seg
    for k, v in HANDLES.items():
        if h == k or h.endswith('.' + k): return v
    return l['source']

# Source stance. Default is mainstream; a link may override with "stance" in data.json.
ISRAELI_GOV_HOSTS = ('idf.il', 'gov.il', 'mfa.gov.il', 'terrorism-info.org.il')
ISRAELI_GOV_X = {'idf', 'netanyahu', 'orenmarmorstein', 'ltc_ariella', 'israelmfa', 'israel', 'israelipm', 'idfspokesperson', 'avichayadraee', 'israelingeneva', 'cogatonline'}
PRO_ISRAEL_HOSTS = ('aipac.org', 'honestreporting.com', 'honestreporting.ca', 'washingtoninstitute.org', 'algemeiner.com', 'camera.org', 'ngo-monitor.org', 'jns.org', 'worldisraelnews.com', 'unwatch.org', 'israellycool.com')
PRO_ISRAEL_X = {'gazawood1'}
PRO_PAL_HOSTS = ('mondoweiss.net', 'electronicintifada.net', 'palestinechronicle.com', 'middleeastmonitor.com', 'alhaq.org', 'euromedmonitor.org', 'palestine-studies.org', 'hindrajabfoundation.org', 'wafa.ps', 'qudsnen.co')
PRO_PAL_X = {'mondoweiss', 'qudsnen', 'euromedhr'}
GAZA_GOV_HOSTS = ('shehabnews.com', 'alresalah.news')
STANCES = {
    'mainstream': ('Mainstream, international, UN & NGO', ''),
    'pro-palestinian': ('Palestinian & pro-Palestinian', ' (pro-Palestinian)'),
    'gaza-gov': ('Gaza authorities (Hamas-run) & Hamas-aligned media', ' (Hamas-aligned)'),
    'israeli-gov': ('Israeli government & military', ' (Israeli gov)'),
    'pro-israel': ('Pro-Israel advocacy', ' (pro-Israel)'),
}
def stance(l):
    if l.get('stance'): return l['stance']
    u = urlparse(l['url']); h = (u.hostname or '').removeprefix('www.')
    acct = u.path.strip('/').split('/')[0].lower() if h in ('x.com', 'twitter.com', 'facebook.com') else ''
    on = lambda hosts: any(h == x or h.endswith('.' + x) for x in hosts)
    if on(ISRAELI_GOV_HOSTS) or acct in ISRAELI_GOV_X: return 'israeli-gov'
    if on(PRO_ISRAEL_HOSTS) or acct in PRO_ISRAEL_X: return 'pro-israel'
    if on(GAZA_GOV_HOSTS): return 'gaza-gov'
    if on(PRO_PAL_HOSTS) or acct in PRO_PAL_X: return 'pro-palestinian'
    if l.get('tag') == 'propaganda': return 'pro-israel'
    return 'mainstream'
META_CACHE = json.loads((ROOT / 'tools' / 'meta_cache.json').read_text()) if (ROOT / 'tools' / 'meta_cache.json').exists() else {}

def tweet_line(l):
    tag = STANCES[stance(l)][1] + (' (propaganda)' if l.get('tag') == 'propaganda' else '')
    head = l.get('headline')
    return f'{handle(l)}{tag}: {l["url"]}' + (f' — {head}' if head else '')

def row(i, l):
    head = l.get('headline') or ''
    gd = '<span class="host" title="Headline as indexed by the GDELT Project; the publisher blocked direct retrieval, so punctuation may differ from the original.">(GDELT)</span>' if l.get('headline_via') == 'gdelt' else ('<span class="host" title="Title as recorded in the Wikipedia citation; the publisher blocked direct retrieval.">(via Wikipedia)</span>' if l.get('headline_via') == 'wikipedia' else '')
    h = (f'<a href="{e(l["url"])}" target="_blank" rel="noopener">{e(head)}</a>{gd}' if head
         else f'<a href="{e(l["url"])}" target="_blank" rel="noopener"><span class="nohead">headline not retrieved</span></a><span class="host">{e(host(l["url"]))}</span>')
    date = l.get('published') or '—'
    if l.get('tag') == 'propaganda':
        h += '<span class="tag-prop" title="Cited as an example of denial, not as evidence">propaganda</span>'
    return (f'<tr class="{"fa" if is_fa(l["url"]) else ""}{" prop" if l.get("tag") == "propaganda" else ""}"><td class="d">{e(date)}</td>'
            f'<td class="p"><img src="{favicon(l["url"])}" alt="" loading="lazy">{e(l["source"])}</td><td class="h">{h}</td>'
            f'<td class="x"><button class="cp" type="button" data-tweet="{e(tweet_line(l))}" title="Copy as tweet" aria-label="Copy as tweet">𝕏</button></td></tr>')

def page(d, prev, nxt):
    links = d['links']
    fa = [l for l in links if is_fa(l['url'])]
    rest = sorted([l for l in links if not is_fa(l['url'])], key=lambda l: (not l.get('published'), l.get('published') or ''))
    ordered = fa + rest
    off = d.get('official')
    machine_links = [l for l in ordered if stance(l) in ('israeli-gov', 'pro-israel')]
    if off and off['url'] not in {l['url'] for l in links}:
        m = META_CACHE.get(off['url'], {})
        machine_links.insert(0, {'url': off['url'], 'source': 'Official response', 'headline': m.get('headline') or off['label'],
                                 'published': m.get('published', ''), 'stance': 'israeli-gov'})
    record_links = [l for l in ordered if stance(l) not in ('israeli-gov', 'pro-israel')]
    def group_rows(ls, keys):
        out = ''
        for k in keys:
            g = [l for l in ls if stance(l) == k]
            if g:
                out += f'<tr class="grp"><td colspan="4">{STANCES[k][0]} · {len(g)}</td></tr>' + ''.join(row(0, l) for l in g)
        return out
    record_rows = group_rows(record_links, ('mainstream', 'pro-palestinian', 'gaza-gov'))
    machine_rows = group_rows(machine_links, ('israeli-gov', 'pro-israel'))
    machine = f'''<section class="record machine">
    <h2>Official government sources — {len(machine_links)} {"source" if len(machine_links) == 1 else "sources"}</h2>
    <p class="sub"><a href="/official-government-sources-exercise-extra-caution/"><b>Exercise extra caution.</b></a> The Israeli government's own statements and the pro-Israel advocacy that amplifies them, kept apart from the record above. Israel is a party to the war, its public-diplomacy budget roughly quintupled to $730 million in 2026, and its first accounts of several incidents here were later contradicted — so read them as one side's case, and check them. Labels describe each source's stance; <b>propaganda</b> marks what we cite as an example of denial, not as evidence.</p>
    <table class="sources">
      <thead><tr><th>Date</th><th>Publication</th><th>Headline</th><th></th></tr></thead>
      <tbody>{machine_rows}</tbody>
    </table>
  </section>''' if machine_links else ''
    dated = sum(1 for l in record_links if l.get('published'))
    url = f'{SITE}/{path(d)}/'
    desc = first_sentence(d['summary'])
    title = f'{plain(d["title"])} — War Crimes Safari'
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': plain(d['title'])[:110], 'description': desc,
          'url': url, 'isPartOf': {'@type': 'WebSite', 'name': 'The War Crimes Safari', 'url': SITE + '/'},
          'dateModified': UPDATED[d['id']],
          'citation': [l['url'] for l in ordered] + ([d['wikipedia']] if d.get('wikipedia') else [])}
    fig = d.get('figure')
    og_image = (f'<meta property="og:image" content="{SITE}{fig["src"]}">\n<meta name="twitter:card" content="summary_large_image">'
                if fig else '<meta name="twitter:card" content="summary">')
    # figure is the poster and social preview; figures (optional) adds more posters below it
    figure = ''.join(f'<figure class="poster"><h2>{e(f["title"])}</h2><a href="{f["src"]}"><img src="{f["src"]}" alt="{e(f["alt"])}" loading="lazy"></a>'
              f'<figcaption>{e(f["caption"])}' + (f' <a href="{e(f["credit"]["url"])}" target="_blank" rel="noopener">{e(f["credit"]["label"])}</a>' if f.get('credit') else '')
              + '</figcaption></figure>' for f in ([fig] if fig else []) + d.get('figures', []))
    vid = d.get('video')
    video = (f'<figure class="poster"><h2>{e(vid["title"])}</h2><video controls preload="none" playsinline poster="{vid["poster"]}" src="{vid["src"]}"></video>'
             f'<figcaption>{e(vid["caption"])}' + (f' <a href="{e(vid["credit"]["url"])}" target="_blank" rel="noopener">{e(vid["credit"]["label"])}</a>' if vid.get('credit') else '')
             + '.</figcaption></figure>') if vid else ''
    # optional dossier: [{heading, html?, table?{cols, rows}}] — profile sections for organisation pages
    dossier = ''.join(
        f'<section class="dossier"><h2>{s["heading"]}</h2>' + (s.get('html') or '')
        + ((f'<div class="tw"><table class="facts"><thead><tr>' + ''.join(f'<th>{c}</th>' for c in s['table']['cols']) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in s['table']['rows']) + '</tbody></table></div>'
            + (f'<p class="sub">{s["table"]["note"]}</p>' if s['table'].get('note') else '')) if s.get('table') else '')
        + '</section>' for s in d.get('dossier', []))
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
    pager = '<nav class="pager">' + (f'<a href="/{path(prev)}/">← {LABEL[prev["id"]]} {e(plain(prev["title"]))}</a>' if prev else '<span></span>') + \
            (f'<a href="/{path(nxt)}/" style="text-align:right">{LABEL[nxt["id"]]} {e(plain(nxt["title"]))} →</a>' if nxt else '<span></span>') + '</nav>'
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
{og_image}
<link rel="stylesheet" href="{CSS}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<nav id="topnav">
  <a class="brand" href="/" style="opacity:1">War Crimes Safari</a>
  <a href="/#top">Incidents</a>
  <a href="/#sec-closers">Closers</a>
  <a href="/#sec-docket">Docket</a>
  <a href="/#sec-hamas">Hamas</a>
  <a href="/#sec-propaganda">Propaganda</a>
  <a href="/talking-about-war-crimes-is-not-antisemitic/">Not antisemitic</a>
  <a href="/al-ahli.html">Contested</a>
</nav>
<main class="page">
  <div class="crumbs"><a href="/">War Crimes Safari</a> › <a href="/{SECTION_ANCHOR[d['section']]}">{SECTION_NAME[d['section']]}</a> › {LABEL[d['id']]}</div>
  <h1><span class="num">{LABEL[d['id']]}</span>{d['title']}</h1>
  <div class="meta">{d['date']} · <span class="updated">Last updated <time datetime="{UPDATED[d['id']]}">{nice_date(UPDATED[d['id']])}</time></span></div>
  {'<ul class="why">' + ''.join(f'<li>{b}</li>' for b in d['bullets']) + '</ul>' if d.get('bullets') else ''}
  <p class="lede">{d['summary']}</p>
  {f'<div class="comment">{d["comment"]}</div>' if d.get('comment') else ''}
  {f'<div class="verify">⚠ {d["verify"]}</div>' if d.get('verify') else ''}
  {official}
  {wiki}
  {score}
  {video}
  {figure}
  {dossier}
  <section class="record">
    <h2>The record — {len(record_links)} sources</h2>
    <p class="sub">Date, publication and headline for each source, as the source itself published them, grouped by stance. {"Forensic Architecture is pinned first; the rest" if fa else "Sorted"} by publication date. {dated} of {len(record_links)} dated; a blank means the publisher's page didn't expose it, and we don't guess.</p>
    <div class="tweetbar"><button class="cpall" type="button" data-head="{e(plain(d['title']))}&#10;{url}">𝕏 Copy all as tweet</button><span class="cpmsg" aria-live="polite"></span></div>
    <table class="sources">
      <thead><tr><th>Date</th><th>Publication</th><th>Headline</th><th></th></tr></thead>
      <tbody>
      {record_rows}
      </tbody>
    </table>
  </section>
  {machine}
  {pager}
  <footer>Permalink: <a href="{url}">{url}</a> · Data: <a href="/data.json">data.json</a> · Corrections: <a href="https://github.com/PlanetaryCouncil/warcrimes/issues" target="_blank" rel="noopener">open an issue</a></footer>
</main>
<script src="/copy.js"></script>
</body>
</html>
'''

STATIC_PAGES = ('talking-about-war-crimes-is-not-antisemitic', 'official-government-sources-exercise-extra-caution')  # hand-written pages listed in the sitemap
STATIC_DIRS = ('talking-about-war-crimes-is-not-antisemitic', 'official-government-sources-exercise-extra-caution', 'img', 'video', 'archive')  # hand-written pages and assets, never cleaned up

def main():
    ids = {d['id'] for d in incidents} | {path(d) for d in incidents}
    # remove pages for incidents that no longer exist (only dirs we generated: they contain a marker-free index.html next to nothing else)
    for p in ROOT.iterdir():
        if p.is_dir() and (p / 'index.html').exists() and p.name not in ids and p.name not in ('tools', '.git', '.claude') + STATIC_DIRS:
            if 'War Crimes Safari' in (p / 'index.html').read_text(): shutil.rmtree(p)
    for i, d in enumerate(ORDER):
        out = ROOT / path(d); out.mkdir(exist_ok=True)
        (out / 'index.html').write_text(page(d, ORDER[i - 1] if i else None, ORDER[i + 1] if i + 1 < len(ORDER) else None))
        if path(d) != d['id']:  # keep the short URL working: redirect to the keyword URL
            old = ROOT / d['id']; old.mkdir(exist_ok=True)
            target = f'/{path(d)}/'
            (old / 'index.html').write_text(f'<!doctype html><meta charset="utf-8"><title>War Crimes Safari — moved</title>'
                f'<link rel="canonical" href="{SITE}{target}"><meta name="robots" content="noindex">'
                f'<meta http-equiv="refresh" content="0; url={target}"><script>location.replace("{target}"+location.hash)</script>'
                f'<a href="{target}">{e(plain(d["title"]))}</a>\n')
    for f in ['index.html'] + [f'{x}/index.html' for x in STATIC_PAGES]:  # hand-written pages share the stylesheet
        fp = ROOT / f; t = fp.read_text(); n = re.sub(r'href="/?site\.css(\?v=\w+)?"', f'href="{CSS}"', t)
        if n != t: fp.write_text(n)
    urls = ([(SITE + '/', max(UPDATED.values())), (SITE + '/al-ahli.html', file_updated('al-ahli.html'))]
            + [(f'{SITE}/{x}/', file_updated(f'{x}/index.html')) for x in STATIC_PAGES] + [(f'{SITE}/{path(d)}/', UPDATED[d['id']]) for d in ORDER])
    (ROOT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + ''.join(f'  <url><loc>{u}</loc><lastmod>{m}</lastmod></url>\n' for u, m in urls) + '</urlset>\n')
    (ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
    print(f'built {len(ORDER)} pages')

if __name__ == '__main__':
    main()
