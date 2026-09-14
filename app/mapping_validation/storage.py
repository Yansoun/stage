import os, json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUGGESTIONS_DIR = BASE_DIR / "mapping" / "data" / "processed" / "mappings_v2"
APPROVED_DIR = BASE_DIR / "mapping" / "data" / "processed" / "mappings_approved"

def _safe_job_id(job_id: str):
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise ValueError("Invalid job_id")

def list_jobs():
    if not SUGGESTIONS_DIR.exists():
        return []
    jobs = []
    for fn in os.listdir(SUGGESTIONS_DIR):
        if fn.endswith(".json"):
            jobs.append({"job_id": os.path.splitext(fn)[0], "filename": fn})
    return sorted(jobs, key=lambda x: x["job_id"])

def load_suggestions(job_id: str) -> dict:
    _safe_job_id(job_id)
    path = SUGGESTIONS_DIR / f"{job_id}.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def approved_path(job_id: str) -> str:
    _safe_job_id(job_id)
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    return str(APPROVED_DIR / f"{job_id}_approved.json")

def load_approved(job_id: str):
    path = approved_path(job_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_approved(job_id: str, payload: dict) -> str:
    path = approved_path(job_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path