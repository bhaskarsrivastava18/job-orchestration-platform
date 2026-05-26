import redis, json, time, os, threading
from datetime import datetime
from dotenv import load_dotenv
from database import SessionLocal, JobRecord
from heartbeat import write_heartbeat, watchdog
load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
def process_job(job_data: dict):
    job_id = job_data["id"]
    db = SessionLocal()
    stop_event = threading.Event()
    try:
        hb_thread = threading.Thread(
            target=write_heartbeat,
            args=(job_id, stop_event),
            daemon=True
        )
        hb_thread.start()
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
        stop_event.set()  
        db.close()

def main():
    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()
    print(f"Worker {os.getpid()} started. Listening...")
    while True:
        result = r.zpopmax("job_queue", count=1)
        if result:
            job_json, score = result[0]
            job_data = json.loads(job_json)
            print(f"\n[Job] Priority {int(score)}: {job_data['name']}")
            process_job(job_data)
        else:
            time.sleep(30)

if __name__ == "__main__":
    main()