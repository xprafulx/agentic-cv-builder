import os
import time
import PyPDF2

from agents import (
    run_profiler_agent, 
    run_recruiter_agent, 
    run_tailor_agent, 
    run_supervisor_agent,
    run_storyteller_agent
)

# --- Helper Functions ---
def extract_text_from_pdf(pdf_path: str) -> str:
    print(f"📄 Reading {pdf_path}...")
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def safe_latex(text):
    if not isinstance(text, str):
        return str(text)
    return text.replace("%", "\\%").replace("$", "\\$").replace("&", "\\&").replace("_", "\\_").replace("#", "\\#").replace("^", "\\^")

def generate_latex_string(draft_data, template_filename="template.tex"):
    with open(template_filename, 'r', encoding='utf-8') as file:
        template_text = file.read()

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

def generate_cover_letter_latex(cl_draft, cv_draft, template_filename="template_coverletter.tex"):
    with open(template_filename, 'r', encoding='utf-8') as file:
        template_text = file.read()

    final_tex = template_text.replace("<<RECIPIENT_NAME>>", safe_latex(cl_draft.recipient_name))
    final_tex = final_tex.replace("<<HOOK_PARAGRAPH>>", safe_latex(cl_draft.hook_paragraph))
    final_tex = final_tex.replace("<<CAR_STORY_1>>", safe_latex(cl_draft.car_story_1))
    
    story_2 = safe_latex(cl_draft.car_story_2) if cl_draft.car_story_2 else ""
    final_tex = final_tex.replace("<<CAR_STORY_2>>", story_2)
    
    final_tex = final_tex.replace("<<CLOSING_PARAGRAPH>>", safe_latex(cl_draft.closing_paragraph))
    final_tex = final_tex.replace("<<NAME>>", safe_latex(cv_draft.name))

    return final_tex

# --- MAIN EXECUTION ---
def main():
    print("🚀 INITIALIZING 5-AGENT CV & COVER LETTER PIPELINE...\n" + "="*50)
    
    cv_file = "CV.pdf"
    if not os.path.exists(cv_file):
        print(f"❌ ERROR: Could not find '{cv_file}'. Please ensure your master CV is named '{cv_file}'.")
        return

    print("📋 Paste the target Job Description below.")
    print("(When finished typing or pasting, press Enter, type 'DONE', and press Enter again)\n")
    
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

    print("\n" + "="*50)
    
    # 1. Run Analysis Agents
    raw_cv_text = extract_text_from_pdf(cv_file)
    profiler_data = run_profiler_agent(raw_cv_text)
    print("✅ Profiler Agent finished building Master Database.\n")
    
    recruiter_data = run_recruiter_agent(job_description_text)
    print("✅ Recruiter Agent finished extracting Job Requirements.\n")

    # 2. CV Generation & QA Loop
    MAX_RETRIES = 2
    attempt = 1
    is_approved = False
    feedback = ""
    final_cv_draft = None
    
    while attempt <= MAX_RETRIES and not is_approved:
        print(f"🔄 Routing to Tailor Agent (Attempt {attempt}/{MAX_RETRIES})... waiting 5 seconds.")
        time.sleep(5) 
        draft = run_tailor_agent(profiler_data, recruiter_data, feedback)
        
        print("🧐 Routing to Supervisor Agent for QA Audit... waiting 5 seconds.")
        time.sleep(5) 
        review = run_supervisor_agent(draft, recruiter_data)
        
        if review.is_approved:
            print("🟢 SUPERVISOR APPROVED: The CV draft meets all criteria!")
            is_approved = True
            final_cv_draft = draft
        else:
            print(f"🔴 SUPERVISOR REJECTED. Feedback: {review.feedback}")
            feedback = review.feedback
            attempt += 1

    if not is_approved:
        print("⚠️ MAX RETRIES REACHED. Supervisor forced to approve the latest CV draft.")
        final_cv_draft = draft

    # 3. Save CV .tex 
    print("\n⚙️ Formatting CV .tex source code...")
    cv_latex = generate_latex_string(final_cv_draft)
    with open("Tailored_CV.tex", "w", encoding="utf-8") as f:
        f.write(cv_latex)
    print("✅ Tailored CV code saved!")

    # 4. Cover Letter Generation
    print("\n✍️ Routing to Storyteller Agent for CAR-method Cover Letter... waiting 5 seconds.")
    time.sleep(5)
    cl_draft = run_storyteller_agent(profiler_data, recruiter_data)
    
    print("⚙️ Formatting Cover Letter .tex source code...")
    cl_latex = generate_cover_letter_latex(cl_draft, final_cv_draft)
    with open("Tailored_CoverLetter.tex", "w", encoding="utf-8") as f:
        f.write(cl_latex)
    print("✅ Cover Letter code saved!")

    print("\n" + "="*50)
    print("🎉 PIPELINE COMPLETE! Your LaTeX source code is ready in this folder:")
    print("📄 Tailored_CV.tex")
    print("📄 Tailored_CoverLetter.tex")
    print("\n(You can now copy these into Overleaf to generate your PDFs!)")

if __name__ == "__main__":
    main()