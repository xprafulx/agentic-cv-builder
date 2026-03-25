import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from schemas import ExtractedCV, JobRequirements, TailoredDraft, SupervisorReview

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not found in .env file.")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

def run_profiler_agent(raw_cv_text: str) -> ExtractedCV:
    print("🕵️‍♂️ Profiler Agent: Analyzing raw CV...")
    prompt = f"""
    You are an expert Career Profiler. Read the raw CV.
    
    CONTACT INFO RULES:
    Extract the candidate's specific contact information into the strict fields provided.
    CRITICAL: Strip away all redundant labels. 
    - E.g., Change "Phone: +45 12345678" to JUST "+45 12345678"
    - E.g., Change "Email: user@mail.com" to JUST "user@mail.com"
    - E.g., Change "Address: 123 Main St, City" to JUST "123 Main St, City"
    
    MISSING DATA RULE: 
    If ANY field (email, phone, location, linkedin, github) is missing from the CV, or if the user chose not to include an address, you MUST leave that specific field as an empty string "". Do not invent or guess contact info.

    DYNAMIC SECTIONS RULES:
    Extract the rest of the details and group them into logical dynamic sections based EXACTLY on what the user provided 
    (e.g., 'Work Experience', 'Projects', 'Certifications', 'Training', 'Volunteer Work').
    Expand every entry into highly detailed, action-oriented bullet points.
    
    Raw CV:
    {raw_cv_text}
    """
    response = client.models.generate_content(
        model=MODEL_NAME, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=ExtractedCV, temperature=0.1)
    )
    return ExtractedCV.model_validate_json(response.text)

def run_recruiter_agent(raw_jd_text: str) -> JobRequirements:
    print("👔 Recruiter Agent: Extracting job requirements...")
    prompt = f"Analyze this job description. Extract the job title, mandatory/preferred skills, core responsibilities, and tone.\n\nJob Description:\n{raw_jd_text}"
    response = client.models.generate_content(
        model=MODEL_NAME, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=JobRequirements, temperature=0.1)
    )
    return JobRequirements.model_validate_json(response.text)

def run_tailor_agent(cv_data: ExtractedCV, jd_data: JobRequirements, feedback: str = "") -> TailoredDraft:
    print("✍️ Tailor Agent: Drafting customized CV...")
    feedback_section = f"\nSUPERVISOR FEEDBACK TO FIX:\n{feedback}" if feedback else ""
    prompt = f"""
    You are an elite Career Strategist drafting a tailored CV.
    RULES:
    1. ZERO HALLUCINATIONS. Only use facts from the Master Profile.
    2. DYNAMIC SECTIONS: Rebuild the CV using the custom sections provided by the Profiler (e.g., Certifications, Training, Experience). Select the most relevant entries for each section.
    3. TONE: Write in clear, simple, human-readable language. Do not use overly complex vocabulary or dense corporate jargon.
    4. IDENTITY: Copy the user's exact 'name', 'contact_info', and 'education' from the Master Profile directly into your output.
    {feedback_section}
    
    Master Profile: {cv_data.model_dump_json()}
    Job Requirements: {jd_data.model_dump_json()}
    """
    response = client.models.generate_content(
        model=MODEL_NAME, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=TailoredDraft, temperature=0.3)
    )
    return TailoredDraft.model_validate_json(response.text)

def run_supervisor_agent(draft: TailoredDraft, jd_data: JobRequirements) -> SupervisorReview:
    print("🧐 Supervisor Agent: Auditing the draft...")
    prompt = f"""
    Review the proposed CV Draft against the Job Requirements.
    If it is perfect, set 'is_approved' to True and leave feedback empty.
    If it is flawed, set 'is_approved' to False and write strict feedback on what to fix.
    
    CV Draft: {draft.model_dump_json()}
    Job Requirements: {jd_data.model_dump_json()}
    """
    response = client.models.generate_content(
        model=MODEL_NAME, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=SupervisorReview, temperature=0.1)
    )
    return SupervisorReview.model_validate_json(response.text)