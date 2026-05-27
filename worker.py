import redis, json, time, os, threading
from datetime import datetime
from dotenv import load_dotenv
from database import SessionLocal, JobRecord
from heartbeat import write_heartbeat, watchdog
from metrics import (
    jobs_completed, job_duration, job_wait_time,
    queue_depth, active_workers, jobs_running,
    start_metrics_server
)

load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

def process_job(job_data: dict):
    job_id = job_data["id"]
    job_name = job_data["name"]
    submitted_at = job_data.get("submitted_at", time.time())
    db = SessionLocal()
    stop_event = threading.Event()
    wait_seconds = time.time() - submitted_at
    job_wait_time.labels(job_name=job_name).observe(wait_seconds)
    start_time = time.time()

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

        jobs_running.inc()
        active_workers.inc()

        print(f"  → Running: {job_name} (priority {job_data['priority']}, waited {wait_seconds:.1f}s)")
        time.sleep(2)
        if job:
            job.status = "done"
            job.completed_at = datetime.utcnow()
            db.commit()
        jobs_completed.labels(job_name=job_name, status="done").inc()
        print(f"  ✓ Done: {job_name}")
    except Exception as e:
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
        jobs_completed.labels(job_name=job_name, status="failed").inc()
        print(f"  ✗ Failed: {e}")

    finally:
        stop_event.set()
        jobs_running.dec()
        active_workers.dec()
        duration = time.time() - start_time
        job_duration.labels(job_name=job_name).observe(duration)
        queue_depth.set(r.zcard("job_queue"))
        db.close()


def main():
    metrics_port = int(os.getenv("METRICS_PORT", "8002"))
    start_metrics_server(port=metrics_port)
    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()

    print(f"Worker {os.getpid()} started. Metrics on :{metrics_port}")

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