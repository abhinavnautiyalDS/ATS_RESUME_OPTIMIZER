# 🎯 ATS Resume Optimizer

> A production-quality GenAI system that converts any resume + job description into an ATS-optimized resume and tailored cover letter — using 100% open-source models.

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (GitHub Pages)                       │
│  HTML + CSS + Vanilla JS                                             │
│  • Resume Upload (PDF/DOCX)    • Job Description Input               │
│  • ATS Score Display           • Download Generated Files            │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTP POST (multipart/form-data)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI Server)                         │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Pipeline Orchestrator                      │   │
│  │                                                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐   │   │
│  │  │  Resume  │  │    JD    │  │   ATS    │  │  Resume   │   │   │
│  │  │  Parser  │→ │Analyzer  │→ │  Scorer  │→ │Optimizer  │   │   │
│  │  │ Stage 1  │  │ Stage 2  │  │ Stage 3  │  │ Stage 4   │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────┬─────┘   │   │
│  │                                                   │         │   │
│  │                              ┌────────────────────┘         │   │
│  │                              ▼                              │   │
│  │               ┌──────────────────────────┐                  │   │
│  │               │    DOCX Generator         │                  │   │
│  │               │    Stage 5               │                  │   │
│  │               └─────────────┬────────────┘                  │   │
│  │                             │                               │   │
│  │               ┌─────────────▼────────────┐                  │   │
│  │               │  Cover Letter Generator   │                  │   │
│  │               │    Stage 6               │                  │   │
│  │               └──────────────────────────┘                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      LLM Client Layer                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐   │   │
│  │  │ HuggingFace │  │   Ollama    │  │       Groq         │   │   │
│  │  │  (cloud)    │  │   (local)   │  │  (free cloud API)  │   │   │
│  │  └─────────────┘  └─────────────┘  └────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Processing Pipeline

```
Upload Resume (PDF/DOCX) + Job Description Text
                    │
                    ▼
         ┌─────────────────┐
         │  Stage 1        │
         │  Resume Parser  │  ← pdfplumber / python-docx (text extraction)
         │                 │  ← LLM (structured parsing to JSON)
         └────────┬────────┘
                  │ ParsedResume
                  ▼
         ┌─────────────────┐
         │  Stage 2        │
         │  JD Analyzer    │  ← LLM (extracts skills, tools, keywords)
         │                 │
         └────────┬────────┘
                  │ ParsedJobDescription
                  ▼
         ┌─────────────────┐
         │  Stage 3        │
         │  ATS Scorer     │  ← Deterministic (keyword matching)
         │                 │  ← LLM (semantic relevance scoring)
         └────────┬────────┘
                  │ ATSAnalysis (score + gaps)
                  ▼
         ┌─────────────────┐
         │  Stage 4        │
         │ Resume Optimizer│  ← LLM (rewrites bullets, summary, skills)
         │                 │  ← Never fabricates experience
         └────────┬────────┘
                  │ OptimizedResume
                  ▼
         ┌─────────────────┐
         │  Stage 5        │
         │ DOCX Generator  │  ← python-docx (ATS-safe formatting)
         │                 │
         └────────┬────────┘
                  │ resume.docx
                  ▼
         ┌─────────────────┐
         │  Stage 6        │
         │ Cover Letter    │  ← LLM (tailored letter generation)
         │ Generator       │  ← python-docx (DOCX formatting)
         └────────┬────────┘
                  │
                  ▼
         PipelineResponse
         (JSON + download links)
```

---

## 📁 Project Structure

```
ats-resume-system/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt           # Python dependencies
│   ├── pyproject.toml             # Pytest config
│   ├── .env.example               # Environment template
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # All FastAPI endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic settings (all env vars)
│   │   ├── llm_client.py          # LLM provider abstraction
│   │   └── pipeline.py            # Pipeline orchestrator
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── resume_parser.py       # Stage 1: PDF/DOCX → ParsedResume
│   │   ├── jd_analyzer.py         # Stage 2: JD text → ParsedJobDescription
│   │   ├── ats_scorer.py          # Stage 3: Gap analysis + ATS score
│   │   ├── resume_optimizer.py    # Stage 4: Optimize resume content
│   │   ├── docx_generator.py      # Stage 5: Generate ATS-friendly DOCX
│   │   └── cover_letter_generator.py  # Stage 6: Cover letter + DOCX
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # All Pydantic data models
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── templates.py           # All LLM prompts (centralized)
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py             # Shared utility functions
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_pipeline.py       # Full test suite
│   │
│   ├── uploads/                   # Temp storage for uploaded files
│   └── output/                    # Generated DOCX files
│
└── frontend/
    ├── index.html                 # Main upload interface
    ├── results.html               # Results display page
    ├── css/
    │   └── styles.css             # Styling
    └── js/
        ├── app.js                 # Main application logic
        └── results.js             # Results rendering
```

---

## 🚀 Local Setup Instructions

### Prerequisites
- Python 3.11+
- pip
- One of: Groq API key (free), HuggingFace token (free), or Ollama installed

### Step 1: Clone and Set Up Backend

```bash
git clone https://github.com/yourusername/ats-resume-system.git
cd ats-resume-system/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — choose ONE provider:

**Option A: Groq (Recommended — Free, Fast)**
```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_from_console.groq.com
GROQ_MODEL=llama3-8b-8192
```

**Option B: HuggingFace (Free with rate limits)**
```env
LLM_PROVIDER=huggingface
HF_API_TOKEN=your_token_from_huggingface.co
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3
```

**Option C: Ollama (Fully Local, No API key)**
```bash
# Install Ollama: https://ollama.ai
ollama pull llama3
ollama serve
```
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 3: Run the Backend

```bash
# Create output directories
mkdir -p uploads output

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now running at `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Step 4: Run the Frontend

```bash
# From the frontend directory
cd ../frontend
# Open index.html with a local server (required for CORS)
python -m http.server 5500
# Open http://localhost:5500 in your browser
```

### Step 5: Run Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🌐 Deployment Instructions

### Backend: Deploy to Railway / Render / Fly.io (Free Tiers)

**Railway (Easiest):**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

**Render:**
1. Push to GitHub
2. New Web Service → Connect repo → Select `backend/` root
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars from `.env` in Render dashboard

**Fly.io:**
```bash
fly launch
fly secrets set GROQ_API_KEY=your_key LLM_PROVIDER=groq
fly deploy
```

### Frontend: Deploy to GitHub Pages

```bash
# In your repo settings → Pages → Source: Deploy from branch
# Select: main branch, /frontend folder

# Update the API URL in frontend/js/app.js:
# const API_BASE_URL = "https://your-backend.railway.app/api/v1";
```

---

## 📊 Example API Usage

### cURL
```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -F "resume_file=@/path/to/resume.pdf" \
  -F "job_description=We are looking for a Senior Python Engineer..."
```

### Python
```python
import httpx

with open("resume.pdf", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/api/v1/optimize",
        files={"resume_file": ("resume.pdf", f, "application/pdf")},
        data={"job_description": "Job description text here..."},
        timeout=120,
    )

result = response.json()
print(f"ATS Score: {result['ats_analysis']['ats_score']}/100")
print(f"Missing Keywords: {result['ats_analysis']['missing_keywords']}")
```

---

## 🔬 LLM Prompts Used

The system uses 5 specialized prompts located in `prompts/templates.py`:

| Prompt | Purpose | Output Format |
|--------|---------|---------------|
| `RESUME_PARSER_SYSTEM` | Extract structured data from resume text | JSON (ParsedResume) |
| `JD_ANALYZER_SYSTEM` | Identify skills, keywords, requirements from JD | JSON (ParsedJobDescription) |
| `ATS_ANALYZER_SYSTEM` | Score compatibility + identify gaps | JSON (ATSAnalysis) |
| `RESUME_OPTIMIZER_SYSTEM` | Rewrite resume to improve ATS match | JSON (OptimizedResume) |
| `COVER_LETTER_SYSTEM` | Generate tailored 4-paragraph cover letter | JSON (CoverLetter) |

All prompts instruct the model to return ONLY valid JSON, with retry logic for invalid responses.

---

## 💡 System Improvement Suggestions

### Short Term
1. **Caching**: Cache LLM responses by resume+JD hash to avoid re-processing identical inputs
2. **Async file cleanup**: Auto-delete generated DOCX files after 24 hours
3. **PDF preview**: Show resume preview before processing
4. **Multiple JD comparison**: Score a resume against multiple JDs simultaneously

### Medium Term
5. **Fine-tuned model**: Fine-tune Mistral-7B on resume datasets for better extraction accuracy
6. **RAG for industry keywords**: Build a vector store of industry-specific keywords per role
7. **Resume scoring history**: Save past scores to track improvement over time
8. **LinkedIn scraper**: Auto-populate JD from a LinkedIn URL

### Long Term
9. **Multi-language support**: Support non-English resumes and job descriptions
10. **Interview prep**: Generate likely interview questions based on matched role
11. **Salary estimation**: Add salary range prediction based on skills and experience
12. **A/B prompt testing**: Framework for testing different prompts against quality metrics

---

## ⚠️ Important Notes

- The system **never fabricates experience** — the optimizer only integrates keywords into existing experience
- Generated DOCX files are stored locally in `output/` — add cleanup logic for production
- Free-tier LLMs (HuggingFace) have rate limits — use Groq or Ollama for higher throughput
- For production, set `CORS_ORIGINS` to your specific GitHub Pages URL

---

## 📄 License
MIT License — free to use and modify for personal and commercial projects.
