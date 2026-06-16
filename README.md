# Smart Restaurant — WhatsApp AI Agent · وكيل المطعم الذكي

Conversational ordering, reservations, payments and support over WhatsApp, in
Egyptian Arabic & English. Built on a **LangGraph** state machine driving
**Claude**, with a multi-tenant **FastAPI** core.

> **Local-first.** The whole system runs on your machine with **no paid APIs** —
> in-memory storage, a mock LLM, local embeddings, and a built-in web chat that
> simulates WhatsApp. Every external service sits behind an interface, so going
> to production is a `.env` change, not a rewrite.

See [`documentation.html`](documentation.html) for the full technical case study
and [`pipeline.svg`](pipeline.svg) for the architecture diagram.

---

## Quick start (local, zero API keys)

```powershell
# 1. create the virtualenv & install deps
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 2. (optional) copy the env template — defaults are already fully local
copy .env.example .env

# 3. run the app
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8080
```

Open **http://localhost:8080** and chat with the agent. First run downloads a
small (~120 MB) local embedding model; after that it works offline.

Try:
- `عايز شاورما فراخ` → searches the menu, builds the cart, offers payment
- `المنيو` → interactive menu list
- `فين الأوردر؟` → order tracking + ETA
- `احجز ترابيزة ٤ افراد بكرة الساعة ٨` → table reservation
- `عايزة اكلم حد من خدمة العملاء` → human escalation
- English works too: `I want a beef burger and a coke`

Run the end-to-end smoke test without a server:

```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe scripts\smoke.py
```

---

## Architecture (7 layers, docs §03)

```
WhatsApp / Local Chat
        │  webhook / POST /chat
        ▼
Ingress  ──►  Multi-modal (STT · Vision · location)
        │
        ▼
Agent core — LangGraph state machine
   intent → plan → tools → reflect → respond
        │           │
        │           ▼
        │     6 tools: menu_rag · cart · reservations
        │              payments · tracking · recommender
        ▼
Storage: repositories (memory | Postgres+pgvector) · vector store · Redis
        ▼
Response composer → dispatcher → telemetry
```

The LLM **proposes**; the graph **commits**. Prices and menu items are always
retrieved (RAG), never recited, and cart totals are computed from integer
piastres — so they can't drift or be hallucinated.

## Project layout

| Path | What |
|------|------|
| `app/config.py` | All settings; every provider is selected here |
| `app/schemas/` | Enums, domain objects, messaging envelopes, stored entities |
| `app/agent/` | `state.py`, `graph.py`, `nodes/` (intent·plan·tools·reflect·respond) |
| `app/tools/` | The 6 tools + allergen/eta/escalation; `__init__.py` is the registry |
| `app/providers/` | LLM, embeddings, vector store, channel, PSP, STT, vision (+ `base.py`) |
| `app/repositories/` | Storage interfaces + in-memory (and Postgres) implementations |
| `app/security/` | PII redaction, prompt-injection defense, signatures |
| `app/services/` | `pipeline.py` (spine), `response.py`, `telemetry.py`, `text.py` |
| `app/api/` | `local_chat.py`, `health.py` (+ prod `webhooks.py`, `admin.py`) |
| `app/seed/` | Demo tenant (مطعم بطة) + bilingual menu |
| `web/chat.html` | Local WhatsApp simulator UI |

## Providers — local default → production

| Capability | Local default | Production | Switch |
|-----------|---------------|-----------|--------|
| LLM | `mock` (deterministic) | Anthropic Claude | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` |
| Storage | `memory` | Postgres + RLS | `STORE_BACKEND=sql` + `DATABASE_URL` |
| Vectors | `memory` | pgvector / Pinecone | `VECTOR_PROVIDER=...` |
| Channel | `local` web chat | Meta WhatsApp Cloud API | `CHANNEL_PROVIDER=whatsapp` + WA_* keys |
| Payments | `mock` | Paymob / Stripe / Fawry | `PSP_PROVIDER=...` |
| Speech | `mock` | Whisper (local/OpenAI) | `STT_PROVIDER=...` |
| Vision | `mock` | Claude Vision | `VISION_PROVIDER=anthropic` |

## Going to production

1. Set `ANTHROPIC_API_KEY` and `LLM_PROVIDER=anthropic` for real reasoning.
2. Bring up Postgres + Redis, set `STORE_BACKEND=sql`, `VECTOR_PROVIDER=pgvector`,
   run migrations.
3. Register a Meta WhatsApp number, set `CHANNEL_PROVIDER=whatsapp` and the WA_*
   credentials; point the webhook at `/webhook/whatsapp`.
4. Wire a real PSP (`PSP_PROVIDER=paymob`), deploy with the provided
   Docker/Kubernetes manifests.

_Production adapters, SQL repositories, migrations, webhooks and infra are tracked
as the next build stage._

## Tech

Python 3.12 · FastAPI · LangGraph · Anthropic Claude · Pydantic v2 ·
SQLAlchemy · pgvector · Redis · Celery · fastembed · structlog · Prometheus.
