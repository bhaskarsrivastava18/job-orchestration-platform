import redis, json, time, os, threading
from datetime import datetime
from dotenv import load_dotenv
from database import SessionLocal, JobRecord

load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

HEARTBEAT_TTL     = 12   
HEARTBEAT_INTERVAL = 5
WATCHDOG_INTERVAL  = 10  

def write_heartbeat(job_id: str, stop_event: threading.Event):
    """Write heartbeat every 5 seconds while job is running."""
    while not stop_event.is_set():
        r.setex(f"heartbeat:{job_id}", HEARTBEAT_TTL, "alive")
        time.sleep(HEARTBEAT_INTERVAL)

def watchdog():
    """Scan for running jobs with missing heartbeats. Re-queue them."""
    print("[Watchdog] Started.")
    while True:
        time.sleep(WATCHDOG_INTERVAL)
        db = SessionLocal()
        try:
            running_jobs = db.query(JobRecord).filter(JobRecord.status == "running").all()

            for job in running_jobs:
                heartbeat = r.get(f"heartbeat:{job.id}")
                if not heartbeat:
                   
                    print(f"[Watchdog] Dead worker detected for job {job.id[:8]}. Re-queuing...")
                    job_data = {
                        "id": job.id, "name": job.name,
                        "description": job.description, "priority": job.priority
                    }
                   
                    r.zadd("job_queue", {json.dumps(job_data): job.priority})
                  
                    job.status = "pending"
                    job.started_at = None
                    db.commit()
                    print(f"[Watchdog] ✓ Job {job.id[:8]} re-queued successfully.")

        except Exception as e:
            print(f"[Watchdog] Error: {e}")
        finally:
            db.close()
            