from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import redis, uuid, json, os
from dotenv import load_dotenv
from database import get_db, JobRecord, init_db
from fastapi import Request
from fastapi.responses import JSONResponse

load_dotenv()

RATE_LIMIT      = 10   
RATE_WINDOW_SEC = 60
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

    # Rate limit check
    if not check_rate_limit(job.name):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {RATE_LIMIT} '{job.name}' jobs per minute",
            headers={"Retry-After": "60"}
        )

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
def check_rate_limit(job_name: str) -> bool:
    """
    Sliding window rate limit using Redis sorted set.
    Key: ratelimit:{job_name}
    Score: timestamp
    Count entries in last 60 seconds.
    """
    now = time.time()
    window_start = now - RATE_WINDOW_SEC
    key = f"ratelimit:{job_name}"

    pipe = r.pipeline()
    # Remove old entries outside the window
    pipe.zremrangebyscore(key, 0, window_start)
    # Count entries in current window
    pipe.zcard(key)
    # Add current timestamp
    pipe.zadd(key, {str(now): now})
    # Set TTL so key auto-expires
    pipe.expire(key, RATE_WINDOW_SEC)
    results = pipe.execute()

    current_count = results[1]
    return current_count < RATE_LIMIT

# Add this import at the top
import time