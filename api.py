import os
import time
import PyPDF2
import subprocess
import zipfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents import (
    run_profiler_agent, 
    run_recruiter_agent, 
    run_tailor_agent, 
    run_supervisor_agent,
    run_storyteller_agent # <-- Added our new agent here
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper Functions ---

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def safe_latex(text):
    if not isinstance(text, str):
        return str(text)
    return text.replace("%", "\\%").replace("$", "\\$").replace("&", "\\&").replace("_", "\\_")

def generate_latex_string(draft_data, template_filename="template.tex"):
    try:
        with open(template_filename, 'r', encoding='utf-8') as file:
            template_text = file.read()
    except FileNotFoundError:
        raise Exception(f"❌ ERROR: Could not find {template_filename}.")

    skills_tex = ""
    for category in draft_data.selected_skills:
        skills_joined = ", ".join(category.skills)
        skills_tex += f"    \\item \\textbf{{{safe_latex(category.category_name)}:}} {safe_latex(skills_joined)}\n"
    
    dynamic_sections_tex = ""
    for section in draft_data.tailored_sections:
        dynamic_sections_tex += f"\\section{{{safe_latex(section.section_title)}}}\n"
        for entry in section.entries:
            subtitle_str = f" $|$ \\textit{{{safe_latex(entry.subtitle)}}}" if entry.subtitle else ""
            dynamic_sections_tex += f"\\noindent\\textbf{{{safe_latex(entry.title)}}}{subtitle_str} \\hfill {safe_latex(entry.dates)}\n"
            if entry.expanded_bullets:
                dynamic_sections_tex += "\\begin{itemize}[leftmargin=0.15in, topsep=0pt, partopsep=0pt, itemsep=-2pt]\n"
                for bullet in entry.expanded_bullets:
                    dynamic_sections_tex += f"    \\item {safe_latex(bullet)}\n"
                dynamic_sections_tex += "\\end{itemize}\n"
            dynamic_sections_tex += "\\vspace{4pt}\n\n"

    education_tex = ""
    for edu in draft_data.education:
        subtitle_str = f" $|$ \\textit{{{safe_latex(edu.subtitle)}}}" if edu.subtitle else ""
        education_tex += f"\\noindent\\textbf{{{safe_latex(edu.title)}}}{subtitle_str} \\hfill {safe_latex(edu.dates)}\\\\\n\\vspace{{2pt}}\n\n"

    c = draft_data.contact_info
    contact_parts = []
    if c.location: contact_parts.append(safe_latex(c.location))
    if c.phone: contact_parts.append(safe_latex(c.phone))
    if c.email: contact_parts.append(f"\\href{{mailto:{safe_latex(c.email)}}}{{{safe_latex(c.email)}}}")
    if c.linkedin: contact_parts.append(f"\\href{{https://{safe_latex(c.linkedin)}}}{{LinkedIn}}")
    if c.github: contact_parts.append(f"\\href{{https://{safe_latex(c.github)}}}{{GitHub}}")
    clean_contact_string = " $|$ ".join(contact_parts)

    final_tex = template_text.replace("<<NAME>>", safe_latex(draft_data.name))
    final_tex = final_tex.replace("<<CONTACT>>", clean_contact_string)
    final_tex = final_tex.replace("<<SUMMARY>>", safe_latex(draft_data.summary))
    final_tex = final_tex.replace("<<SKILLS>>", skills_tex)
    final_tex = final_tex.replace("<<DYNAMIC_SECTIONS>>", dynamic_sections_tex)
    final_tex = final_tex.replace("<<EDUCATION>>", education_tex)

    return final_tex

# --- NEW: Cover Letter LaTeX Generator ---
def generate_cover_letter_latex(cl_draft, cv_draft, template_filename="template_coverletter.tex"):
    try:
        with open(template_filename, 'r', encoding='utf-8') as file:
            template_text = file.read()
    except FileNotFoundError:
        raise Exception(f"❌ ERROR: Could not find {template_filename}.")

    final_tex = template_text.replace("<<RECIPIENT_NAME>>", safe_latex(cl_draft.recipient_name))
    final_tex = final_tex.replace("<<HOOK_PARAGRAPH>>", safe_latex(cl_draft.hook_paragraph))
    final_tex = final_tex.replace("<<CAR_STORY_1>>", safe_latex(cl_draft.car_story_1))
    
    story_2 = safe_latex(cl_draft.car_story_2) if cl_draft.car_story_2 else ""
    final_tex = final_tex.replace("<<CAR_STORY_2>>", story_2)
    
    final_tex = final_tex.replace("<<CLOSING_PARAGRAPH>>", safe_latex(cl_draft.closing_paragraph))
    final_tex = final_tex.replace("<<NAME>>", safe_latex(cv_draft.name))

    return final_tex

# --- AI API Routes ---

@app.post("/generate-cv/")
async def generate_cv(file: UploadFile = File(...), job_description: str = Form(...)):
    print(f"📥 Received Request: Processing {file.filename}...")
    temp_pdf_path = f"temp_{file.filename}"
    
    with open(temp_pdf_path, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        raw_cv_text = extract_text_from_pdf(temp_pdf_path)
        
        profiler_data = run_profiler_agent(raw_cv_text)
        recruiter_data = run_recruiter_agent(job_description)
        
        # --- 1. Generate the CV ---
        MAX_RETRIES = 2
        attempt = 1
        is_approved = False
        feedback = ""
        final_cv_draft = None
        
        while attempt <= MAX_RETRIES and not is_approved:
            time.sleep(4) 
            draft = run_tailor_agent(profiler_data, recruiter_data, feedback)
            time.sleep(4) 
            review = run_supervisor_agent(draft, recruiter_data)
            
            if review.is_approved:
                is_approved = True
                final_cv_draft = draft
            else:
                feedback = review.feedback
                attempt += 1

        if not is_approved:
            final_cv_draft = draft
            
        cv_latex = generate_latex_string(final_cv_draft)
        with open("Tailored_CV.tex", "w", encoding="utf-8") as f:
            f.write(cv_latex)
            
        print("⚙️ Compiling CV PDF...")
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "Tailored_CV.tex"], check=True, capture_output=True)

        # --- 2. Generate the Cover Letter ---
        print("✍️ Generating Story-Driven Cover Letter...")
        time.sleep(4) # Respect rate limits
        cl_draft = run_storyteller_agent(profiler_data, recruiter_data)
        cl_latex = generate_cover_letter_latex(cl_draft, final_cv_draft)
        
        with open("Tailored_CoverLetter.tex", "w", encoding="utf-8") as f:
            f.write(cl_latex)
            
        print("⚙️ Compiling Cover Letter PDF...")
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "Tailored_CoverLetter.tex"], check=True, capture_output=True)

        # --- 3. Package both into a ZIP file ---
        zip_filename = "Application_Package.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            zipf.write("Tailored_CV.pdf")
            zipf.write("Tailored_CoverLetter.pdf")

        print("✅ Success! Packaging files...")
        return FileResponse(zip_filename, media_type="application/zip", filename=zip_filename)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up all the temporary files so your Mac doesn't get cluttered
        files_to_remove = [
            temp_pdf_path, 
            "Tailored_CV.tex", "Tailored_CV.aux", "Tailored_CV.log", "Tailored_CV.out",
            "Tailored_CoverLetter.tex", "Tailored_CoverLetter.aux", "Tailored_CoverLetter.log", "Tailored_CoverLetter.out"
        ]
        for f in files_to_remove:
            if os.path.exists(f):
                os.remove(f)

# --- Static Files (The Front Door) ---
app.mount("/", StaticFiles(directory="docs", html=True), name="docs")