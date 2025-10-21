from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
import threading
import time
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

AMAZON_JOBS_URL = "https://www.amazon.jobs/en/locations/ottawa-canada"
CHECK_INTERVAL = 30  # seconds
DATA_FILE = "data.json"

# Load environment variables
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# Load previously seen jobs
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        known_jobs = json.load(f)
else:
    known_jobs = []

def send_email(job_title, job_link):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"New Amazon Job: {job_title}"

    body = f"A new Amazon job has been posted:\n\nTitle: {job_title}\nLink: {job_link}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent for job: {job_title}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def check_amazon_jobs():
    global known_jobs
    try:
        response = requests.get(AMAZON_JOBS_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        jobs = soup.select("a[href*='/jobs/']")
        for job in jobs:
            title = job.get_text(strip=True)
            link = "https://www.amazon.jobs" + job['href']
            if link not in known_jobs:
                known_jobs.append(link)
                send_email(title, link)
        with open(DATA_FILE, "w") as f:
            json.dump(known_jobs, f)
    except Exception as e:
        print(f"Error checking jobs: {e}")

def check_loop():
    while True:
        check_amazon_jobs()
        time.sleep(CHECK_INTERVAL)

@app.route("/")
def index():
    return render_template("index.html", jobs=known_jobs)

@app.route("/jobs")
def jobs_api():
    return jsonify(known_jobs)

if __name__ == "__main__":
    # Start background thread
    thread = threading.Thread(target=check_loop, daemon=True)
    thread.start()

    # Use Railway PORT if available
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
