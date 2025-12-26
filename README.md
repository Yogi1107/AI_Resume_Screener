# 🤖 AI Resume Screener

An end-to-end **AI-powered Resume Screening System** that evaluates a
candidate's resume against a given job description using a **Large
Language Model (LLM)**.

------------------------------------------------------------------------

## 📌 Project Overview

This project automates resume screening by analyzing resumes against job
descriptions and providing structured hiring insights similar to an ATS.

------------------------------------------------------------------------

## 🧠 Features

-   Upload PDF resume
-   Paste job description
-   AI-based resume evaluation
-   Match score (0--100)
-   Interview / Reject recommendation
-   Strengths and missing skills

------------------------------------------------------------------------

## 🛠️ Tech Stack

-   Frontend: HTML, CSS, JavaScript
-   Backend: Python, Flask
-   AI / LLM
    - Ollama (Dockerized)
    - LLaMA 3.2 (pulled at runtime)
    - Prompt Engineering
-   PDF Parsing: PyMuPDF

------------------------------------------------------------------------

## 📂 Project Structure

ai-resume-screener/ ├── backend/ │ ├── app.py │ ├── requirements.txt ├──
frontend/ │ └── index.html └── README.md

------------------------------------------------------------------------

## 🐳 Run Using Docker (Recommended)

### Prerequisites
- Docker
- Docker Compose

---

### Step 1: Clone Repository
```bash
git clone https://github.com/your-username/ai-resume-screener.git
cd ai-resume-screener
```

### Step 2: Start Services
```bash
docker-compose up --build
```

This will:
    - Start Ollama container
    - Pull LLaMA 3.2 model
    - Start Flask backend

### Step 3: Pull Model (First Time Only)
```bash
docker exec -it ollama ollama pull llama3.2:3b
```

### Step 4: Access Application
    
    - Backend: http://localhost:5000
    - Health check: http://localhost:5000/health
    - Frontend: open frontend/index.html

---

------------------------------------------------------------------------

## 📦 What is NOT Included in the Repository

- Ollama model files (pulled at runtime)
- Docker images
- Virtual environments
- Environment secrets

This keeps the repository lightweight and secure.

------------------------------------------------------------------------

## 🚀 Setup

1.  Clone repo
2.  Install backend dependencies
3.  Run Ollama
4.  Start Flask server
5.  Open frontend

------------------------------------------------------------------------

## 👤 Author

Yogiraj Bhilare\
M.Sc. Computer Science

------------------------------------------------------------------------

## 📜 License

Educational use only.
