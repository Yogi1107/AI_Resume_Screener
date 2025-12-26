import os
import json
import fitz
from flask import Flask, request, jsonify
from flask_cors import CORS
from ollama import Client

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Ollama client setup
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client = Client(host=OLLAMA_HOST)


# ------------------------------- 
# PDF TEXT EXTRACTION 
# ------------------------------- 
def extract_text_from_pdf(pdf_file) -> str:
    """Extracts and returns text from a PDF file using PyMuPDF."""
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

# ------------------------------- 
# RESUME SCREENING FUNCTION 
# ------------------------------- 
def screen_resume(resume_text: str, job_description: str) -> dict:
    """Screens a resume against a job description using an LLM."""
    # Limit resume size for small models
    resume_text = resume_text[:6000]
    
    system_prompt = """
You are a Senior Technical Recruiter with 20 years of experience. 
You evaluate candidates strictly and objectively. 
You must return ONLY valid JSON. No explanations or extra text.
"""
    
    user_prompt = f"""
JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{resume_text}

TASK:
Analyze the resume against the JD. Be strict but fair.
"React" matches "React.js". "AWS" matches "Amazon Web Services".

Return ONLY valid JSON in the following structure:
{{
  "candidate_name": "string",
  "match_score": 0-100,
  "key_strengths": ["string", "string", "string"],
  "missing_critical_skills": ["string"],
  "recommendation": "Interview" or "Reject",
  "reasoning": "2 sentences max"
}}
"""
    
    try:
        response = client.chat(
            model="llama3.2:3b",
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        result = json.loads(response["message"]["content"])
        return result
    except Exception as e:
        return {
            "error": str(e),
            "candidate_name": "Unknown",
            "match_score": 0,
            "key_strengths": [],
            "missing_critical_skills": [],
            "recommendation": "Error",
            "reasoning": "Failed to process the resume"
        }

# ------------------------------- 
# API ENDPOINTS 
# ------------------------------- 
@app.route('/screen', methods=['POST'])
def screen():
    """API endpoint to screen a resume."""
    try:
        # Check if files are present
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
        
        if 'job_description' not in request.form:
            return jsonify({"error": "No job description provided"}), 400
        
        resume_file = request.files['resume']
        job_description = request.form['job_description']
        
        # Validate PDF file
        if not resume_file.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(resume_file)
        
        if not resume_text.strip():
            return jsonify({"error": "Could not extract text from PDF"}), 400
        
        # Screen the resume
        result = screen_resume(resume_text, job_description)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "Resume Screener API is running"}), 200

# ------------------------------- 
# MAIN EXECUTION 
# ------------------------------- 
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting Resume Screener API...")
    print("=" * 60)
    print("📡 Server running on: http://localhost:5000")
    print("🤖 Ollama endpoint: http://localhost:11434")
    print("📄 API Documentation:")
    print("   - POST /screen  -> Screen a resume")
    print("   - GET  /health  -> Check API health")
    print("=" * 60)
    print("⚠️  Make sure Ollama is running with llama3.2:3b model!")
    print("   Run: ollama serve")
    print("   Run: ollama pull llama3.2:3b")
    print("=" * 60)
    print()
    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000)
