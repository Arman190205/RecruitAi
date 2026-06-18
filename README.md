# ⚡ RecruitAI — AI-Augmented Recruitment Platform

> Screen 1,000 CVs. Surface the 10 that matter. Explain why.

RecruitAI is a full-stack web application that uses LLMs to **semantically screen CVs** against a job description — going far beyond keyword matching to understand true candidate fit and explain every ranking decision transparently.

---

## ✨ Features

| Feature | Description |
|---|---|
| **JD Parser** | Paste any job posting → AI extracts hard skills, soft skills, must-haves, nice-to-haves, experience level, and domain knowledge |
| **Batch CV Upload** | Drag-and-drop up to 50 PDF or DOCX résumés at once |
| **Semantic Scoring** | Each candidate scored across 5 weighted dimensions (Hard Skills 35%, Must-Have 30%, Experience 15%, Soft Skills 10%, Domain 10%) |
| **Adjustable Weights** | Re-weight the 5 scoring dimensions from the results view and the shortlist re-ranks instantly in the browser — no re-scoring round trip |
| **Explainable Rankings** | Per-candidate AI justification: why they fit, what gaps exist |
| **Bias & Diversity Flags** | Detects homogeneous shortlists; surfaces "Hidden Gem" candidates with strong technical fundamentals |
| **Interview Questions** | 3 tailored, gap-probing interview questions auto-generated per candidate |
| **Export CSV** | Download the full ranked shortlist as a spreadsheet |

---

## 🏗️ Tech Stack

### Backend
- **FastAPI** + **Uvicorn** — async REST API
- **Groq API** (Llama 3.3 70B) — LLM for JD parsing, CV parsing, and scoring
- **pdfplumber** — PDF text extraction
- **python-docx** — DOCX text extraction
- **asyncio** — parallel CV processing pipeline

### Frontend
- **React 19** + **Vite 8**
- **Vanilla CSS** — custom design system with dark mode, glassmorphism, micro-animations

---

## 📁 Project Structure

```
GenAIProject/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example          # Copy to .env and add your keys
│   ├── core/
│   │   ├── config.py         # Settings (loaded from .env)
│   │   └── groq_client.py    # Groq API wrapper
│   ├── models/
│   │   ├── jd_models.py
│   │   ├── cv_models.py
│   │   └── result_models.py
│   ├── routers/
│   │   ├── jd.py             # POST /api/jd/parse
│   │   ├── cv.py             # POST /api/cv/upload
│   │   └── results.py        # GET /api/jobs/{id}/status|results
│   ├── services/
│   │   ├── jd_parser.py      # LLM-based JD extraction
│   │   ├── cv_extractor.py   # PDF/DOCX text extraction
│   │   ├── cv_parser.py      # LLM-based CV extraction
│   │   ├── scorer.py         # Semantic candidate scoring
│   │   ├── ranker.py         # Parallel pipeline orchestrator
│   │   └── bias_detector.py  # Shortlist diversity analysis
│   └── storage/
│       └── session_store.py  # In-memory job state store
└── frontend/
    ├── index.html
    ├── vite.config.js
    └── src/
        ├── App.jsx            # 4-step wizard state machine
        ├── api.js             # Typed API client
        ├── index.css          # Full design system
        └── components/
            ├── StepIndicator.jsx
            ├── JDStep.jsx
            ├── UploadStep.jsx
            ├── ProcessingStep.jsx
            ├── ResultsStep.jsx
            └── CandidateCard.jsx
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/GenAIProject.git
cd GenAIProject
```

### 2. Set up the Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Open `.env` and fill in your Groq API key:

```env
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
MAX_CVS_PER_BATCH=50
TOP_N_CANDIDATES=10
PROCESSING_TIMEOUT_SECONDS=120
```

Start the API server:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

API docs available at: **http://localhost:8002/docs**

### 3. Set up the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: **http://localhost:5173**

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/jd/parse` | Parse a raw job description text |
| `POST` | `/api/cv/upload` | Upload CVs + JD, start background scoring |
| `GET` | `/api/jobs/{id}/status` | Poll job progress (0–100%) |
| `GET` | `/api/jobs/{id}/results` | Fetch ranked candidates when complete |

---

## ⚙️ Configuration

All settings are in `backend/.env` (copied from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model to use |
| `MAX_CVS_PER_BATCH` | `50` | Max CVs per upload |
| `TOP_N_CANDIDATES` | `10` | Candidates shown in results |
| `PROCESSING_TIMEOUT_SECONDS` | `120` | Pipeline timeout |

---

## 🧪 Running the Test Pipeline

With the backend running, execute the end-to-end integration test:

```bash
cd backend
python test_pipeline.py
```

Update the `CV_FILES` list in `test_pipeline.py` to point to your own résumé PDFs before running.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
