# 🚀 Agentic CV Builder 

An automated, multi-agent LLM architecture built with FastAPI and Google Gemini to dynamically tailor CVs to specific job descriptions. 

## ⚠️ The Problem
Applying for modern tech roles is fundamentally broken:
* **Generic CVs are rejected:** ATS systems and recruiters filter out applications that don't address specific job requirements.
* **Manual tailoring is unscalable:** Rewriting history and adjusting tone for every application takes hours of manual labor.
* **Formatting Fragility:** Copy-pasting text between editors often destroys professional document formatting.

## 💡 The Solution
The **Agentic CV Builder** shifts the paradigm from manual editing to an automated, intelligent pipeline. It orchestrates a team of specialized AI agents to analyze, rewrite, audit, and compile a perfectly tailored LaTeX-based PDF in seconds.

## 🧠 Multi-Agent Architecture
This system utilizes a **Routing & Supervisor Agent Architecture** to ensure high-fidelity outputs:

1. **🕵️‍♂️ Profiler Agent:** Parsers the master CV into a structured JSON schema, preserving core data while removing redundant formatting.
2. **🎯 Recruiter Agent:** Deconstructs the job description to identify "must-have" skills, company culture, and hiring intent.
3. **✍️ Tailor Agent:** Synthesizes data from the Profiler and Recruiter to rewrite bullet points and select relevant experience.
4. **🧐 Supervisor Agent (QA):** The gatekeeper. It audits the final draft against the job description. If requirements are missing, it triggers a **self-correction loop** with specific feedback for the Tailor.

## 🛠️ Tech Stack
* **Language:** Python 3.11+
* **Framework:** FastAPI (Asynchronous Backend)
* **LLM:** Google Gemini 1.5 Flash (via `google-genai` SDK)
* **Schema Validation:** Pydantic (Structured Outputs)
* **Document Engine:** MacTeX / BasicTeX (Automated PDF compilation)
* **UI:** HTML5 / Tailwind CSS / JavaScript

## ⚙️ Local Setup & Installation

**1. Clone the repository**
```bash
git clone [https://github.com/xprafulx/agentic-cv-builder.git](https://github.com/xprafulx/agentic-cv-builder.git)
cd agentic-cv-builder

**2. Set up the Python environment
python -m venv venv
source venv/bin/activate 
pip install -r requirements.txt

**3. Install LaTeX Compiler
brew install --cask basictex
eval "$(/usr/libexec/path_helper)"

**4. Add API Key
Create a .env file in the root:
GEMINI_API_KEY="your_api_key_here"

**5. Start the Server
python -m uvicorn api.py:app --reload
🚀 Usage
Open index.html in your browser. Upload your master PDF, paste the job description, and the system will automatically handle the orchestration and download your tailored .pdf.

Developed as a showcase of Agentic AI and LLMOps workflow orchestration.
