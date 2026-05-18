import redis, json, time, os
from dotenv import load_dotenv
load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL"))
def process_job(job_data: dict):
    job_id = job_data["id"]
    print(f"  → Running job: {job_data['name']} (priority {job_data['priority']})")
    r.hset(f"job:{job_id}", "status", "running")
    time.sleep(2)
    r.hset(f"job:{job_id}", "status", "done")
    print(f"  ✓ Done: {job_data['name']}")
def main():
    print("Worker started. Listening for jobs...")
    print("Priority queue: highest priority jobs run first.\n")

    while True:
        result = r.zpopmax("job_queue", count=1)
        if result:
            job_json, score = result[0]
            job_data = json.loads(job_json)
            print(f"\n[Job received] Priority {int(score)}: {job_data['name']}")
            process_job(job_data)
        else:
            time.sleep(1)

if __name__ == "__main__":
    main()