import os
import json
import hashlib
import fitz
import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from ollama import Client

# ======================================================
# ENV
# ======================================================
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
VALKEY_HOST = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT = int(os.getenv("VALKEY_PORT", 6379))
CACHE_TTL = int(os.getenv("CACHE_TTL", 86400))

# ======================================================
# CLIENTS
# ======================================================
ollama_client = Client(host=OLLAMA_HOST)

valkey = redis.Redis(
    host=VALKEY_HOST,
    port=VALKEY_PORT,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)

# ======================================================
# LIFESPAN (SAFE STARTUP)
# ======================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_in_threadpool(
            ollama_client.chat,
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "ping"}],
        )
        print("✅ Ollama warmed up")
    except Exception as e:
        print("⚠️ Ollama warmup skipped:", e)

    yield

    print("🛑 API shutdown")

# ======================================================
# APP
# ======================================================
app = FastAPI(
    title="AI Resume Screener",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# UTILS
# ======================================================
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "".join(page.get_text() for page in doc)

def normalize_text(text: str) -> str:
    return " ".join(text.split())[:4000]  # IMPORTANT: smaller input

def cache_key(resume: str, jd: str) -> str:
    return "resume:" + hashlib.sha256((resume + jd).encode()).hexdigest()

# ======================================================
# LLM LOGIC
# ======================================================
async def screen_with_llm(resume: str, jd: str) -> dict:
    key = cache_key(resume, jd)

    cached = valkey.get(key)
    if cached:
        data = json.loads(cached)
        data["cache"] = "HIT"
        return data

    prompt = f"""
JD:
{jd}

RESUME:
{resume}

Return JSON only:
{{
 "candidate_name": "",
 "match_score": 0,
 "key_strengths": [],
 "missing_critical_skills": [],
 "recommendation": "Interview or Reject",
 "reasoning": ""
}}
"""

    try:
        response = await run_in_threadpool(
            ollama_client.chat,
            model="llama3.2:3b",
            format="json",
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": 4096},
        )

        result = json.loads(response["message"]["content"])
        result["cache"] = "MISS"
        valkey.setex(key, CACHE_TTL, json.dumps(result))
        return result

    except Exception as e:
        return {"error": str(e)}

# ======================================================
# ROUTES
# ======================================================
@app.post("/screen")
async def screen(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    if not resume.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF allowed")

    pdf_bytes = await resume.read()
    resume_text = extract_text_from_pdf(pdf_bytes)

    if not resume_text.strip():
        raise HTTPException(400, "Empty resume")

    return await screen_with_llm(
        normalize_text(resume_text),
        job_description,
    )

@app.get("/health")
def health():
    return {"status": "ok"}

# ======================================================
# ENTRYPOINT
# ======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",   # 🔴 FIXED
        host="127.0.0.1",
        port=5000,
        reload=True,
    )
