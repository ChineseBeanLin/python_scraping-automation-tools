"""
Dormitory Availability Monitor

Description:
    A persistent service that monitors the student housing website for changes in text.
    It uses a YAML configuration file for easy deployment and management of credentials.
    
    Features:
    - Configuration separation (config.yaml)
    - Anti-bot random intervals
    - SMTP Email alerts
"""

import requests
import random
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import time
import yaml
import os
import sys

# Load configuration file path (assumes config.yaml is in the same directory)
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

# Load YAML Configuration
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # --- Extract Variables from Config ---

    # Web Configuration
    URL = config['web_config']['url']
    TARGET_TEXT = config['web_config']['target_text']
    CHECK_INTERVAL = config['web_config']['check_interval']

    # Receiver Configuration
    EMAIL_RECEIVER = config['receive_emailbox_config']['emailbox']

    # Sender (SMTP) Configuration
    SMTP_SERVER = config['send_emailbox_config']['smtp_server']
    SMTP_PORT = config['send_emailbox_config']['smtp_port']
    SMTP_USER = config['send_emailbox_config']['smtp_user']
    SMTP_PASSWORD = config['send_emailbox_config']['smtp_password']

    # Email Content Configuration
    EMAIL_SUBJECT = config['email_config']['subject']
    EMAIL_TITLE_TEMPLATE = config['email_config']['title']

    print("Configuration loaded successfully.")

except FileNotFoundError:
    print(f"Error: Configuration file not found at {config_path}")
    sys.exit(1)
except KeyError as e:
    print(f"Error: Missing required field in config file: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unknown error while loading config: {e}")
    sys.exit(1)

def fetch_page(url):
    """Fetches the HTML content of the target website."""
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def check_text_change(html, target_text):
    """
    Checks if the target text exists in the HTML.
    Returns True if the text is present (no rooms).
    Returns False if the text is missing (possible availability).
    """
    soup = BeautifulSoup(html, "html.parser")
    # Normalize text to lower case for comparison to be safe
    return target_text.lower() in soup.get_text().lower()

def send_email(subject, body):
    """Sends an email notification via SMTP."""
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [EMAIL_RECEIVER], msg.as_string())
        print("Alert email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def monitor_website():
    """Main loop to monitor website changes."""
    print(f"Starting monitoring service for: {URL}")
    while True:
        # Add random jitter to avoid being detected as a bot
        wait_time = CHECK_INTERVAL + random.randint(1, 5)
        time.sleep(wait_time)
        
        try:
            html = fetch_page(URL)
            if not check_text_change(html, TARGET_TEXT):
                print("Status Change Detected: Target text disappeared!")
                send_email(
                    subject=EMAIL_SUBJECT,
                    body=EMAIL_TITLE_TEMPLATE.format(URL=URL)
                )
                break  # Stop monitoring after sending the alert
            else:
                print(f"No change detected. Checking again in {wait_time}s...")
        except Exception as e:
            print(f"Runtime Error: {e}")
            # Wait longer on error before retrying
            time.sleep(CHECK_INTERVAL + random.randint(50, 100))

if __name__ == "__main__":
    monitor_website()