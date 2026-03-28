from typing import List
from pydantic import BaseModel, Field
from typing import Optional

class CoverLetterDraft(BaseModel):
    recipient_name: str = Field(description="The name of the hiring manager, or 'Hiring Team' if unknown.")
    hook_paragraph: str = Field(description="The opening. Must create tension or grab attention based on the company's core problem.")
    car_story_1: str = Field(description="A highly relevant story from the CV using the Context, Action, Result method. Simple, human language.")
    car_story_2: Optional[str] = Field(description="A second, shorter CAR story if needed for technical requirements.")
    closing_paragraph: str = Field(description="A confident, brief closing statement.")

class ContactInfo(BaseModel):
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""

class SkillCategory(BaseModel):
    category_name: str
    skills: List[str]

# --- THE UNIVERSAL BLOCKS ---
class CVEntry(BaseModel):
    title: str               # e.g., "Data Scientist" or "Registered Nurse"
    subtitle: str            # e.g., "Company Name" or "Hospital Name" (can be empty)
    dates: str               # e.g., "Jan 2020 - Present"
    expanded_bullets: List[str]

class CVSection(BaseModel):
    section_title: str       # The AI decides this: "Publications", "Clinical Experience", "Projects", etc.
    entries: List[CVEntry]

# --- UPDATED DATA FLOW ---
class ExtractedCV(BaseModel):
    name: str
    contact_info: ContactInfo
    core_skills: List[str]
    education: List[CVEntry] # Using the universal entry for education too
    custom_sections: List[CVSection] # The AI will dynamically create sections here

class JobRequirements(BaseModel):
    job_title: str
    mandatory_skills: List[str]
    preferred_skills: List[str]
    core_responsibilities: List[str]
    company_tone: str

class TailoredDraft(BaseModel):
    name: str
    contact_info: ContactInfo
    summary: str
    selected_skills: List[SkillCategory]
    education: List[CVEntry]
    tailored_sections: List[CVSection] # The final dynamic sections

class SupervisorReview(BaseModel):
    is_approved: bool
    feedback: str