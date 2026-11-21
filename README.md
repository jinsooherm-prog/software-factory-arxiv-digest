# Software Factories — arXiv Daily Digest

A rolling digest of the most interesting recent arXiv papers on **AI coding
agents, autonomous software engineering, agentic software-engineering
pipelines, and LLM-driven software development** — broadly, "software
factories."

- **Live site:** https://jinsooherm-prog.github.io/software-factory-arxiv-digest/
- **Homepage** (`index.html`) always shows the current top-5 picks.
- **`archive/`** keeps one dated page per day this has run, plus an archive index.
- Updated automatically once a day by a Hermes Agent cron job when a new,
  relevant paper appears on arXiv (rolling 7-day lookback window,
  deduplicated against `state.json`).

## How it works

`scripts/generate_digest.py` has two subcommands:

- `candidates --days 7` — queries the arXiv API with a broad keyword set,
  filters to unseen papers from the last N days, and prints them as JSON for
  review/ranking.
- `publish --selections selections.json --date YYYY-MM-DD` — takes a curated
  shortlist (with a one-line "why" and a short summary per paper) and renders
  `index.html`, `archive/YYYY-MM-DD.html`, and `archive/index.html`, then
  records the chosen paper IDs in `state.json` so they aren't repeated.

The "pick the 5 most interesting + summarize" step is done by an LLM agent
reading the `candidates` output, not by a fixed heuristic.
