# MeerKAT Ops Assistant (Tier 1 — RAG Q&A)

**Private/internal project — not for the public GitHub portfolio.**

A retrieval-augmented Q&A tool over the operator manual, handover notes, and
weekly summaries, so an on-shift operator can ask "what's the procedure for
resetting an AP" or "when was the last global sync" instead of hunting
through documents while also watching KATGUI.

## Data governance — read this first

This tool will index real SKAO/MeerKAT operational documents. Before putting
any real manual, handover note, or sensor log into this tool:

1. **Check with your manager / data owner** whether these documents may be
   processed by an LLM at all, and whether an external API (Anthropic,
   OpenAI, etc.) is acceptable or whether it must stay fully local.
2. Until that's confirmed, this project defaults to a **fully local,
   retrieval-only mode** — no document content leaves your machine, and no
   LLM generation happens at all (see "Modes" below).
3. `docs/` and `data/` are gitignored. Never commit real operational
   documents to this repo, even privately — treat it as local-only.

## Modes

- **`retrieval` (default, safest)** — no LLM call at all. Given a question,
  returns the most relevant passages from your documents verbatim, with
  source file + section. Purely extractive, nothing sent anywhere.
- **`local_llm`** — routes retrieved passages + your question through a
  local model via [Ollama](https://ollama.com) (e.g. `llama3`). Still
  nothing leaves your machine, but answers are synthesized rather than raw
  extracts.
- **`api_llm`** — routes through an external API. **Do not enable this
  until data governance sign-off** (see above). Disabled by default in
  `config.yaml`.

## Setup

```bash
pip install -r requirements.txt
```

**Try it first with the bundled example** (safe, no real data):

```bash
cp example_docs/sample_manual.md docs/
python scripts/build_index.py
python src/cli.py
# try asking: "how often do I need to run a global sync?"
```

Then delete `docs/sample_manual.md` and drop your real documents (manual,
handover notes, weekly summaries — .md, .txt, .pdf, .docx) into `docs/`
instead. Then rebuild the index:

```bash
python scripts/build_index.py
```

Then ask questions:

```bash
python src/cli.py
```

## Project Structure

```
meerkat-ops-assistant/
├── docs/                 # your real documents go here (gitignored)
├── data/vector_store/    # built index (gitignored)
├── src/
│   ├── ingest.py         # load + chunk documents
│   ├── vector_store.py   # embed + search (sentence-transformers/FAISS, TF-IDF fallback)
│   ├── llm_provider.py   # pluggable generation backend (retrieval-only / Ollama / API)
│   ├── rag.py            # orchestrates retrieve -> (optionally) generate, with citations
│   └── cli.py            # interactive Q&A loop
├── scripts/build_index.py
├── tests/
├── config.yaml
└── requirements.txt
```

## Roadmap

- [x] Tier 1: RAG Q&A over static docs
- [x] Tier 2 (in progress): command/note logger + JIRA ticket fetching — see below.
      Draft-generation (combining these into an actual handover note) is next.
- [ ] Tier 3: Sensor anomaly flagging (reuses LSTM autoencoder approach from
      `telemetry-anomaly-detection`)

## Tier 2 — Shift logger + JIRA citing (dummy data, safe to use now)

Both pieces below run entirely on dummy/mock data — no real Jira credentials,
no real shift data required. Safe to try before any manager sign-off.

### Shift logger (`oplog`)

Tags what issue you're working on, logs notes, and logs commands (with
captured output) — all to a local JSONL file, nothing sent anywhere.

```bash
python src/oplog.py tag "M030 pointing drift"
python src/oplog.py note "Confirmed encoder drift, not mechanical"
python src/oplog.py run -- python check_status.py --antenna m030
python src/oplog.py show
```

Logs land in `data/shift_logs/YYYY-MM-DD.jsonl` (gitignored). Each entry
carries whatever tag was most recently set, so entries from an issue can
later be grouped together automatically when drafting a handover note.

### JIRA ticket fetching (mock mode by default)

```python
from jira_client import build_jira_client

client = build_jira_client(mode="mock")   # no network, uses example_docs/dummy_jira_tickets.json
for ticket in client.fetch_tickets(project_key="OPS"):
    print(ticket.line(), ticket.cite())
```

To eventually wire up a real Jira instance: copy `.env.example` to `.env`,
fill in `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (a Jira API token,
not your password), and switch `jira.mode` in `config.yaml` from `mock` to
`live`. **Don't do this until data governance is cleared** — same caution
as loading real docs.

### Not built yet

Combining shift-log entries + JIRA tickets + previous handover note into an
actual draft document. That's the next piece — the shift logger and JIRA
client above are the inputs it'll need.

## KPI framing (for when you pitch this internally)

Track before/after: average time operators spend searching the manual or
Slack history per shift, number of Friday/Monday summary drafting hours,
handover note completeness/accuracy at shift changeover. Even a small pilot
with 2-3 operators over a few weeks gives you real numbers to present.
