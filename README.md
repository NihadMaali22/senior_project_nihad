# Academic Decision-Making Assistant

A production-style intelligent academic assistant for universities that combines **Hybrid RAG**, **SQL querying**, and **policy-based decision-making** to answer complex academic questions.

> This is **not** a simple PDF chatbot. It reasons over regulations, inspects student data, applies policy conditions, and returns justified decisions with citations.

Designed as a **Senior Project** — the backend is a RESTful API consumed by:
- A **web browser frontend** (`frontend/`)
- **curl / Postman** (testing & integration)
- **Reachy Mini robots** (physical kiosk mode — robot speaks answers to students)

---

## How It Works

A student asks: *"Can I register for Internship 2?"*

1. **Query Router** classifies the question → `HYBRID` (needs data + policy)
2. **SQL Agent** fetches the student's GPA, credits, and course history from PostgreSQL
3. **Hybrid RAG** retrieves relevant sections from the internship policy document (Qdrant)
4. **Decision Engine** checks all conditions (GPA ≥ 2.0, credits ≥ 90, Internship 1 completed)
5. **Citation Generator** attaches the exact policy articles
6. Response: `APPROVED` or `DENIED` with full reasoning and citations

---

## Architecture

```
Client (Browser / curl / Reachy Mini)
        │
        ▼
  FastAPI  ─── JWT Auth Middleware
        │
        ▼
  Query Router (LLM + Keywords)
   ├── SQL Agent  ──────────────► PostgreSQL (student data)
   ├── RAG Engine ──────────────► Qdrant (regulation vectors)
   │     ├── Dense: SentenceTransformers (all-MiniLM-L6-v2)
   │     ├── Sparse: FastEmbed SPLADE
   │     └── Reranker: CrossEncoder (ms-marco-MiniLM-L-6-v2)
   └── Decision Engine ─────────► Ollama (llama3.1:8b)
         └── Citation Generator
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| API Framework | FastAPI (async) | ≥ 0.115 |
| Pipeline Orchestration | Haystack 2.x | ≥ 2.5 |
| Vector Database | Qdrant | 1.9.2 |
| Relational Database | PostgreSQL | 16 |
| Local LLM | Ollama — llama3.1:8b | 0.3.12 |
| Dense Embeddings | SentenceTransformers | ≥ 3.0 |
| Sparse Embeddings | FastEmbed (SPLADE) | ≥ 0.3 |
| Reranker | CrossEncoder (HuggingFace) | ≥ 4.40 |
| Auth | JWT + bcrypt | — |
| Containerization | Docker Compose | — |

---

## Project Structure

```
.
├── docker-compose.yml          # All services (Postgres, Qdrant, Ollama, App)
├── Dockerfile                  # Multi-stage production build
├── requirements.txt            # Python dependencies
├── alembic.ini                 # DB migration config
├── app/
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config.py               # Pydantic settings (env vars)
│   ├── dependencies.py         # Dependency injection helpers
│   ├── auth/
│   │   ├── service.py          # JWT creation & bcrypt hashing
│   │   ├── middleware.py       # Bearer token validation + role checks
│   │   ├── router.py           # POST /auth/login, /auth/me
│   │   └── schemas.py          # Auth request/response models
│   ├── db/
│   │   ├── database.py         # Async SQLAlchemy engine & session
│   │   ├── models.py           # ORM models (User, Student, Course, …)
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   └── seed.py             # Sample data (students, courses, grades)
│   ├── api/
│   │   ├── assistant.py        # POST /ask  — main chat endpoint
│   │   ├── documents.py        # Document upload & management
│   │   ├── tts.py              # POST /tts  — Arabic TTS proxy (Munsit)
│   │   └── router.py           # Aggregates all sub-routers under /api/v1
│   ├── admin/
│   │   └── router.py           # Admin: stats, seed, ingest (admin role only)
│   ├── router/
│   │   └── query_router.py     # LLM + keyword classification → SQL/RAG/HYBRID
│   ├── sql_agent/
│   │   ├── queries.py          # Pre-built safe SQL templates (no raw generation)
│   │   └── agent.py            # Query dispatcher & result formatter
│   ├── rag/
│   │   ├── document_store.py   # QdrantDocumentStore singleton
│   │   ├── embedders.py        # Model name constants (dense/sparse/reranker)
│   │   ├── ingestion.py        # Haystack ingestion pipeline (reads regulations + knowledge)
│   │   └── retrieval.py        # Haystack hybrid retrieval pipeline
│   ├── knowledge/              # ── Standalone crawler — NOT imported at app startup
│   │   ├── targets.py          # List of AAUP pages to crawl (path, slug, title, type)
│   │   ├── crawler.py          # Async crawl4ai crawler → saves to data/knowledge/
│   │   └── pipeline.py         # CLI: crawl + ingest in one command
│   ├── decision/
│   │   ├── engine.py           # Core orchestrator (SQL + RAG + LLM)
│   │   ├── rules.py            # Deterministic policy checks
│   │   └── prompts.py          # LLM prompt templates
│   ├── citation/
│   │   └── generator.py        # Source attribution with article references
│   └── memory/
│       └── conversation.py     # Multi-turn session history (PostgreSQL)
├── data/
│   ├── regulations/            # Hand-written university policy files (.txt)
│   │   ├── graduation_requirements.txt
│   │   ├── academic_probation.txt
│   │   ├── course_registration.txt
│   │   ├── withdrawal_policy.txt
│   │   └── internship_policy.txt
│   └── knowledge/              # Auto-generated by crawler (gitignored)
│       └── aaup_*.txt          # One file per crawled page
├── sql/
│   └── schema.sql              # Database schema (auto-applied on first run)
├── frontend/
│   ├── index.html              # Web UI
│   ├── app.js                  # API calls & UI logic
│   └── style.css               # Styles
└── tests/
    ├── conftest.py             # Fixtures & test DB setup
    ├── test_decision.py        # Decision engine tests
    ├── test_rag.py             # Retrieval pipeline tests
    └── test_sql_agent.py       # SQL agent tests
```

---

## First-Time Setup

> Run these steps **once** when setting up the project on a new machine.

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker Engine + Docker Compose | [Install Docker](https://docs.docker.com/engine/install/) |
| Python 3.11+ | 3.12 or 3.13 work fine |
| 8 GB RAM | Required for the local LLM (Ollama) |
| Internet access | For pulling Docker images and HuggingFace models |

---

### Step 1 — Clone the Repository

```bash
git clone <repo-url>
cd senior_project_nihad
```

---

### Step 2 — Create the `.env` File

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
SECRET_KEY=<random-32-char-string>   # openssl rand -hex 32
```

All other values are pre-filled for local development.

---

### Step 3 — Start the Database and Vector Store

Start only the two required services first (Postgres and Qdrant):

```bash
sudo docker compose up -d postgres qdrant
```

Wait until both are healthy (~10 seconds):

```bash
sudo docker compose ps
# postgres → (healthy)
# qdrant   → (healthy)
```

---

### Step 4 — Create a Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

---

### Step 5 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

After installation, download the NLTK tokenizer data (required once for sentence splitting):

```bash
python -c "import nltk; nltk.download('punkt_tab')"
```

---

### Step 6 — Seed the Database

```bash
python -m app.db.seed
```

Creates: 12 students, 28 courses, grade records, and 7 login accounts (see [Default Accounts](#default-accounts-after-seeding)).

---

### Step 7 — Ingest Regulation Documents into Qdrant

```bash
python -m app.rag.ingestion
```

Reads the 5 `.txt` files in `data/regulations/`, chunks and embeds them, and writes 28 chunks to Qdrant.  
The first run downloads the embedding model from HuggingFace (~120 MB) — this is automatic.

---

### Step 8 — (Optional) Start Ollama for LLM Answers

```bash
sudo docker compose up -d ollama
```

Downloads `llama3.1:8b` (~5 GB) automatically on first run. Watch progress:

```bash
sudo docker compose logs -f ollama-init
```

> **Without Ollama**, the assistant still returns citations and structured decisions from RAG + SQL.  
> Natural-language answers will show a fallback message until Ollama is ready.

---

## Running the App

After first-time setup is complete, use these commands to start and stop the system day-to-day.

### 1. Start Infrastructure

```bash
sudo docker compose up -d postgres qdrant
# Also start Ollama if needed:
sudo docker compose up -d ollama
```

### 2. Activate the Virtual Environment

```bash
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

### 3. Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server is ready when you see:
```
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 4. Access

| Interface | URL |
|-----------|-----|
| Web UI | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

### 5. Demo Accounts

All accounts are pre-loaded by the seed script.

| Username | Password | Role | Notes |
|----------|----------|------|-------|
| `admin` | `admin123` | Admin | Full system access |
| `khalid` | `student123` | Student | Senior, high GPA |
| `noor` | `student123` | Student | On academic probation |
| `tariq` | `student123` | Student | Eligible for graduation |
| `hassan` | `student123` | Student | On internship watch |
| `lina` | `student123` | Student | Freshman |
| `advisor` | `advisor123` | Advisor | Dr. Ahmad Al-Rashid |

> Use any student account to test the decision engine. Each student has different academic standing, GPA, and credit history so you get varied responses.

### 6. Stop Everything

```bash
# Stop the API server: Ctrl+C in its terminal

# Stop Docker containers (keeps data volumes)
sudo docker compose down

# Stop and wipe all data (full reset)
sudo docker compose down -v
```

---

## Knowledge Base — Crawling AAUP Website

The `app/knowledge/` module crawls [aaup.edu/ar](https://www.aaup.edu/ar), extracts clean Arabic text from 12 key pages, and saves them to `data/knowledge/`. The ingestion pipeline then embeds them into Qdrant alongside the hand-written regulation files.

This process is **completely separate from the app** — it never runs at startup. Run it once at the beginning of a semester, or whenever the university updates its website.

### First-time setup

```bash
# Install the browser used by crawl4ai (one-time)
pip install crawl4ai
crawl4ai-setup
```

### Run the pipeline

```bash
# Crawl only new/missing pages, then ingest everything into Qdrant
python -m app.knowledge.pipeline

# Force re-crawl all 12 pages (e.g. start of new semester)
python -m app.knowledge.pipeline --force
```

### What gets crawled

| Slug | Page | Type |
|------|------|------|
| `academic_programs` | البرامج الأكاديمية | academic |
| `faculties` | الكليات والأقسام | academic |
| `admissions` | القبول والدراسة | admissions |
| `scholarships` | المنح الدراسية | admissions |
| `regulations` | الأنظمة والتعليمات | regulation |
| `academic_calendar` | التقويم الأكاديمي | regulation |
| `about_university` | عن الجامعة | general |
| `facts_figures` | الحقائق والأرقام | general |
| `e_services` | الخدمات الإلكترونية | services |
| `university_life` | الحياة الجامعية | general |
| `alumni` | الخريجون | general |
| `masters_programs` | برامج الماجستير | academic |

Saved files are gitignored (`data/knowledge/*.txt`) — they are generated content, not source code.

---

## Full Docker Deploy (All-in-One)

```bash
docker compose up -d
```

The app container starts after Postgres, Qdrant, and Ollama are healthy.  
Then run seed and ingest once:

```bash
docker compose exec app python -m app.db.seed
docker compose exec app python -m app.rag.ingestion
```

---

## API Reference

### Authentication

```bash
# Get a JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "khalid", "password": "student123"}'
```

Response:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

### Default Accounts (after seeding)

| Username | Password | Role | Notes |
|----------|----------|------|-------|
| `admin` | `admin123` | admin | Full access |
| `khalid` | `student123` | student | GPA 3.65 |
| `noor` | `student123` | student | GPA 3.20 |
| `tariq` | `student123` | student | GPA 1.85 — on probation |
| `hassan` | `student123` | student | GPA 2.90 |
| `lina` | `student123` | student | GPA 3.80 — freshman |
| `advisor` | `advisor123` | advisor | Dr. Ahmad Al-Rashid |

### Ask a Question

```bash
TOKEN="<jwt_from_login>"

# SQL — pure data lookup
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is my GPA?"}'

# RAG — policy lookup
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the withdrawal policy?"}'

# Hybrid — decision with data + policy
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Can I register for Internship 2?"}'
```

### Response Format

```json
{
  "answer": "Based on your academic record, you ARE eligible to register for Internship 2.",
  "decision": "APPROVED",
  "reasoning": [
    "Student status is active.",
    "GPA is 2.900 (minimum 2.0 required).",
    "95 completed credits (minimum 90 required).",
    "Internship 1 completed with grade B+."
  ],
  "student_data": {
    "full_name": "Hassan Darwish",
    "gpa": 2.9,
    "total_credits": 95
  },
  "citations": [
    {
      "source": "Internship Policy",
      "section": "Section 13.2",
      "text": "To register for Internship 2, a student must have completed a minimum of 90 credit hours..."
    }
  ],
  "confidence": 0.92,
  "query_type": "HYBRID"
}
```

### Text-to-Speech (Arabic)

```bash
curl -X POST http://localhost:8000/api/v1/tts/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "أهلاً، كيف يمكنني مساعدتك اليوم؟", "voice_id": "ar-najdi-male-2"}' \
  --output response.wav
```

### Admin Endpoints

```bash
# System statistics
curl http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Trigger data seed
curl -X POST http://localhost:8000/api/v1/admin/seed \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Trigger document re-ingestion
curl -X POST http://localhost:8000/api/v1/admin/ingest \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Query Routing

| Question | Route | Reason |
|----------|-------|--------|
| "What is my GPA?" | `SQL_ONLY` | Pure data lookup |
| "Show my completed courses" | `SQL_ONLY` | Database query |
| "What is the withdrawal policy?" | `RAG_ONLY` | Regulation lookup |
| "How does academic probation work?" | `RAG_ONLY` | Policy explanation |
| "Can I register for Internship 2?" | `HYBRID` | Needs data + policy |
| "Why am I on probation?" | `HYBRID` | Needs standing + rules |
| "Can I graduate?" | `HYBRID` | Needs progress + requirements |

---

## Reachy Mini Integration

[Reachy Mini](https://www.pollen-robotics.com/) is a desktop humanoid robot that acts as a physical kiosk for students.  
It communicates with this backend over the same RESTful API — no special integration needed.

### Flow

```
Student speaks → Reachy STT (Whisper) → POST /api/v1/ask → answer text → POST /api/v1/tts/synthesize → Reachy speaks
```

### Python Client on Reachy

```python
import httpx

BASE_URL = "http://<server-ip>:8000/api/v1"

# 1. Authenticate once and store the token
resp = httpx.post(f"{BASE_URL}/auth/login",
                  json={"username": "reachy_kiosk", "password": "..."})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Send a student question (transcribed from speech)
resp = httpx.post(f"{BASE_URL}/ask",
                  headers=headers,
                  json={"question": "Can I graduate this semester?"})
data = resp.json()
answer_text = data["answer"]

# 3. Convert answer to speech and play on Reachy's speaker
audio = httpx.post(f"{BASE_URL}/tts/synthesize",
                   headers=headers,
                   json={"text": answer_text, "voice_id": "ar-najdi-male-2"})
# Write audio.content (WAV bytes) to Reachy's audio output
```

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | — | **Required.** Random string for JWT signing |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST endpoint |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | LLM model name |
| `DENSE_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Dense embedding model |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker model |
| `RAG_TOP_K` | `10` | Candidates retrieved before reranking |
| `RAG_RERANK_TOP_K` | `5` | Final results after reranking |
| `JWT_EXPIRATION_MINUTES` | `480` | Token lifetime (8 hours) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT
