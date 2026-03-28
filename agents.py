import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError

from schemas import (
    ExtractedCV, 
    JobRequirements, 
    TailoredDraft, 
    SupervisorReview, 
    CoverLetterDraft
)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not found in .env file.")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

# --- THE SENIOR FIX: EXPONENTIAL BACKOFF WRAPPER ---
def call_with_retry(prompt: str, schema: any, temperature: float = 0.1, max_retries: int = 4):
    """Wraps the Gemini API call with automatic retries for Server and Rate Limit Errors."""
    delay = 15  # Start with a 15-second wait to let the API cool down
    
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", 
                    response_schema=schema, 
                    temperature=temperature
                )
            )
            return response
            
        except Exception as e:
            error_str = str(e)
            # Catch both 503 (Server Jam) and 429 (Rate Limit)
            if ("429" in error_str or "503" in error_str) and attempt < max_retries:
                print(f"\n   ⏳ API Speed Limit Hit. Pausing for {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2  # Waits 15s, then 30s, then 60s
            else:
                print("\n   ❌ Max retries reached or unhandled error.")
                raise e
# --- THE AGENTS ---

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
    Extract the rest of the details and group them into logical dynamic sections based EXACTLY on what the user provided.
    Expand every entry into highly detailed, action-oriented bullet points.
    
    Raw CV:
    {raw_cv_text}
    """
    response = call_with_retry(prompt=prompt, schema=ExtractedCV, temperature=0.1)
    return ExtractedCV.model_validate_json(response.text)

def run_recruiter_agent(raw_jd_text: str) -> JobRequirements:
    print("👔 Recruiter Agent: Extracting job requirements...")
    prompt = f"Analyze this job description. Extract the job title, mandatory/preferred skills, core responsibilities, and tone.\n\nJob Description:\n{raw_jd_text}"
    
    response = call_with_retry(prompt=prompt, schema=JobRequirements, temperature=0.1)
    return JobRequirements.model_validate_json(response.text)

def run_tailor_agent(cv_data: ExtractedCV, jd_data: JobRequirements, feedback: str = "") -> TailoredDraft:
    print("✍️ Tailor Agent: Drafting customized CV...")
    feedback_section = f"\nSUPERVISOR FEEDBACK TO FIX:\n{feedback}" if feedback else ""
    prompt = f"""
    You are an elite Career Strategist drafting a tailored CV.
    RULES:
    1. ZERO HALLUCINATIONS. Only use facts from the Master Profile.
    2. DYNAMIC SECTIONS: Rebuild the CV using the custom sections provided by the Profiler. Select the most relevant entries.
    3. TONE: Write in clear, simple, human-readable language. Do not use overly complex vocabulary or dense corporate jargon.
    4. IDENTITY: Copy the user's exact 'name', 'contact_info', and 'education' from the Master Profile directly into your output.
    {feedback_section}
    
    Master Profile: {cv_data.model_dump_json()}
    Job Requirements: {jd_data.model_dump_json()}
    """
    
    response = call_with_retry(prompt=prompt, schema=TailoredDraft, temperature=0.3)
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
    
    response = call_with_retry(prompt=prompt, schema=SupervisorReview, temperature=0.1)
    return SupervisorReview.model_validate_json(response.text)

def run_storyteller_agent(profiler_data, recruiter_data) -> CoverLetterDraft:
    print("✍️ Storyteller Agent: Drafting CAR-method cover letter...")
    prompt = f"""
    You are an elite tech copywriter and career strategist. Your task is to write a highly compelling, storytelling-driven cover letter.
    
    Candidate Data: {profiler_data.model_dump_json()}
    Job Analysis: {recruiter_data.model_dump_json()}
    
    STRICT RULES:
    1. Tone: Simple, human, and conversational. Absolutely NO corporate jargon, buzzwords, or robotic AI speak (e.g., "delve", "testament", "tapestry").
    2. The Hook: Open with tension. What is the immediate technical or business problem this company is trying to solve? Hook their attention immediately.
    3. The Body: Use the CAR method (Context, Action, Result). Tell a specific story from the candidate's CV that proves they can solve the company's problem.
    4. Voice constraint: You must use active voice. Keep passive voice strictly under 10%.
    5. Formatting: Do not include the greeting or the sign-off (these are hardcoded in the template). Just write the core paragraphs.
    """
    
    # Notice the slightly higher temperature here for better storytelling!
    response = call_with_retry(prompt=prompt, schema=CoverLetterDraft, temperature=0.7)
    return CoverLetterDraft.model_validate_json(response.text)