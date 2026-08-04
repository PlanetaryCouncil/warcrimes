# The War Crimes Safari

Documented war crimes and related repression — Gaza & the West Bank, 2023–2026.
Goal: **the most-documented war crimes record in history.** Every claim independently sourced.

## Files

- **`data.json`** — the canonical dataset. 33 entries: 18 main incidents (incl. the Doha negotiator strike), 3 closers, 10 docket individuals, 2 Hamas entries (Oct 7 crimes; designations and support bans). 330+ sources. The page is just a renderer; all curation happens here.
- **`coverage.json`** — the press-coverage matrix: per event, article counts per major international outlet (GDELT DOC 2.0, English-language, ~30-outlet whitelist, event-specific query + date window). Rows GDELT throttled are flagged `not_measured` — never read a flagged row as a coverage gap. This is the dataset for coverage-pattern analysis.
- **`press-articles.json`** — the full article corpus behind the matrix (URL, outlet, title, date per article).
- **`index.html`** — static renderer, no dependencies. Serve the folder over HTTP (`python3 -m http.server 8315`) and open `localhost:8315`. Every card is deep-linkable: `/#hind-rajab`, `/#flour-massacre`, …
- `.claude/launch.json` — dev server config.

## Schema (per incident)

| field | meaning |
|---|---|
| `id` | stable slug, also the page anchor |
| `section` | `main`, `closers`, `docket`, or `hamas` |
| `comment` | optional curator's note, rendered as an accent-bar italic block |
| `title`, `date` | sober factual title; date or range |
| `summary` | 2 sentences, attributed ("according to…") |
| `links` | `[{url, source}]` — independent sources. **Add as many as you find; 3 is the floor, not the ceiling.** |
| `wikipedia` | most relevant Wikipedia article |
| `official` | `{url, label}` — the official Israeli response, primary source where one exists (gov.il / idf.il / official X) |
| `image` | `{src, page, credit, license}` — freely licensed embed (Wikimedia Commons only) |
| `photo` | `{url, source}` — link out to an iconic copyrighted photo when no free image exists |
| `verify` | open curation caveat, rendered as ⚠ on the card |

## Roadmap

1. **Curation pass** — resolve the ⚠ flags (the "rocket jump" clip identification; the malformed Doctors Under Fire full-film YouTube ID `iv3wpeJ6Ocos`); swap in your preferred video links from the sheet.
2. **The Docket (accountability section)** — the "prosecute the top 20" piece, grounded in documented proceedings, not our own accusations: ICC arrest warrants (Netanyahu, Gallant — 21 Nov 2024), the ICJ genocide case and the officials whose statements it cites, universal-jurisdiction complaints (Hind Rajab Foundation has filed against dozens of soldiers), commanders named in published investigations. Each person: role, documented acts/statements, proceeding, sources — same JSON discipline.
3. **Lebanon section** — from the sheet: villa, bridges, ambulance double-tap, solar panels, nun, Jesus smash, monastery. Same pipeline (one research agent per item).
4. **Evidence hardening** — add an `archive` field per link (archive.org snapshot of every source, so link-rot can't erase the record); tag sources by type (`news / un / ngo / primary / video`).
5. **Publish** — `git init`, GitHub Pages or a domain. The JSON-first structure means others can fork, verify, and extend the dataset.

## Image principle

We are an independent site with no budget to license professional photography. Images exist to make the record visible: we attribute truthfully and openly, always link the original source, and stay as close to legal as the record allows. In the moral dilemma between exposing war crimes and deferring to copyright law, we chose the side of maximum impact — that is our principle. If your work appears here and you object, open a GitHub issue and we will simply remove it — though we would rather you saw it as your work bearing witness, credited, where it matters.

## Method

Built with parallel research agents: every incident researched independently; every link appeared literally in search results (never constructed); images embedded only when freely licensed on Wikimedia Commons, with credit + license shown; official Israeli responses linked as primary sources wherever one exists.
