# scalyn.si — Agent 2: Target Market Researcher

Python market-research prototype with a web dashboard, public search-index discovery, heuristic prospect qualification, and Excel/CSV/JSON exports.

## Run locally

Use Python 3.10 or later. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r agent_2_market_researcher/requirements.txt
python -m agent_2_market_researcher.web.server
```

Open <http://127.0.0.1:8000/dashboard>. Set `PORT` in the process environment to choose another port. Generated research files are stored under `agent_2_market_researcher/output/` and are excluded from Git.

The default workflow uses Python rules and templates without an LLM. Search requires internet access, and providers may challenge or block requests. Optional Gemini hooks require additional SDK/model validation; see the architecture guide for details.

## Documentation

Open [`agent_architecture_explainer.html`](agent_architecture_explainer.html) directly in a browser. It contains embedded styles, fonts, diagrams, a pipeline walkthrough, query inspector, and source-grounded limitations. It works offline.

## Regression checks

```powershell
python -m unittest agent_2_market_researcher.tests.test_live_features -v
node --test agent_2_market_researcher/tests/dashboard_actions.test.cjs
```

Node.js is needed for dashboard JavaScript checks. The older `test_scout.py` suite includes live-network behavior and two known query-planner expectation failures.

## Project layout

- `agent_2_market_researcher/web/`: dashboard and HTTP API
- `agent_2_market_researcher/core/`: schemas, planning, qualification, pitch templates, and exports
- `agent_2_market_researcher/tools/`: ingestion, search, signal detection, and workbook persistence
- `agent_2_market_researcher/tests/`: fixtures and regression checks
- `resources/`: project design and planning references

Indexed URLs can be real while personas, locations, need signals, competitor notes, and pitches remain inferred. Review supporting evidence before treating an exported row as a qualified lead.

Local credentials, environment files, caches, logs, and generated lead data are intentionally excluded from this repository.
