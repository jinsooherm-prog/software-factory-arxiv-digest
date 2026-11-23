#!/usr/bin/env python3
"""
Daily arXiv digest generator for "software factories" (AI coding agents,
autonomous SWE agents, agentic software engineering, LLM dev pipelines).

Format: ONE consolidated daily briefing (single flowing narrative covering
up to 10 papers, written by an LLM) rather than per-paper repeated cards.

Workflow:
  1. `candidates --hours 23` queries arXiv for the given lookback window and
     prints unseen papers (not already in state.json) as JSON.
  2. An LLM agent reads that JSON, picks up to 10 genuinely interesting /
     on-topic papers, and writes ONE cohesive briefing (headline + flowing
     HTML summary with inline links to each paper it mentions) into a
     briefing JSON file.
  3. `publish --briefing briefing.json --date YYYY-MM-DD` renders
     index.html (today's briefing, "current" page), archive/YYYY-MM-DD.html,
     and archive/index.html, and records the paper IDs as seen.
"""
import argparse
import datetime
import html
import json
import os
import re
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
    base = "https://export.arxiv.org/api/query"
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
    data = urllib.request.urlopen(req, timeout=90).read()
    root = ET.fromstring(data)
    entries = []
    for e in root.findall('atom:entry', NS):
        pub_el = e.find('atom:published', NS)
        title_el = e.find('atom:title', NS)
        summary_el = e.find('atom:summary', NS)
        id_el = e.find('atom:id', NS)
        if pub_el is None or title_el is None or summary_el is None or id_el is None:
            continue
        pub = datetime.datetime.strptime(pub_el.text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        title = re.sub(r'\s+', ' ', title_el.text.strip())
        summary = re.sub(r'\s+', ' ', summary_el.text.strip())
        link = id_el.text.strip()
        arxiv_id = link.rstrip('/').split('/')[-1]
        authors = [a.find('atom:name', NS).text for a in e.findall('atom:author', NS) if a.find('atom:name', NS) is not None]
        cats = [c.get('term') for c in e.findall('atom:category', NS)]
        entries.append({
            'id': arxiv_id, 'pub': pub.isoformat(), 'title': title,
            'summary': summary, 'link': link, 'authors': authors, 'cats': cats,
        })
    return entries


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {'seen_ids': [], 'history': []}


def save_state(state):
    with open(STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2)


def cmd_candidates(args):
    state = load_state()
    seen = set(state['seen_ids'])
    entries = fetch_arxiv()
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=args.hours)
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


PAGE_CSS = """
:root {
  color-scheme: dark;
  --bg: #07080c;
  --bg-grad: radial-gradient(1200px 600px at 15% -10%, #1b2a4a33, transparent 60%),
             radial-gradient(1000px 500px at 110% 0%, #4a1b4a33, transparent 55%),
             #07080c;
  --panel: #10131aee;
  --panel-border: #22283a;
  --text: #eef0f5;
  --muted: #8a93a8;
  --accent1: #6ee7ff;
  --accent2: #b899ff;
  --accent3: #ff9ecb;
  --good: #7ee8a0;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg-grad); color: var(--text); line-height: 1.65; min-height: 100vh;
}
::selection { background: #6ee7ff44; }

.topbar {
  position: sticky; top: 0; z-index: 20; backdrop-filter: blur(14px);
  background: #0a0c12cc; border-bottom: 1px solid var(--panel-border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.85rem 1.6rem;
}
.topbar .brand { display:flex; align-items:center; gap:0.6rem; font-weight: 700; letter-spacing: -0.01em; }
.topbar .brand .dot { width:10px; height:10px; border-radius:50%; background: linear-gradient(135deg,var(--accent1),var(--accent2)); box-shadow: 0 0 14px #6ee7ff99; }
.topbar nav a { color: var(--muted); text-decoration:none; font-size:0.9rem; margin-left:1.3rem; transition: color .15s; }
.topbar nav a:hover { color: var(--accent1); }

header.hero {
  text-align: center; padding: 5rem 1.5rem 3.2rem; position: relative; overflow: hidden;
}
header.hero::before {
  content: ""; position: absolute; inset: 0; pointer-events:none;
  background: radial-gradient(500px 240px at 50% 0%, #6ee7ff14, transparent 70%);
}
.eyebrow {
  display: inline-block; font-size: 0.75rem; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--accent1); background: #6ee7ff14; border: 1px solid #6ee7ff33; border-radius: 999px;
  padding: 0.35rem 0.9rem; margin-bottom: 1.3rem;
}
header.hero h1 {
  font-size: clamp(2.1rem, 5vw, 3.4rem); margin: 0 0 0.9rem; letter-spacing: -0.02em; font-weight: 800;
  background: linear-gradient(100deg, var(--accent1), var(--accent2) 55%, var(--accent3));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
header.hero p.sub { color: var(--muted); font-size: 1.08rem; max-width: 620px; margin: 0 auto; }
.meta-row { margin-top: 1.4rem; display:flex; gap:0.6rem; justify-content:center; flex-wrap:wrap; }
.chip {
  font-size: 0.78rem; color: var(--muted); border: 1px solid var(--panel-border); background: #ffffff06;
  padding: 0.3rem 0.8rem; border-radius: 999px;
}

main { max-width: 860px; margin: 0 auto; padding: 0 1.5rem 5rem; }

.briefing {
  background: linear-gradient(180deg, #ffffff09, #ffffff02), var(--panel);
  border: 1px solid var(--panel-border); border-radius: 22px;
  padding: 2.4rem 2.6rem; margin: 0 0 2.6rem; position: relative;
  box-shadow: 0 30px 80px -40px #000a, inset 0 1px 0 #ffffff0d;
}
.briefing .date-badge {
  display:inline-flex; align-items:center; gap:0.4rem; font-size:0.78rem; color: var(--good);
  background:#7ee8a014; border:1px solid #7ee8a033; padding:0.25rem 0.75rem; border-radius:999px; margin-bottom:1.1rem;
}
.briefing h2 { font-size: 1.6rem; margin: 0 0 1rem; letter-spacing: -0.01em; }
.briefing .prose { font-size: 1.04rem; color: #d6dae3; }
.briefing .prose p { margin: 0 0 1rem; }
.briefing .prose a { color: var(--accent1); text-decoration: none; border-bottom: 1px dotted #6ee7ff66; }
.briefing .prose a:hover { color: #fff; border-color: #fff; }

.papers-ref { margin-top: 2.2rem; padding-top: 1.6rem; border-top: 1px dashed var(--panel-border); }
.papers-ref h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin: 0 0 1rem; }
.paper-pill {
  display: flex; align-items: baseline; gap: 0.6rem; padding: 0.55rem 0; border-bottom: 1px solid #ffffff08;
  font-size: 0.92rem;
}
.paper-pill:last-child { border-bottom: none; }
.paper-pill a.title { color: var(--text); text-decoration: none; font-weight: 600; flex: 1; }
.paper-pill a.title:hover { color: var(--accent1); }
.paper-pill .cat { font-size: 0.72rem; color: var(--muted); background:#ffffff08; padding:0.15rem 0.55rem; border-radius:999px; white-space:nowrap; }

section.archive-section h2 { font-size: 1.3rem; margin: 0 0 1.2rem; }
.archive-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(190px,1fr)); gap: 0.8rem; }
.archive-card {
  background: var(--panel); border: 1px solid var(--panel-border); border-radius: 14px;
  padding: 1rem 1.1rem; text-decoration:none; color: var(--text); transition: transform .15s, border-color .15s;
}
.archive-card:hover { transform: translateY(-2px); border-color: #6ee7ff55; }
.archive-card .d { font-weight: 700; font-size: 0.95rem; }
.archive-card .n { color: var(--muted); font-size: 0.78rem; margin-top: 0.2rem; }

footer { text-align:center; color: var(--muted); font-size: 0.82rem; padding: 2.5rem 1.5rem 3rem; border-top: 1px solid var(--panel-border); margin-top: 1rem; }
footer a { color: var(--accent1); text-decoration:none; }
"""


def render_papers_ref(papers):
    items = []
    for p in papers:
        cats = ", ".join(p.get('cats', [])[:3])
        items.append(
            f'<div class="paper-pill"><a class="title" href="{esc(p["link"])}" target="_blank" rel="noopener">{esc(p["title"])}</a>'
            f'<span class="cat">{esc(cats)}</span></div>'
        )
    return "\n".join(items)


def render_topbar():
    return """
    <div class="topbar">
      <div class="brand"><span class="dot"></span> Software Factories</div>
      <nav><a href="#briefing">Briefing</a><a href="archive/index.html">Archive</a><a href="https://arxiv.org/list/cs.SE/recent" target="_blank" rel="noopener">arXiv cs.SE</a></nav>
    </div>
    """


def render_index(date_str, headline, summary_html, papers, history):
    updated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    archive_cards = "\n".join(
        f'<a class="archive-card" href="archive/{h["date"]}.html"><div class="d">{esc(h["date"])}</div>'
        f'<div class="n">{len(h["papers"])} papers</div></a>'
        for h in sorted(history, key=lambda x: x['date'], reverse=True)[:12]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Software Factories — Daily arXiv Briefing</title>
<meta name="description" content="A daily, single-briefing digest of the most interesting arXiv research on AI coding agents and autonomous software engineering.">
<style>{PAGE_CSS}</style>
</head>
<body>
{render_topbar()}
<header class="hero">
  <span class="eyebrow">Daily arXiv Briefing</span>
  <h1>Software Factories</h1>
  <p class="sub">One daily briefing on AI coding agents, autonomous software engineering, and the research shaping how software gets built by machines.</p>
  <div class="meta-row">
    <span class="chip">Updated {esc(updated)}</span>
    <span class="chip">Covers last 23h of arXiv</span>
    <span class="chip">Up to 10 papers/day</span>
  </div>
</header>
<main>
  <section class="briefing" id="briefing">
    <div class="date-badge">● {esc(date_str)}</div>
    <h2>{esc(headline)}</h2>
    <div class="prose">
      {summary_html}
    </div>
    <div class="papers-ref">
      <h3>Papers in this briefing ({len(papers)})</h3>
      {render_papers_ref(papers)}
    </div>
  </section>

  <section class="archive-section">
    <h2>Past briefings</h2>
    <div class="archive-grid">
      {archive_cards}
    </div>
  </section>
</main>
<footer>Generated automatically by a Hermes Agent daily cron job · one briefing a day, zero noise on days with nothing new · <a href="archive/index.html">full archive</a></footer>
</body>
</html>
"""


def render_archive_page(date_str, headline, summary_html, papers):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(date_str)} — Software Factories Briefing</title>
<style>{PAGE_CSS}</style>
</head>
<body>
{render_topbar()}
<header class="hero" style="padding:3.2rem 1.5rem 2rem;">
  <span class="eyebrow">Archived Briefing</span>
  <h1 style="font-size:2.1rem;">{esc(date_str)}</h1>
</header>
<main>
  <section class="briefing">
    <h2>{esc(headline)}</h2>
    <div class="prose">
      {summary_html}
    </div>
    <div class="papers-ref">
      <h3>Papers in this briefing ({len(papers)})</h3>
      {render_papers_ref(papers)}
    </div>
  </section>
</main>
<footer><a href="../index.html">&larr; Back to current briefing</a> &middot; <a href="index.html">All briefings</a></footer>
</body>
</html>
"""


def render_archive_index(history):
    cards = "\n".join(
        f'<a class="archive-card" href="{h["date"]}.html"><div class="d">{esc(h["date"])}</div>'
        f'<div class="n">{len(h["papers"])} papers</div></a>'
        for h in sorted(history, key=lambda x: x['date'], reverse=True)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive — Software Factories</title>
<style>{PAGE_CSS}</style>
</head>
<body>
{render_topbar()}
<header class="hero" style="padding:3.2rem 1.5rem 2rem;">
  <span class="eyebrow">Archive</span>
  <h1 style="font-size:2.1rem;">All briefings</h1>
</header>
<main>
  <section class="archive-section">
    <div class="archive-grid">
      {cards}
    </div>
  </section>
</main>
<footer><a href="../index.html">&larr; Back to current briefing</a></footer>
</body>
</html>
"""


def cmd_publish(args):
    with open(args.briefing) as f:
        b = json.load(f)
    papers = b['papers']
    if not papers:
        print("No papers in briefing, nothing to publish.")
        return
    papers = papers[:10]

    date_str = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    state = load_state()
    for p in papers:
        if p['id'] not in state['seen_ids']:
            state['seen_ids'].append(p['id'])

    history = [h for h in state.get('history', []) if h['date'] != date_str]
    history.append({'date': date_str, 'headline': b['headline'], 'papers': papers})
    state['history'] = history
    save_state(state)

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(os.path.join(ARCHIVE_DIR, f"{date_str}.html"), 'w') as f:
        f.write(render_archive_page(date_str, b['headline'], b['summary_html'], papers))
    with open(os.path.join(ARCHIVE_DIR, "index.html"), 'w') as f:
        f.write(render_archive_index(history))
    with open(os.path.join(ROOT, "index.html"), 'w') as f:
        f.write(render_index(date_str, b['headline'], b['summary_html'], papers, history))

    print(f"Published briefing for {date_str} covering {len(papers)} papers.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("candidates", help="fetch+filter unseen recent papers as JSON")
    c.add_argument("--hours", type=float, default=23)
    c.set_defaults(func=cmd_candidates)

    p = sub.add_parser("publish", help="render site from a briefing.json")
    p.add_argument("--briefing", required=True)
    p.add_argument("--date", default=None)
    p.set_defaults(func=cmd_publish)

    args = ap.parse_args()
    args.func(args)
