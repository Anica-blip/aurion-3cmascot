"""
Aurion Scheduled Posts Runner - Independent Background Thread
Runs separately from main bot logic
"""

import os
import time
import requests
import json
import threading
from datetime import datetime, timezone, timedelta

# WEST timezone (UTC+1)
WEST = timezone(timedelta(hours=1))

# Execution times in WEST
EXECUTION_TIMES = ["09:00", "12:00", "19:00", "21:00"]

# Track last execution
last_execution = None


def call_gateway():
    """Call Vercel gateway for scheduled posts"""
    gateway_url = os.getenv("VERCEL_GATEWAY_URL")
    db_url = os.getenv("CRON_SUPABASE_DB_URL")
    password = os.getenv("CRON_RUNNER_PASSWORD")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not all([gateway_url, db_url, password, service_role_key]):
        print("⚠️  Scheduled posts: Missing environment variables, skipping...")
        return
    
    try:
        response = requests.post(
            gateway_url,
            headers={
                "Content-Type": "application/json",
                "X-Cron-Password": password,
            },
            json={
                "runner_name": "Aurion Background Worker",
                "service_type": "Render Background/Aurion",
                "db_url": db_url,
                "service_role_key": service_role_key,
            },
            timeout=60
        )
        
        data = response.json()
        
        if response.ok and data.get("success"):
            print(f"✅ Scheduled posts: Processed {data.get('total_claimed', 0)} posts")
        else:
            print(f"⚠️  Scheduled posts: {data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"⚠️  Scheduled posts error: {str(e)}")


def scheduler_loop():
    """Background loop that checks for scheduled execution times"""
    global last_execution
    
    print("🕐 Scheduled posts runner started (09:00, 12:00, 19:00, 21:00 WEST)")
    
    while True:
        try:
            now = datetime.now(WEST)
            current_time = now.strftime("%H:%M")
            execution_key = f"{now.strftime('%Y-%m-%d')}_{current_time}"
            
            if current_time in EXECUTION_TIMES and last_execution != execution_key:
                print(f"\n⏰ Scheduled posts: Execution time reached ({current_time})")
                last_execution = execution_key
                call_gateway()
            
            time.sleep(60)
            
        except Exception as e:
            print(f"⚠️  Scheduler error: {str(e)}")
            time.sleep(60)


def start_scheduler():
    """Start the scheduler in a background thread"""
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
