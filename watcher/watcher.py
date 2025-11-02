import os
import time
import re
import collections
import json
from slack_sdk.webhook import WebhookClient

# --- Configuration & Environment Loading ---
# Recall that: In a production setup, python-dotenv is used to read variables from 
# the local .env file. Here, Docker Compose passes them directly.

# Inject ID into Title of alert
OPERATOR_ID = os.environ.get("OPERATOR_ID", "UNKNOWN_OP")

# Constants from Environment
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
# Convert threshold to a float
ERROR_RATE_THRESHOLD = float(os.environ.get("ERROR_RATE_THRESHOLD", 2)) / 100
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", 200))
ALERT_COOLDOWN_SEC = int(os.environ.get("ALERT_COOLDOWN_SEC", 300))
LOG_FILE_PATH = "/var/log/nginx/access.log"

# Global State Variables
LAST_SEEN_POOL = os.environ.get("ACTIVE_POOL", "blue") # Initialize with the active pool
ERROR_WINDOW = collections.deque(maxlen=WINDOW_SIZE)
LAST_ALERT_TIME = 0

# Regex to safely parse the custom Nginx log format
# This regex extracts status code, pool, and release from the 'combined_obs' format.
LOG_PATTERN = re.compile(
    r'.*?\s(?P<status>\d{3})\s.*?'
    r'pool=(?P<pool>\w+)\s'
    r'release=(?P<release>[^ ]+)\s'
    r'up_status=(?P<up_status>\d{3})'
)

# Slack Alerting Functions
def send_slack_alert(title, color, text):
    """Posts a formatted message to Slack, prepending the unique OPERATOR_ID."""
    if not SLACK_WEBHOOK_URL or 'T00000000' in SLACK_WEBHOOK_URL:
        print(f"ALERT SKIPPED (NO WEBHOOK): {title}")
        return

    # Injects the unique ID into the title
    unique_title = f"[{OPERATOR_ID}] {title}"

    payload = {
        "text": f":warning: {title}",
        "attachments": [{
            "color": color,
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": title}},
                {"type": "section", "text": {"type": "mrkdwn", "text": text}}
            ]
        }]
    }
    
    try:
        webhook = WebhookClient(SLACK_WEBHOOK_URL)
        response = webhook.send(
            text=f"*{title}*",
            blocks=payload["attachments"][0]["blocks"],
            attachments=[{"color": color, "text": text}] # Fallback structure
        )
        print(f"Slack alert sent successfully: {response.status_code}")
    except Exception as e:
        print(f"Failed to send Slack alert: {e}")

# Core Logic Functions
def check_error_rate(current_request_status):
    """Calculates rolling 5xx error rate and triggers an alert if threshold is breached."""
    global ERROR_WINDOW, LAST_ALERT_TIME

    # Log 5xx upstream status codes (server errors)
    is_error = 500 <= current_request_status <= 599
    ERROR_WINDOW.append(is_error)

    # This only check rate if the window is full
    if len(ERROR_WINDOW) < WINDOW_SIZE:
        return

    error_count = sum(ERROR_WINDOW)
    current_rate = error_count / WINDOW_SIZE
    
    if current_rate >= ERROR_RATE_THRESHOLD:
        cooldown_elapsed = time.time() - LAST_ALERT_TIME
        
        if cooldown_elapsed > ALERT_COOLDOWN_SEC:
            title = f"🔥 HIGH ERROR RATE: {current_rate:.2%} 5XX"
            text = (f"The error rate for the last {WINDOW_SIZE} requests is {current_rate:.2%} "
                    f"(Target: <{ERROR_RATE_THRESHOLD:.2%} ). "
                    f"Action: Check logs for active pool and consider a manual pool toggle.")
            
            send_slack_alert(title, "#ff0000", text) # Red for critical
            LAST_ALERT_TIME = time.time()
            return
    
    # Send a recovery alert if needed (optional, not strictly required by task)
    if current_rate < ERROR_RATE_THRESHOLD and (time.time() - LAST_ALERT_TIME < ALERT_COOLDOWN_SEC) and LAST_ALERT_TIME != 0:
        # A simple debounce mechanism is enough for the recovery
        LAST_ALERT_TIME = 0
        send_slack_alert("✅ RECOVERY: Error Rate Normalized", "#00ff00", "The 5xx error rate has dropped below the threshold.")


def check_failover(current_pool, current_release, current_status):
    """Detects a change in the active pool and triggers a failover alert."""
    global LAST_SEEN_POOL
    
    if current_pool != LAST_SEEN_POOL:
        prev_pool = LAST_SEEN_POOL
        LAST_SEEN_POOL = current_pool
        
        if current_status >= 500:
            # We only alert on the initial flip to prevent spam
            title = f"⚠️ AUTO-FAILOVER DETECTED: {prev_pool} → {current_pool}"
            text = (f"Traffic has automatically switched to the *{current_pool.upper()}* pool. "
                    f"Previous pool ({prev_pool}) failed with status {current_status}. "
                    f"New Release ID: {current_release}. "
                    f"Action: Investigate {prev_pool}'s health and logs immediately.")
            send_slack_alert(title, "#ffcc00", text) # Yellow/Orange for warning/critical event
            return

def tail_logs():
    """Tails the Nginx access log file."""
    print(f"Watcher started. Tailing log file: {LOG_FILE_PATH}")
    
    # Standard log tailing loop
    while not os.path.exists(LOG_FILE_PATH):
        print("Log file not found yet. Waiting for Nginx to start...")
        time.sleep(5)
        
    with open(LOG_FILE_PATH, "r") as f:
        # Move cursor to the end of the file
        f.seek(0, 2) 
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            match = LOG_PATTERN.search(line)
            if match:
                try:
                    data = match.groupdict()
                    pool = data['pool']
                    release = data['release']
                    up_status = int(data['up_status'])
                    
                    # 1. Error Rate Check (Uses the upstream status)
                    check_error_rate(up_status)

                    # 2. Failover Check (Only check if the Nginx request was successful)
                    if int(data['status']) == 200:
                        check_failover(pool, release, up_status)
                        
                except Exception as e:
                    print(f"Error processing line: {e} | Line: {line.strip()}")

if __name__ == "__main__":
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL not set. Running in silent mode.")
    
    # Initialize the log file by ensuring it exists, so 'tail_logs' doesn't wait forever 
    # if Nginx hasn't written anything yet.
    if not os.path.exists(LOG_FILE_PATH):
         os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
         with open(LOG_FILE_PATH, 'a'): 
             os.utime(LOG_FILE_PATH, None)
    
    tail_logs()
