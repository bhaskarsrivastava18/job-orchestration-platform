from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis, uuid, json, os
from dotenv import load_dotenv
from database import get_db, JobRecord, init_db

load_dotenv()

app = FastAPI(title="Job Orchestration Platform")
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

@app.on_event("startup")
def startup():
    init_db()

class JobRequest(BaseModel):
    name: str
    description: str
    priority: int = 5

@app.post("/jobs")
def create_job(job: JobRequest, db: Session = Depends(get_db)):
    if not 1 <= job.priority <= 10:
        raise HTTPException(status_code=400, detail="Priority must be 1-10")

    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id, "name": job.name,
        "description": job.description, "priority": job.priority
    }

    r.zadd("job_queue", {json.dumps(job_data): job.priority})
    db_job = JobRecord(
        id=job_id, name=job.name,
        description=job.description, priority=job.priority, status="pending"
    )
    db.add(db_job)
    db.commit()

    return {"job_id": job_id, "status": "pending", "priority": job.priority}

@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobRecord).filter(JobRecord.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id, "name": job.name, "status": job.status,
        "priority": job.priority, "created_at": str(job.created_at),
        "started_at": str(job.started_at), "completed_at": str(job.completed_at)
    }

@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobRecord).order_by(JobRecord.created_at.desc()).limit(50).all()
    return [{"id": j.id, "name": j.name, "status": j.status, "priority": j.priority} for j in jobs]

@app.get("/health")
def health():
    r.ping()
    return {"status": "ok", "redis": "connected"}