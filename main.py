import os
import json
import PyPDF2
import time  # <-- NEW: We imported the time library here

from agents import (
    run_profiler_agent, 
    run_recruiter_agent, 
    run_tailor_agent, 
    run_supervisor_agent
)

def extract_text_from_pdf(pdf_path: str) -> str:
    print(f"📄 Reading {pdf_path}...")
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def safe_latex(text):
    """Escapes special LaTeX characters to prevent compile errors."""
    if not isinstance(text, str):
        return str(text)
    return text.replace("%", "\\%").replace("$", "\\$").replace("&", "\\&").replace("_", "\\_")

def generate_latex_from_file(draft_data, template_filename="template.tex", output_filename="Tailored_Application.tex"):
    print(f"🖨️ Publisher Agent: Reading '{template_filename}' and formatting document...")
    
    try:
        with open(template_filename, 'r', encoding='utf-8') as file:
            template_text = file.read()
    except FileNotFoundError:
        print(f"❌ ERROR: Could not find {template_filename}.")
        return

    # 1. Format Skills
    skills_tex = ""
    for category in draft_data.selected_skills:
        skills_joined = ", ".join(category.skills)
        skills_tex += f"    \\item \\textbf{{{safe_latex(category.category_name)}:}} {safe_latex(skills_joined)}\n"
    
    # 2. Format Dynamic Sections (Experience, Projects, etc.)
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

    # 3. Format Education
    education_tex = ""
    for edu in draft_data.education:
        subtitle_str = f" $|$ \\textit{{{safe_latex(edu.subtitle)}}}" if edu.subtitle else ""
        education_tex += f"\\noindent\\textbf{{{safe_latex(edu.title)}}}{subtitle_str} \\hfill {safe_latex(edu.dates)}\\\\\n\\vspace{{2pt}}\n\n"

    # 4. Format Contact Info (THE FIX)
    c = draft_data.contact_info
    contact_parts = []
    if c.location: contact_parts.append(safe_latex(c.location))
    if c.phone: contact_parts.append(safe_latex(c.phone))
    if c.email: contact_parts.append(f"\\href{{mailto:{safe_latex(c.email)}}}{{{safe_latex(c.email)}}}")
    if c.linkedin: contact_parts.append(f"\\href{{https://{safe_latex(c.linkedin)}}}{{LinkedIn}}")
    if c.github: contact_parts.append(f"\\href{{https://{safe_latex(c.github)}}}{{GitHub}}")
    clean_contact_string = " $|$ ".join(contact_parts)

    # 5. Inject tags into the template
    final_tex = template_text.replace("<<NAME>>", safe_latex(draft_data.name))
    final_tex = final_tex.replace("<<CONTACT>>", clean_contact_string) # Using the clean string here!
    final_tex = final_tex.replace("<<SUMMARY>>", safe_latex(draft_data.summary))
    final_tex = final_tex.replace("<<SKILLS>>", skills_tex)
    final_tex = final_tex.replace("<<DYNAMIC_SECTIONS>>", dynamic_sections_tex)
    final_tex = final_tex.replace("<<EDUCATION>>", education_tex)

    with open(output_filename, 'w', encoding='utf-8') as file:
        file.write(final_tex)
    print(f"✅ Final Universal CV successfully generated: {output_filename}")

def main():
    print("🚀 INITIALIZING MULTI-AGENT CV PIPELINE...\n" + "="*40)
    
    cv_file = "CV.pdf"
    
    print("📋 Paste the target Job Description below.")
    print("(When finished, press Enter, type 'DONE', and press Enter again)\n")
    
    lines = []
    while True:
        line = input()
        if line.strip().upper() == 'DONE':
            break
        lines.append(line)
        
    job_description_text = "\n".join(lines)
    
    if not job_description_text.strip():
        print("⚠️ No job description provided. Exiting.")
        return
        
    raw_cv_text = extract_text_from_pdf(cv_file)
    profiler_data = run_profiler_agent(raw_cv_text)
    print("✅ Profiler Agent finished building Master Database.\n")
    
    recruiter_data = run_recruiter_agent(job_description_text)
    print("✅ Recruiter Agent finished extracting Job Requirements.\n")
    
    MAX_RETRIES = 2
    attempt = 1
    is_approved = False
    feedback = ""
    final_draft = None
    
    # --- THIS IS WHERE THE PACING FIX LIVES ---
    while attempt <= MAX_RETRIES and not is_approved:
        print(f"🔄 Routing to Tailor Agent (Attempt {attempt}/{MAX_RETRIES})... waiting 5 seconds to avoid server overload.")
        time.sleep(5)  # <-- NEW: Pause before the Tailor Agent
        draft = run_tailor_agent(profiler_data, recruiter_data, feedback)
        
        print("🕵️‍♂️ Routing to Supervisor Agent for QA Audit... waiting 5 seconds.")
        time.sleep(5)  # <-- NEW: Pause before the Supervisor Agent
        review = run_supervisor_agent(draft, recruiter_data)
        
        if review.is_approved:
            print("🟢 SUPERVISOR APPROVED: The draft meets all criteria!")
            is_approved = True
            final_draft = draft
        else:
            print(f"🔴 SUPERVISOR REJECTED. Feedback: {review.feedback}")
            feedback = review.feedback
            attempt += 1

    if not is_approved:
        print("⚠️ MAX RETRIES REACHED. Supervisor forced to approve the latest draft.")
        final_draft = draft
        
    json_filename = "Tailored_CV_Data.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(final_draft.model_dump(), f, indent=4, ensure_ascii=False)
        
    generate_latex_from_file(final_draft)
        
    print("="*40)
    print(f"🎉 PIPELINE COMPLETE! Your tailored CV is ready in 'Tailored_Application.tex'")

if __name__ == "__main__":
    main()