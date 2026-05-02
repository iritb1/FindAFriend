# Animal Adoption Assistant

This is a conversational AI agent that helps people find a dog or cat to adopt from rescue shelters. The user describes what they're looking for in free text — *"young friendly female dog"*, *"חתול שחור רגוע"*, *"a calm cat that's good with kids"* — and the agent returns the best matches from a live-scraped catalog with the gaps explained honestly.

Built with **React + Tailwind** (frontend), **FastAPI + LangGraph + OpenAI GPT-4o** (agent), and a **Playwright + LLM** scraper that pulls real listings from `yad4.co.il`. - god bless claude code, but I chose the nice colors.

---

## Project layout

```
.
├── backend/          # Python: API, agent, scraper
│   ├── agent/        # LangGraph orchestration + matcher
│   ├── api/          # FastAPI app
│   ├── ingestion/    # Playwright scraper + LLM extraction
│   ├── utils/        # Singleton + logger
│   ├── data/
│   │   └── animals.json   # Scraper output, matcher input
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── frontend/         # React + Vite + Tailwind
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.ts
```

---

## Architecture

### The agent — LangGraph

```
User question
      |
      v
  guard_node            "Is this an adoption conversation?"
      |
   in_scope?
   /        \
  YES        NO
  |           |
  v           v
extract_node  refusal_node    Fixed redirect, no LLM call
  |               |
  v               END
match_node        Deterministic Python over data/animals.json
  |
  v
answer_node       LLM presents matches with reasons + missing
  |
 END
```

| Node          | Purpose                                                                                                                                  | LLM? |
|---------------|------------------------------------------------------------------------------------------------------------------------------------------|------|
| `guard_node`  | Classifies the latest user message as `in_scope` or `off_topic`. Default-on-anything-else: `off_topic`.                                  | yes  |
| `extract_node`| `with_structured_output(AdoptionQuery)` — extracts `animal_type`, `gender`, `breed`, `color`, `age_preference`, `personality_traits`, `free_text`. | yes  |
| `match_node`  | Calls `matcher.find_matches(query)` — pure Python; no LLM.                                                                               | no   |
| `answer_node` | Composes a friendly reply from the scored matches.                                                                                       | yes  |
| `refusal_node`| Returns a fixed "I only help with adoption searches" message.                                                                            | no   |

Multi-turn refinement is supported via `MemorySaver` keyed on `thread_id`.

### The matcher — `backend/agent/matcher.py`

Two-stage scoring:

**Hard filters** — animal is excluded entirely if any fail:
- `animal_type` (dog vs cat) when the query specified one
- `gender` (male vs female) when the query specified one

**Soft scoring** — animals that pass the hard filters get scored:
- `age_preference` ↔ Hebrew age string heuristic (`"5 חודשים"` → puppy/young, `"3 שנים"` → adult, etc.)
- `breed` ↔ animal's breed/raw_text, with English→Hebrew breed mapping (`"husky"` matches `"האסקי"`)
- `color` ↔ same, with English→Hebrew color mapping (`"white"` matches `"לבן"`)
- `personality_traits` ↔ Hebrew trait keywords (`"calm"` matches `"רגוע"`, `"רגועה"`, `"שקט"`, `"שקטה"`...)
- Free-text overlap against the animal's combined text fields

Mismatches are recorded in `missing_or_uncertain`, so the answer node can be honest: *"Bella is a great match, but the description doesn't mention being good with cats."*

### The scraper — `backend/ingestion/scraper.py`

Real browser, real data. The flow:

1. **Playwright (Chromium headless)** opens `yad4.co.il/search?type=כלב` and `?type=חתול`.
2. **Auto-scrolls** the page so lazy-loaded cards hydrate.
3. **Heuristic card detection** — collects every `<a>` whose text contains a Hebrew gender word (`זכר`/`נקבה`) AND either a "details" button or an age-word hint (`שנים`/`חודשים`).
4. For each card: extract image URL, profile URL, raw text.
5. **LLM extraction** (`gpt-4o-mini` via OpenAI structured outputs) normalizes the raw Hebrew text into `AnimalExtraction` (name, gender, age, breed, color, size, description).
6. **Atomic write** to `backend/data/animals.json`.

Hebrew is preserved everywhere — names, descriptions, breed labels — so nothing gets lost in translation. The matcher does Hebrew↔English bridging via static lookup tables (see `agent/constants.py`).

---

## Quick start

### Prerequisites
- Docker (or: Python 3.12+, Node 20+, Chromium for the scraper).
- An OpenAI API key in `backend/.env`.

### With Docker (recommended)

```bash
cd backend
docker compose up --build
```

Builds the React frontend in stage 1, copies the bundle into a slim Python image in stage 2, starts the API. Open:

- **UI**: http://localhost:8000
- **Swagger**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Local dev (hot reload)

Two terminals:

**Terminal 1 — backend:**
```bash
cd backend
python -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
playwright install chromium    # one-time, for the scraper
PYTHONPATH=. uvicorn api.main:app --reload
```

**Terminal 2 — frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Scraping fresh data

```bash
cd backend
PYTHONPATH=. python -m ingestion.scraper
```

Hits `yad4.co.il`, runs 60 cards through `gpt-4o-mini`, writes `data/animals.json`.

---

## API

### `GET /health`
```json
{"status": "ok"}
```

### `POST /chat`
First message creates a `thread_id`; pass it back to continue.

```jsonc
// First message
POST /chat
{"message": "I'm looking for a young friendly female dog"}

// Response
{
  "answer": "Here are some great matches!\n\n🐾 **מאצ'ה** — female, 4 months ...",
  "thread_id": "a1b2c3d4-…"
}

// Follow-up — same conversation
POST /chat
{"message": "any of them good with kids?", "thread_id": "a1b2c3d4-…"}
```

---

## Tests

```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

| File                  | Tests | What it covers                                                       |
|-----------------------|-------|----------------------------------------------------------------------|
| `test_match_node.py`  | 7     | Hard-filter exclusion, soft-score reasons, Hebrew↔English mapping. **No LLM mocks** — `score_animal` is pure Python. |
| `test_extract_node.py`| 2     | LLM is mocked; verifies `with_structured_output(AdoptionQuery)` plumbing. |
| `test_guard_node.py`  | 3     | LLM is mocked; verifies in_scope / off_topic / default-on-garbage.   |
| `test_api.py`         | 4     | health endpoint, off-topic refusal, input validation (422 on empty/oversized). |

---

## Design decisions

### Hebrew is the source of truth
The shelter site is Hebrew. Names, descriptions, and breed labels stay in Hebrew throughout the pipeline. The matcher bridges via static lookup tables (`HEBREW_TRAIT_KEYWORDS`, `ENGLISH_TO_HEBREW_BREEDS`, `ENGLISH_TO_HEBREW_COLORS`) — far cheaper and more deterministic than asking the LLM to translate everything per request.

### Hard filter on `animal_type`, soft-score the rest
Asking for a dog must never return cats. Everything else is fuzzy — partial matches with explained gaps are useful, not noise. Gender is the only other hard filter (people who say "female cat" mean it).

### Real browser for the scraper
`yad4.co.il` is React-rendered. Static HTML fetches return an empty shell. Playwright is the right tool — adds a Chromium dep but it's a one-shot scrape, not a runtime concern.

### LLM only where it adds value
| Where               | Approach              | Why                                                                  |
|---------------------|-----------------------|----------------------------------------------------------------------|
| Card discovery      | Hebrew heuristic     | Free, deterministic, robust to React class-name churn.               |
| Field extraction    | gpt-4o-mini structured output | Hebrew text is messy; LLM normalizes name/age/breed cheaply. |
| Trait/color matching| Static lookup tables | No need to call LLM per match — Hebrew→English mappings are stable.  |
| User intent (`AdoptionQuery`) | gpt-4o structured output | The hard part; multilingual + open-ended.                |
| Final reply         | gpt-4o               | Tone, language, and explanation of gaps.                              |

### JSON, not a database
~60 records, one-shot scrape. `lru_cache` over the JSON file is faster, simpler, and more debuggable than running Postgres. Easy to swap to a DB if multiple shelters or live updates land.

### Frontend separated from backend
React app under `frontend/`, Python API under `backend/`. Multi-stage Dockerfile builds both. In dev: Vite dev server proxies `/chat` → backend.

---

## Lets talk about Improvements

### Scraper hardening (intentionally minimal today)
- **Tests** with saved HTML fixtures + mocked LLM — currently smoke-tested only.
- **Retry/backoff** (`tenacity`) around `polite_get` and `extract_animal_with_llm`.
- **Concurrent fetches** via `asyncio.gather` with a semaphore.
- **More shelters** — add another source dict and the scraper handles it.

### Matching depth
- **Animal cards** in the UI rendered from a structured `full_matches` field on `ChatResponse`, instead of (or alongside) the markdown answer.
- **Streaming the answer** via LangGraph `astream_events` — token-by-token rendering instead of waiting for the full reply.
### Production hardening
- **Rate limiting** + an API key on `/chat`.
- **Structured logs** (JSON + trace IDs).
- **LangSmith tracing** — drop-in observability for the LangGraph run: full trace per `thread_id` (guard → extract → match → answer), token/latency per node, and replay from any step.
- **CI** running `pytest` + linting.

### Reach
- **Periodic re-scrape** via cron / scheduled GitHub Action.
- **More shelters** — `yad4` is the easiest source; sospets (wix site so it will be a different kind of scraper), letlive, spca all viable additions.

---

## Tech stack

| Component           | Technology                       |
|---------------------|----------------------------------|
| Frontend            | React 18 + Vite + Tailwind CSS + lucide-react |
| API                 | FastAPI 0.115 + Uvicorn          |
| Agent               | LangGraph 0.2.28                 |
| LLM (agent)         | OpenAI GPT-4o                    |
| LLM (scraper)       | OpenAI GPT-4o-mini (structured outputs) |
| Scraper browser     | Playwright (Chromium headless)   |
| Validation          | Pydantic v2                      |
| Testing             | pytest                           |
| Containerization    | Docker (multi-stage)             |
