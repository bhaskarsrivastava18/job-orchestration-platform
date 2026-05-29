from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis, uuid, json, os, time
from dotenv import load_dotenv
from database import get_db, JobRecord, init_db
from metrics import (
    jobs_submitted, rate_limit_hits, queue_depth,
    start_metrics_server
) 

from fastapi.middleware.cors import CORSMiddleware
load_dotenv()
app = FastAPI(title="Job Orchestration Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
RATE_LIMIT = 10
RATE_WINDOW_SEC = 60
@app.on_event("startup")
def startup():
    init_db()
    start_metrics_server(port=8001)
class JobRequest(BaseModel):
    name: str
    description: str
    priority: int = 5
def check_rate_limit(job_name: str) -> bool:
    now = time.time()
    window_start = now - RATE_WINDOW_SEC
    key = f"ratelimit:{job_name}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, RATE_WINDOW_SEC)
    results = pipe.execute()
    return results[1] < RATE_LIMIT
@app.post("/jobs")
def create_job(job: JobRequest, db: Session = Depends(get_db)):
    if not 1 <= job.priority <= 10:
        raise HTTPException(status_code=400, detail="Priority must be 1-10")
    if not check_rate_limit(job.name):
        rate_limit_hits.labels(job_name=job.name).inc()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {RATE_LIMIT} '{job.name}' jobs per minute",
            headers={"Retry-After": "60"}
        )
    job_id = str(uuid.uuid4())
    submitted_at = time.time()
    job_data = {
        "id": job_id,
        "name": job.name,
        "description": job.description,
        "priority": job.priority,
        "submitted_at": submitted_at
    }
    r.zadd("job_queue", {json.dumps(job_data): job.priority})
    queue_depth.set(r.zcard("job_queue"))
    db_job = JobRecord(
        id=job_id, name=job.name,
        description=job.description,
        priority=job.priority, status="pending"
    )
    db.add(db_job)
    db.commit()
    jobs_submitted.labels(
        job_name=job.name,
        priority=str(job.priority)
    ).inc()

    return {"job_id": job_id, "status": "pending", "priority": job.priority}
@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobRecord).filter(JobRecord.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id, "name": job.name,
        "status": job.status, "priority": job.priority,
        "created_at": str(job.created_at),
        "started_at": str(job.started_at),
        "completed_at": str(job.completed_at)
    }
@app.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobRecord).order_by(
        JobRecord.created_at.desc()
    ).limit(50).all()
    return [
        {"id": j.id, "name": j.name,
         "status": j.status, "priority": j.priority}
        for j in jobs
    ]
@app.get("/metrics/summary")
def metrics_summary(db: Session = Depends(get_db)):
    """Human-readable metrics summary endpoint."""
    total = db.query(JobRecord).count()
    pending = db.query(JobRecord).filter(JobRecord.status == "pending").count()
    running = db.query(JobRecord).filter(JobRecord.status == "running").count()
    done = db.query(JobRecord).filter(JobRecord.status == "done").count()
    failed = db.query(JobRecord).filter(JobRecord.status == "failed").count()
    return {
        "total_jobs": total,
        "pending": pending,
        "running": running,
        "done": done,
        "failed": failed,
        "queue_depth": r.zcard("job_queue")
    }
@app.get("/health")
def health():
    r.ping()
    return {"status": "ok", "redis": "connected"}