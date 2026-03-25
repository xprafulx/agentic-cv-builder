import os
import time
import PyPDF2
import subprocess
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agents import (
    run_profiler_agent, 
    run_recruiter_agent, 
    run_tailor_agent, 
    run_supervisor_agent
)

app = FastAPI()

# Enable CORS so our local HTML file is allowed to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        MAX_RETRIES = 2
        attempt = 1
        is_approved = False
        feedback = ""
        final_draft = None
        
        while attempt <= MAX_RETRIES and not is_approved:
            time.sleep(4) # Pacing the API
            draft = run_tailor_agent(profiler_data, recruiter_data, feedback)
            
            time.sleep(4) # Pacing the API
            review = run_supervisor_agent(draft, recruiter_data)
            
            if review.is_approved:
                is_approved = True
                final_draft = draft
            else:
                feedback = review.feedback
                attempt += 1

        if not is_approved:
            final_draft = draft
            
        latex_content = generate_latex_string(final_draft)
        
        # Save the .tex file
        tex_filename = "Tailored_Application.tex"
        with open(tex_filename, "w", encoding="utf-8") as f:
            f.write(latex_content)
            
        print("⚙️ Compiling LaTeX to PDF... (This takes a few seconds)")
        
        # Call the MacTeX compiler
        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_filename],
                check=True,
                capture_output=True
            )
            print("✅ PDF successfully compiled!")
        except subprocess.CalledProcessError as e:
            print(f"❌ LaTeX Error: {e.stdout.decode('utf-8')}")
            raise HTTPException(status_code=500, detail="Failed to compile PDF.")

        pdf_filename = "Tailored_Application.pdf"
            
        print("✅ Success! Sending PDF to frontend.")
        return FileResponse(pdf_filename, media_type="application/pdf", filename=pdf_filename)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary uploaded PDF
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            
        # Clean up LaTeX junk files
        for ext in [".aux", ".log", ".out"]:
            junk_file = f"Tailored_Application{ext}"
            if os.path.exists(junk_file):
                os.remove(junk_file)