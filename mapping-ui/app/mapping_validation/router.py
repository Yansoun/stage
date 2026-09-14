from fastapi import APIRouter, HTTPException
from app.mapping_validation.schemas import (
    MappingJob, SuggestionsResponse, ApprovalRequest, ApprovalResponse
)
from app.mapping_validation import storage

router = APIRouter()

@router.get("/jobs", response_model=list[MappingJob])
def jobs():
    return storage.list_jobs()

@router.get("/jobs/{job_id}", response_model=SuggestionsResponse)
def job_details(job_id: str):
    try:
        data = storage.load_suggestions(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")
    except ValueError as e:
        raise HTTPException(400, str(e))

    suggestions = []
    for s in data.get("suggestions", []):
        suggestions.append({
            "source_column": s["source_column"],
            "candidates": [
                {"target_column": c["target_column"], "confidence": c["confidence"]}
                for c in s.get("candidates", [])
            ],
            "best_target": s.get("best_target"),
            "best_confidence": s.get("best_confidence"),
        })

    return {
        "job_id": job_id,
        "source_file": data.get("source_file", ""),
        "target_file": data.get("target_file", ""),
        "suggestions": suggestions,
    }

@router.get("/jobs/{job_id}/approved")
def get_approved(job_id: str):
    try:
        approved = storage.load_approved(job_id)
        return approved or {"job_id": job_id, "approved_mapping": {}}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/jobs/{job_id}/approved", response_model=ApprovalResponse)
def save_approved(job_id: str, req: ApprovalRequest):
    try:
        suggestions = storage.load_suggestions(job_id)  # ensure job exists
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")
    except ValueError as e:
        raise HTTPException(400, str(e))

    payload = {
        "job_id": job_id,
        "source_file": suggestions.get("source_file", ""),
        "target_file": suggestions.get("target_file", ""),
        "approved_mapping": req.approved_mapping,
    }
    path = storage.save_approved(job_id, payload)
    return {"job_id": job_id, "saved": True, "approved_path": path}