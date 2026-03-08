# 🧠 AI Resume Screener

An intelligent resume screening API built with **FastAPI**, **Groq LLM**, and **Valkey/Redis** caching. Upload a PDF resume and a job description — get back a structured JSON analysis with match score, strengths, gaps, and a hire/reject recommendation in seconds.

---

## ✨ Features

- 📄 **PDF Resume Parsing** — Extracts text from uploaded PDF resumes using PyMuPDF (`fitz`)
- 🤖 **LLM-Powered Analysis** — Uses Groq's API (default: `llama-3.1-8b-instant`) to evaluate candidate fit
- ⚡ **Redis/Valkey Caching** — Identical resume+JD pairs are cached to avoid redundant LLM calls
- 🔁 **Graceful Degradation** — Works fully even if Redis/Valkey is unavailable
- 🌐 **CORS Enabled** — Ready for frontend integration out of the box

---

## 📋 Requirements

- Python 3.9+
- A [Groq API key](https://console.groq.com/)
- (Optional) A running Valkey or Redis instance for caching

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-org/ai-resume-screener.git
cd ai-resume-screener
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn groq pymupdf redis python-dotenv python-multipart
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional — LLM model selection
GROQ_MODEL=llama-3.1-8b-instant

# Optional — Valkey/Redis caching
VALKEY_HOST=localhost
VALKEY_PORT=6379
CACHE_TTL=86400
```

### 4. Run the server

```bash
python main.py
```

Or with Uvicorn directly:

```bash
uvicorn main:app --host 127.0.0.1 --port 5000 --reload
```

The API will be available at `http://127.0.0.1:5000`.

---

## 📡 API Reference

### `POST /screen`

Screen a resume against a job description.

**Request** — `multipart/form-data`

| Field             | Type   | Required | Description                        |
|-------------------|--------|----------|------------------------------------|
| `resume`          | File   | ✅       | PDF resume file                    |
| `job_description` | String | ✅       | Plain text job description         |

**Response** — `application/json`

```json
{
  "candidate_name": "Jane Doe",
  "match_score": 82,
  "key_strengths": [
    "5 years Python experience",
    "Familiarity with FastAPI and REST APIs",
    "Strong background in ML pipelines"
  ],
  "missing_critical_skills": [
    "Kubernetes experience",
    "Terraform/IaC knowledge"
  ],
  "recommendation": "Interview",
  "reasoning": "Strong technical alignment with core requirements. Minor gaps in DevOps tooling which can be addressed on the job.",
  "cache": "MISS",
  "model": "llama-3.1-8b-instant"
}
```

| Field                    | Type     | Description                                      |
|--------------------------|----------|--------------------------------------------------|
| `candidate_name`         | string   | Extracted candidate name from the resume         |
| `match_score`            | integer  | 0–100 score indicating job fit                   |
| `key_strengths`          | string[] | Relevant skills and experiences matched to JD    |
| `missing_critical_skills`| string[] | Important JD requirements absent from resume     |
| `recommendation`         | string   | `"Interview"` or `"Reject"`                      |
| `reasoning`              | string   | Recruiter-style narrative summary                |
| `cache`                  | string   | `"HIT"` if served from cache, `"MISS"` otherwise |
| `model`                  | string   | Groq model used for this evaluation              |

---

### `GET /health`

Check the service status.

```json
{
  "status": "ok",
  "model": "llama-3.1-8b-instant",
  "cache": "connected"
}
```

---

## 🧪 Example Usage

### cURL

```bash
curl -X POST http://127.0.0.1:5000/screen \
  -F "resume=@/path/to/resume.pdf" \
  -F "job_description=We are looking for a Python backend engineer with FastAPI experience..."
```

### Python

```python
import requests

with open("resume.pdf", "rb") as f:
    response = requests.post(
        "http://127.0.0.1:5000/screen",
        files={"resume": ("resume.pdf", f, "application/pdf")},
        data={"job_description": "Looking for a senior Python engineer..."},
    )

print(response.json())
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                  Client                      │
│         (cURL / Frontend / Script)           │
└─────────────────┬───────────────────────────┘
                  │  POST /screen (PDF + JD)
                  ▼
┌─────────────────────────────────────────────┐
│              FastAPI Server                  │
│  1. Extract text from PDF (PyMuPDF)          │
│  2. Normalize & truncate to 4,000 chars      │
│  3. Generate SHA-256 cache key               │
└──────────┬──────────────────────┬────────────┘
           │                      │
     Cache HIT               Cache MISS
           │                      │
           ▼                      ▼
┌──────────────────┐   ┌──────────────────────┐
│  Valkey / Redis  │   │      Groq LLM API     │
│  (cached result) │   │  (structured JSON)    │
└──────────────────┘   └──────────┬───────────┘
                                  │
                        Store in cache (TTL: 24h)
                                  │
                                  ▼
                         Return JSON response
```

---

## ⚙️ Configuration Reference

| Variable       | Default                  | Description                              |
|----------------|--------------------------|------------------------------------------|
| `GROQ_API_KEY` | *(required)*             | Your Groq API key                        |
| `GROQ_MODEL`   | `llama-3.1-8b-instant`   | Groq model to use for screening          |
| `VALKEY_HOST`  | `localhost`              | Redis/Valkey hostname                    |
| `VALKEY_PORT`  | `6379`                   | Redis/Valkey port                        |
| `CACHE_TTL`    | `86400` (24 hours)       | Cache expiry in seconds                  |

---

## 🛡️ Error Handling

| HTTP Code | Cause                                         |
|-----------|-----------------------------------------------|
| `400`     | Non-PDF file uploaded                         |
| `400`     | PDF contains no extractable text              |
| `500`     | Groq API error or invalid JSON response       |

---

## 📁 Project Structure

```
.
├── main.py          # Application entrypoint
├── .env             # Environment variables (not committed)
├── .env.example     # Example env file
└── README.md        # This file
```

---

## 📝 License

MIT License. See [LICENSE](LICENSE) for details.