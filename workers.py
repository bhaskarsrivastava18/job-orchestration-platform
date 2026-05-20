import redis, json, time, os
from datetime import datetime
from dotenv import load_dotenv
from database import SessionLocal, JobRecord
load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
def process_job(job_data: dict):
    job_id = job_data["id"]
    db = SessionLocal()
    try:
        job = db.query(JobRecord).filter(JobRecord.id == job_id).first()
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        print(f"  → Running: {job_data['name']} (priority {job_data['priority']})")
        time.sleep(2)  
        if job:
            job.status = "done"
            job.completed_at = datetime.utcnow()
            db.commit()

        print(f"  ✓ Done: {job_data['name']}")
    except Exception as e:
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
        print(f"  ✗ Failed: {e}")
    finally:
        db.close()
def main():
    print(f"Worker started (PID: {os.getpid()}). Listening...")
    while True:
        result = r.zpopmax("job_queue", count=1)
        if result:
            job_json, score = result[0]
            job_data = json.loads(job_json)
            print(f"\n[Job] Priority {int(score)}: {job_data['name']}")
            process_job(job_data)
        else:
            time.sleep(1)
if __name__ == "__main__":
    main()