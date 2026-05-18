from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
import redis,uuid,json,os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Job orchestration platform")
r = redis.from_url(os.getenv("REDIS_URL"))
class JobRequest(BaseModel):
    name:str
    description:str
    priority:int=5
class JobResponse(BaseModel):
    job_id: str
    name: str
    status: str
    priority: int
@app.post("/jobs", response_model=JobResponse)
def create_job(job: JobRequest):
    if not 1 <= job.priority <= 10:
        raise HTTPException(status_code=400, detail="Priority must be between 1 and 10")

    job_id = str(uuid.uuid4())
    job_data = {
        "id":          job_id,
        "name":        job.name,
        "description": job.description,
        "priority":    job.priority,
        "status":      "pending"
    }
    r.zadd("job_queue", {json.dumps(job_data): job.priority})
    r.hset(f"job:{job_id}", mapping={
        "status":      "pending",
        "name":        job.name,
        "description": job.description,
        "priority":    job.priority
    })
    return JobResponse(
        job_id=job_id,
        name=job.name,
        status="pending",
        priority=job.priority
    )
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job=r.hgetall(f"job:{job_id}")
    if not job:
        return HTTPException(status_code=404, detail="Job not found")
    return {k.decode(): v.decode() for k, v in job.items()}
@app.get("/jobs")
def list_jobs():
    all_jobs=r.zrange("job_queue",0,-1,withscores=True)
    return {
        "pending_count": len(all_jobs),
        "jobs": [
            {"data": json.loads(job), "priority": score}
            for job, score in all_jobs
        ]
    }
@app.get("/health")
def health():
    r.ping()
    return {"status": "ok", "redis": "connected"}