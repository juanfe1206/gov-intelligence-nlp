# gov-intelligence-nlp

Political intelligence platform for analyzing Spanish political discourse via NLP and LLM-powered Q&A.

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+ with pgvector extension

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at http://localhost:3000

### Backend Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend API at http://localhost:8000
API docs at http://localhost:8000/docs

### Environment Variables
Copy `.env.example` to `.env` and configure your database URL and API keys.
