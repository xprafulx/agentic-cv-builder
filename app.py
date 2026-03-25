import os
import json
import PyPDF2
from dotenv import load_dotenv
from docxtpl import DocxTemplate

# The NEW Google SDK
from google import genai
from google.genai import types

# --- SETUP & CONFIGURATION ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not found in .env file.")

# Initialize the new client
client = genai.Client(api_key=api_key)
target_model = "gemini-2.5-flash"
json_config = types.GenerateContentConfig(response_mime_type="application/json")

# --- CORE FUNCTIONS ---
def ingest_cv(pdf_file_path):
    print(f"Reading {pdf_file_path} and building Master Profile...")
    text = ""
    with open(pdf_file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
            
    prompt = f"""
    You are an expert career data extraction agent. Read the raw CV text provided.
    Extract all details and expand every project and job into at least 5-7 highly detailed, 
    action-oriented bullet points. 
    
    Output strictly as a JSON object with this structure:
    {{
      "name": "...", "contact": "...", "summary": "...", "skills": ["..."],
      "experience": [ {{"company": "...", "role": "...", "dates": "...", "expanded_bullets": ["...", "..."]}} ],
      "projects": [ {{"name": "...", "expanded_bullets": ["...", "..."]}} ],
      "education": [ {{"degree": "...", "university": "...", "dates": "..."}} ],
      "certifications": ["...", "..."]
    }}
    
    Raw CV Text:
    {text}
    """
    response = client.models.generate_content(
        model=target_model, contents=prompt, config=json_config
    )
    return json.loads(response.text)

def tailor_cv(master_profile, job_description):
    print("Cross-referencing Master Profile with the Job Description...")
    prompt = f"""
    You are an elite career strategist. Cross-reference the user's Master Profile with the Job Description.
    
    RULES:
    1. ZERO HALLUCINATIONS: Only use facts, skills, and projects from the Master Profile.
    2. SELECTION: Choose only the most relevant projects/jobs, and select only the top 3-4 bullets for each. 
    
    Output a JSON object EXACTLY matching this structure:
    {{
      "name": "[User Name]",
      "contact": "[User Contact Info]",
      "summary": "[Write a custom 3-sentence summary hooking the JD]",
      "skills": "[Comma separated list of only the most relevant skills]",
      "projects": [ {{ "name": "[Project Name]", "bullets": ["[Best bullet]", "[Second best bullet]"] }} ],
      "experience": [ {{ "role": "[Role Name]", "dates": "[Dates]", "bullets": ["[Best bullet]", "[Second best bullet]"] }} ],
      "education": [ {{ "degree": "[Degree]", "university": "[University Name]", "dates": "[Dates]" }} ],
      "certifications": ["[Most relevant cert 1]", "[Most relevant cert 2]"]
    }}
    
    Master Profile: {json.dumps(master_profile)}
    Job Description: {job_description}
    """
    response = client.models.generate_content(
        model=target_model, contents=prompt, config=json_config
    )
    return json.loads(response.text)

def create_docx(tailored_data, template_path="template.docx", output_path="Tailored_CV.docx"):
    print("Injecting data into Word template...")
    doc = DocxTemplate(template_path)
    doc.render(tailored_data)
    doc.save(output_path)
    print(f"🎉 Success! File saved as: {output_path}")

# --- EXECUTION ---
if __name__ == "__main__":
    # 1. Define your files
    USER_CV_PDF = "CV.pdf"  # Make sure this matches your actual PDF filename!
    TEMPLATE_DOCX = "template.docx"
    OUTPUT_DOCX = "Tailored_Application.docx"
    
    # 2. Paste the target job description here
    TARGET_JOB_DESCRIPTION = """
    [PASTE YOUR JOB DESCRIPTION HERE]
    Looking for a data scientist with strong NLP, Python, and multi-agent system experience...
    """
    
    # 3. Run the pipeline
    try:
        # Check if we already built the master profile to save time/API calls
        if not os.path.exists("master_profile.json"):
            master_data = ingest_cv(USER_CV_PDF)
            with open("master_profile.json", "w") as f:
                json.dump(master_data, f, indent=2)
        else:
            print("Loading existing Master Profile from master_profile.json...")
            with open("master_profile.json", "r") as f:
                master_data = json.load(f)
        
        # Tailor and generate
        final_json = tailor_cv(master_data, TARGET_JOB_DESCRIPTION)
        create_docx(final_json, TEMPLATE_DOCX, OUTPUT_DOCX)
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")