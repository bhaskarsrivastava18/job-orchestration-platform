from locust import HttpUser, task, between
import random

class JobUser(HttpUser):
    
    wait_time = between(0.1, 0.5)

    @task(5)  
    def submit_email_job(self):
        self.client.post("/jobs", json={
            "name": "send_email",
            "description": "Send welcome email",
            "priority": random.randint(1, 5),
        })

    @task(3)
    def submit_payment_job(self):
        self.client.post("/jobs", json={
            "name": "process_payment",
            "description": "Process payment",
            "priority": random.randint(6, 10),
        })

    @task(2)
    def submit_report_job(self):
        self.client.post("/jobs", json={
            "name": "generate_report",
            "description": "Generate monthly report",
            "priority": random.randint(3, 7),
        })

    @task(1)
    def check_metrics(self):
        self.client.get("/metrics/summary")