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
