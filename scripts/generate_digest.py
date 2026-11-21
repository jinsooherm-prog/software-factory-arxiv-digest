#!/usr/bin/env python3
"""
Daily arXiv digest generator for "software factories" (AI coding agents,
autonomous SWE agents, agentic software engineering, LLM dev pipelines).

Workflow:
  1. Query arXiv API for recent papers matching a broad keyword set.
  2. Filter to papers published in the last N days not already in state.json.
  3. Rank candidates (simple heuristic: category match + recency) and emit a
     shortlist for an LLM (or human) to pick the "5 most interesting" and
     write one-paragraph summaries into selections.json.
  4. Render index.html (rolling top 5) + archive/YYYY-MM-DD.html + archive/index.html.

This script does the mechanical fetch/filter/render. The "pick interesting +
summarize" step is meant to be driven by the agent (Hermes) reading
candidates.json and writing selections.json, OR by the --auto fallback
below which does an extractive stub summary if no selections.json is given.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(ROOT, "state.json")
ARCHIVE_DIR = os.path.join(ROOT, "archive")

KEYWORDS = [
    'software factory', 'software factories', 'software agent', 'coding agent',
    'autonomous software engineering', 'agentic software engineering',
    'LLM agent software development', 'AI software engineer',
    'autonomous coding', 'multi-agent software development',
    'code generation agent pipeline', 'coding agents',
]

NS = {'atom': 'http://www.w3.org/2005/Atom'}


def fetch_arxiv(max_results=150):
    base = "http://export.arxiv.org/api/query"
    search_query = "(" + " OR ".join(f'all:"{k}"' for k in KEYWORDS) + ")"
    params = {
        'search_query': search_query,
        'start': 0,
        'max_results': max_results,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
    }
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = urllib.request.urlopen(req, timeout=30).read()
    root = ET.fromstring(data)
    entries = []
    for e in root.findall('atom:entry', NS):
        pub_str = e.find('atom:published', NS).text
        pub = datetime.datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        title = re.sub(r'\s+', ' ', e.find('atom:title', NS).text.strip())
        summary = re.sub(r'\s+', ' ', e.find('atom:summary', NS).text.strip())
        link = e.find('atom:id', NS).text.strip()
        arxiv_id = link.rstrip('/').split('/')[-1]
        authors = [a.find('atom:name', NS).text for a in e.findall('atom:author', NS)]
        cats = [c.get('term') for c in e.findall('{http://arxiv.org/schemas/atom}category', NS)] if False else \
               [c.get('term') for c in e.findall('atom:category', NS)]
        entries.append({
            'id': arxiv_id, 'pub': pub.isoformat(), 'title': title,
            'summary': summary, 'link': link, 'authors': authors, 'cats': cats,
        })
    return entries


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'seen_ids': [], 'history': []}  # history: list of {date, papers: [...]}


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def cmd_candidates(args):
    """Fetch + filter new, unseen papers from the last N days; dump JSON for review."""
    state = load_state()
    seen = set(state['seen_ids'])
    entries = fetch_arxiv()
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(days=args.days)
    out = []
    for e in entries:
        pub = datetime.datetime.fromisoformat(e['pub'])
        if pub < cutoff:
            continue
        if e['id'] in seen:
            continue
        out.append(e)
    out.sort(key=lambda x: x['pub'], reverse=True)
    print(json.dumps(out, indent=2))


def esc(s):
    return html.escape(s, quote=True)


def render_paper_card(p):
    authors = ", ".join(p.get('authors', [])[:6])
    if len(p.get('authors', [])) > 6:
        authors += ", et al."
    cats = ", ".join(p.get('cats', []))
    return f"""
    <article class="card">
      <h3><a href="{esc(p['link'])}" target="_blank" rel="noopener">{esc(p['title'])}</a></h3>
      <div class="meta">{esc(authors)} &middot; {esc(cats)} &middot; {esc(p['pub'][:10])}</div>
      <p class="why">{esc(p.get('why', ''))}</p>
      <p class="summary">{esc(p.get('summary_text', p.get('summary', '')))}</p>
      <a class="abs-link" href="{esc(p['link'])}" target="_blank" rel="noopener">View on arXiv &rarr;</a>
    </article>
    """


PAGE_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0b0d12; color: #e6e8ee; line-height: 1.55;
}
header { padding: 3rem 1.5rem 2rem; text-align: center; border-bottom: 1px solid #1c212c; }
header h1 { font-size: 1.9rem; margin: 0 0 0.4rem; background: linear-gradient(90deg,#7dd3fc,#a78bfa); -webkit-background-clip: text; background-clip: text; color: transparent; }
header p { color: #9aa4b2; margin: 0.2rem 0; }
nav.top { text-align: center; padding: 0.8rem; font-size: 0.9rem; }
nav.top a { color: #7dd3fc; text-decoration: none; margin: 0 0.6rem; }
nav.top a:hover { text-decoration: underline; }
main { max-width: 820px; margin: 0 auto; padding: 1rem 1.5rem 4rem; }
.card {
  background: #11141b; border: 1px solid #1c212c; border-radius: 14px;
  padding: 1.4rem 1.6rem; margin: 1.4rem 0;
}
.card h3 { margin: 0 0 0.4rem; font-size: 1.15rem; }
.card h3 a { color: #e6e8ee; text-decoration: none; }
.card h3 a:hover { color: #7dd3fc; }
.meta { font-size: 0.8rem; color: #7b8494; margin-bottom: 0.7rem; }
.why { color: #a78bfa; font-weight: 600; font-size: 0.9rem; margin: 0.3rem 0; }
.summary { color: #c6cad3; font-size: 0.95rem; }
.abs-link { display: inline-block; margin-top: 0.6rem; font-size: 0.85rem; color: #7dd3fc; text-decoration: none; }
.abs-link:hover { text-decoration: underline; }
footer { text-align: center; color: #5c6476; font-size: 0.8rem; padding: 2rem 0; }
.archive-list { list-style: none; padding: 0; }
.archive-list li { margin: 0.5rem 0; }
.archive-list a { color: #7dd3fc; text-decoration: none; }
.archive-list a:hover { text-decoration: underline; }
.badge { display:inline-block; background:#1c212c; color:#9aa4b2; border-radius:999px; padding:0.15rem 0.7rem; font-size:0.75rem; margin-left:0.5rem; }
"""


def render_index(latest_date, latest_papers, history):
    cards = "\n".join(render_paper_card(p) for p in latest_papers)
    archive_items = "\n".join(
        f'<li><a href="archive/{h["date"]}.html">{h["date"]}</a> <span class="badge">{len(h["papers"])} papers</span></li>'
        for h in sorted(history, key=lambda x: x['date'], reverse=True)
    )
    updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Software Factories — arXiv Daily Digest</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<header>
  <h1>Software Factories — arXiv Daily Digest</h1>
  <p>Top 5 most interesting recent papers on AI coding agents, autonomous software engineering, and agentic dev pipelines.</p>
  <p>Last updated: {updated} &middot; latest digest date: {esc(latest_date)}</p>
</header>
<nav class="top"><a href="#top5">Current Top 5</a><a href="archive/index.html">Full Archive</a><a href="https://arxiv.org/list/cs.SE/recent" target="_blank" rel="noopener">arXiv cs.SE</a></nav>
<main>
  <h2 id="top5">Current Top 5 ({esc(latest_date)})</h2>
  {cards}
  <h2>Archive</h2>
  <ul class="archive-list">
    {archive_items}
  </ul>
</main>
<footer>Generated automatically by a Hermes Agent daily cron job. Source keywords cover AI coding agents / agentic software engineering / software factories broadly.</footer>
</body>
</html>
"""


def render_archive_page(date_str, papers):
    cards = "\n".join(render_paper_card(p) for p in papers)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(date_str)} — Software Factories Digest</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<header>
  <h1>Software Factories Digest</h1>
  <p>{esc(date_str)}</p>
</header>
<nav class="top"><a href="../index.html">Home</a><a href="index.html">Archive index</a></nav>
<main>
  {cards}
</main>
<footer>Generated automatically by a Hermes Agent daily cron job.</footer>
</body>
</html>
"""


def render_archive_index(history):
    items = "\n".join(
        f'<li><a href="{h["date"]}.html">{h["date"]}</a> <span class="badge">{len(h["papers"])} papers</span></li>'
        for h in sorted(history, key=lambda x: x['date'], reverse=True)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive — Software Factories Digest</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<header><h1>Digest Archive</h1></header>
<nav class="top"><a href="../index.html">Home</a></nav>
<main>
<ul class="archive-list">
{items}
</ul>
</main>
</body>
</html>
"""


def cmd_publish(args):
    """Consume a selections.json (list of chosen papers with 'why' and 'summary_text'),
    append to state/history, write index.html + archive pages."""
    with open(args.selections) as f:
        selections = json.load(f)
    if not selections:
        print("No selections given, nothing to publish.")
        return

    date_str = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    state = load_state()

    # mark these ids as seen
    for p in selections:
        if p['id'] not in state['seen_ids']:
            state['seen_ids'].append(p['id'])

    # update history (one entry per date; if rerun same day, replace)
    history = [h for h in state.get('history', []) if h['date'] != date_str]
    history.append({'date': date_str, 'papers': selections})
    state['history'] = history
    save_state(state)

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(os.path.join(ARCHIVE_DIR, f"{date_str}.html"), 'w') as f:
        f.write(render_archive_page(date_str, selections))
    with open(os.path.join(ARCHIVE_DIR, "index.html"), 'w') as f:
        f.write(render_archive_index(history))
    with open(os.path.join(ROOT, "index.html"), 'w') as f:
        f.write(render_index(date_str, selections, history))

    print(f"Published digest for {date_str} with {len(selections)} papers.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("candidates", help="fetch+filter unseen recent papers as JSON")
    c.add_argument("--days", type=int, default=7)
    c.set_defaults(func=cmd_candidates)

    p = sub.add_parser("publish", help="render site from a selections.json")
    p.add_argument("--selections", required=True)
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_publish)

    args = ap.parse_args()
    args.func(args)
