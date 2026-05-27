from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
jobs_submitted = Counter(
    'jobs_submitted_total',
    'Total number of jobs submitted',
    ['job_name', 'priority'] 
)

jobs_completed = Counter(
    'jobs_completed_total',
    'Total number of jobs completed',
    ['job_name', 'status']  
)

jobs_requeued = Counter(
    'jobs_requeued_total',
    'Total number of jobs re-queued by watchdog'
)

rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Total number of rate limit rejections',
    ['job_name']
)
job_duration = Histogram(
    'job_duration_seconds',
    'Time taken to process a job',
    ['job_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

job_wait_time = Histogram(
    'job_wait_seconds',
    'Time job spent waiting in queue before pickup',
    ['job_name'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]
)
queue_depth = Gauge(
    'queue_depth',
    'Number of jobs currently in the Redis queue'
)

active_workers = Gauge(
    'active_workers',
    'Number of currently active workers'
)

jobs_running = Gauge(
    'jobs_running',
    'Number of jobs currently being processed'
)


def start_metrics_server(port: int = 8001):
    """Start Prometheus metrics server on a separate port."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")