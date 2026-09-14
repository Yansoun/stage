from pydantic import BaseModel
from typing import Dict, Optional, List

class MappingJob(BaseModel):
    job_id: str
    filename: str

class Candidate(BaseModel):
    target_column: str
    confidence: float

class Suggestion(BaseModel):
    source_column: str
    candidates: List[Candidate]
    best_target: Optional[str] = None
    best_confidence: Optional[float] = None

class SuggestionsResponse(BaseModel):
    job_id: str
    source_file: str
    target_file: str
    suggestions: List[Suggestion]

class ApprovalRequest(BaseModel):
    approved_mapping: Dict[str, Optional[str]]

class ApprovalResponse(BaseModel):
    job_id: str
    saved: bool
    approved_path: str