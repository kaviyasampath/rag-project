# 🎓 NAAC SSR Generator
**Final Year Project — AI-powered Self-Study Report Generation using RAG + Gemini**

## Architecture

```
naac_ssr_system/
├── app.py              ← Institution-facing app  (deploy publicly,  port 8501)
├── admin_app.py        ← Admin knowledge manager (internal only,    port 8502)
├── rag_engine.py       ← Shared RAG engine
├── utils.py            ← Helpers
├── naac_vector_db/     ← Shared persistent ChromaDB (created on first run)
└── requirements.txt
```

## How the Two Apps Work Together

```
Admin (port 8502)                    Institutions (port 8501)
      │                                       │
      │  Upload reference SSRs                │  Upload own documents
      ▼                                       ▼
naac_vector_db/ ◄──── shared on disk ───► naac_vector_db/
(reference SSRs, permanent)            (read at generation time)
```

- Admin loads reference SSRs **once** → saved permanently to `naac_vector_db/`
- Admin can **add more anytime** — institutions benefit immediately, no restart needed
- Institutions only see `app.py` — they upload their own docs and generate SSRs
- The two apps are **completely separate** but share the same DB folder

## Setup & Run

### 1. Install dependencies
```bash
py -3.13 -m pip install -r requirements.txt
```

### 2. Get a free Gemini API key
Go to https://aistudio.google.com → Get API Key

### 3. Admin: Load reference SSRs (do this first, once)
```bash
streamlit run admin_app.py --server.port 8502
```
- Open http://localhost:8502
- Upload public SSRs from naac.gov.in (A++ / A+ institutions)
- Click "Add to Knowledge Base"

### 4. Run the institution app
```bash
streamlit run app.py --server.port 8501
```
- Open http://localhost:8501
- Upload institutional documents
- Generate SSR sections

## Deployment on a Server

```bash
# Terminal 1 — institution app (public)
streamlit run app.py --server.port 8501

# Terminal 2 — admin app (keep private, use firewall to restrict access)
streamlit run admin_app.py --server.port 8502
```

Both apps share the same `naac_vector_db/` folder on the server.
Admin can update the knowledge base from anywhere via port 8502.
Changes are reflected instantly in the institution app.

## Tech Stack
| Component   | Technology                          |
|-------------|-------------------------------------|
| LLM         | Google Gemini 1.5 Flash (free tier) |
| Embeddings  | all-MiniLM-L6-v2 (sentence-transformers) |
| Vector DB   | ChromaDB (persistent, local)        |
| UI          | Streamlit                           |
| Doc parsing | PyMuPDF, python-docx                |
