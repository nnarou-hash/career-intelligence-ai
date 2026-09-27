from typing import List, Optional
from pydantic import BaseModel


class JobOffer(BaseModel):
    company: str
    job_title: str
    location: str
    sector: str
    experience: str
    skills: List[str]
    salary: Optional[str] = None
