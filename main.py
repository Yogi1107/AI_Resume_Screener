import os
import json
import hashlib
import fitz
import redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ======================================================
# ENV
# ======================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

VALKEY_HOST  = os.getenv("VALKEY_HOST", "localhost")
VALKEY_PORT  = int(os.getenv("VALKEY_PORT", 6379))
CACHE_TTL    = int(os.getenv("CACHE_TTL", 86400))

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable is not set.")

# ======================================================
# CLIENTS
# ======================================================
groq_client = Groq(api_key=GROQ_API_KEY)

try:
    valkey = redis.Redis(
        host=VALKEY_HOST,
        port=VALKEY_PORT,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    valkey.ping()
    print("✅ Valkey/Redis connected")
except Exception as e:
    print(f"⚠️ Valkey/Redis unavailable, caching disabled: {e}")
    valkey = None

# ======================================================
# LIFESPAN (SAFE STARTUP)
# ======================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        print("✅ Groq API connection verified")
    except Exception as e:
        print("⚠️ Groq warmup skipped:", e)

    yield

    print("🛑 API shutdown")

# ======================================================
# APP
# ======================================================
app = FastAPI(
    title="AI Resume Screener",
    version="2.0.0",
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
    return " ".join(text.split())[:4000]

def cache_key(resume: str, jd: str) -> str:
    return "resume:" + hashlib.sha256((resume + jd).encode()).hexdigest()

# ======================================================
# LLM LOGIC
# ======================================================
async def screen_with_llm(resume: str, jd: str) -> dict:
    key = cache_key(resume, jd)

    # Check cache only if Valkey/Redis is available
    if valkey:
        try:
            cached = valkey.get(key)
            if cached:
                data = json.loads(cached)
                data["cache"] = "HIT"
                return data
        except Exception as e:
            print(f"⚠️ Cache read failed: {e}")

    prompt = f"""
You are an expert technical recruiter. Analyze the resume against the job description below.

JOB DESCRIPTION:
{jd}

RESUME:
{resume}

Return valid JSON only with no extra text:
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
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical recruiter. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        result["cache"] = "MISS"
        result["model"] = GROQ_MODEL

        # Store in cache only if Valkey/Redis is available
        if valkey:
            try:
                valkey.setex(key, CACHE_TTL, json.dumps(result))
            except Exception as e:
                print(f"⚠️ Cache write failed: {e}")

        return result

    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise HTTPException(500, f"Groq API error: {e}")

# ======================================================
# ROUTES
# ======================================================
@app.post("/screen")
async def screen(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    if not resume.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF resumes are supported")

    pdf_bytes = await resume.read()
    resume_text = extract_text_from_pdf(pdf_bytes)

    if not resume_text.strip():
        raise HTTPException(400, "Could not extract text from the uploaded PDF")

    return await screen_with_llm(
        normalize_text(resume_text),
        job_description,
    )

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model":  GROQ_MODEL,
        "cache":  "connected" if valkey else "disabled",
    }

# ======================================================
# ENTRYPOINT
# ======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=5000,
        reload=True,
    )