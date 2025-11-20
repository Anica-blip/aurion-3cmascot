"""
Render Background Worker - Direct Supabase Connection
Service Type: Render Background/Aurion
Bot Token: TELEGRAM_BOT_TOKEN (Aurion bot)
TIMEZONE: WEST (UTC+1)
"""
import os
import time
import threading
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import requests

# ============================================
# ENVIRONMENT VARIABLES
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

SERVICE_TYPE = "Render Background/Aurion"
WEST = timezone(timedelta(hours=1))
EXECUTION_TIMES = ["09:00", "12:00", "19:00", "21:00"]
last_execution = None

# ============================================
# VALIDATE ENVIRONMENT VARIABLES
# ============================================
print("\n--- ENVIRONMENT VARIABLE CHECK ---")
if not all([SUPABASE_DB_URL, SUPABASE_SERVICE_ROLE_KEY, TELEGRAM_BOT_TOKEN]):
    print("❌ Missing environment variables:")
    print(f"  SUPABASE_DB_URL: {'SET' if SUPABASE_DB_URL else 'MISSING'}")
    print(f"  SUPABASE_SERVICE_ROLE_KEY: {'SET' if SUPABASE_SERVICE_ROLE_KEY else 'MISSING'}")
    print(f"  TELEGRAM_BOT_TOKEN: {'SET' if TELEGRAM_BOT_TOKEN else 'MISSING'}")
    exit(1)

print("✅ All required environment variables are set\n")

# ============================================
# CREATE SUPABASE CLIENT
# ============================================
supabase: Client = create_client(SUPABASE_DB_URL, SUPABASE_SERVICE_ROLE_KEY)

print(f"[{datetime.now(WEST).isoformat()}] Render Background Worker initialized")
print(f"Supabase URL: {SUPABASE_DB_URL}")
print(f"Service Type: {SERVICE_TYPE}")
print(f"Timezone: WEST (UTC+1)")
print(f"Execution Times: {EXECUTION_TIMES}")

# ============================================
# TELEGRAM API FUNCTIONS
# ============================================

def build_caption(post):
    """Build caption from post data"""
    post_content = post.get('post_content', {})
    
    if not post_content:
        caption = ''
        if post.get('title'):
            caption += f"{post['title']}\n\n"
        if post.get('description'):
            caption += f"{post['description']}\n"
        if post.get('hashtags'):
            tags = ' '.join([tag if tag.startswith('#') else f'#{tag}' for tag in post['hashtags']])
            caption += f"\n{tags}"
        if post.get('cta'):
            caption += f"\n\n👉 {post['cta']}"
        return caption.strip()
    
    caption = ''
    
    name = post_content.get('name') or post.get('name')
    username = post_content.get('username') or post.get('username')
    role = post_content.get('role') or post.get('role')
    
    if name:
        caption += f"<b>{name}</b>\n"
        if username:
            formatted_username = username if username.startswith('@') else f'@{username}'
            caption += f"{formatted_username}\n"
        if role:
            caption += f"{role}\n"
        caption += "\n"
    
    if post_content.get('title'):
        caption += f"{post_content['title']}\n\n"
    
    if post_content.get('description'):
        caption += f"{post_content['description']}\n"
    
    if post_content.get('hashtags'):
        tags = ' '.join([tag if tag.startswith('#') else f'#{tag}' for tag in post_content['hashtags']])
        caption += f"\n{tags}"
    
    if post_content.get('cta'):
        caption += f"\n\n👉 {post_content['cta']}"
    
    return caption.strip()


def send_telegram_message(chat_id, text, thread_id=None):
    """Send text message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if thread_id:
        payload['message_thread_id'] = int(thread_id)
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if not response.ok or not data.get('ok'):
        return {
            'success': False,
            'error': data.get('description', f'HTTP {response.status_code}')
        }
    
    return {
        'success': True,
        'message_id': data.get('result', {}).get('message_id')
    }


def send_telegram_photo(chat_id, photo_url, caption, thread_id=None):
    """Send photo to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    
    if thread_id:
        payload['message_thread_id'] = int(thread_id)
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if not response.ok or not data.get('ok'):
        return {
            'success': False,
            'error': data.get('description', f'HTTP {response.status_code}')
        }
    
    return {
        'success': True,
        'message_id': data.get('result', {}).get('message_id')
    }


def post_to_telegram(post):
    """Post content to Telegram based on media type"""
    try:
        chat_id = post['channel_group_id']
        thread_id = post.get('thread_id')
        caption = build_caption(post)
        
        if len(caption) > 1024:
            raise Exception(f"Caption too long ({len(caption)} chars). Please shorten content to under 1024 characters.")
        
        media_files = []
        
        if post.get('media_files') and isinstance(post['media_files'], list):
            media_files = post['media_files']
        else:
            post_content = post.get('post_content', {})
            if post_content.get('media_files') and isinstance(post_content['media_files'], list):
                media_files = post_content['media_files']
        
        if media_files:
            first_media = media_files[0]
            media_url = first_media.get('url') or first_media.get('src') or first_media.get('supabaseUrl') or first_media
            
            if not isinstance(media_url, str):
                raise Exception('Invalid media URL format')
            
            print(f"🖼️ Uploading photo to Telegram: {media_url}")
            result = send_telegram_photo(chat_id, media_url, caption, thread_id)
        else:
            print('💬 Sending text-only message')
            result = send_telegram_message(chat_id, caption, thread_id)
        
        if not result['success']:
            raise Exception(f"Telegram API error: {result.get('error', 'Unknown error')}")
        
        message_id = str(result.get('message_id', 'unknown'))
        print(f"✅ Telegram upload successful! Message ID: {message_id}")
        
        return {
            'success': True,
            'post_id': message_id
        }
        
    except Exception as e:
        print(f"❌ postToTelegram failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# ============================================
# CORE PROCESSING FUNCTIONS
# ============================================

def claim_jobs(limit=50):
    """Query and claim jobs from scheduled_posts table"""
    try:
        now_utc = datetime.now(timezone.utc)
        now_west = now_utc.astimezone(WEST)
        
        current_date = now_west.strftime("%Y-%m-%d")
        current_time = now_west.strftime("%H:%M:%S")
        
        print(f"\n{'='*60}")
        print('Querying pending jobs...')
        print(f"UTC: {now_utc.isoformat()}")
        print(f"WEST: {now_west.isoformat()}")
        print(f"Current Date: {current_date}")
        print(f"Current Time: {current_time}")
        print(f"Service Type: '{SERVICE_TYPE}'")
        print(f"{'='*60}\n")
        
        # Get all pending posts
        response = supabase.table('scheduled_posts')\
            .select('*')\
            .eq('service_type', SERVICE_TYPE)\
            .eq('posting_status', 'pending')\
            .execute()
        
        all_posts = response.data
        
        if not all_posts:
            print(f"⚠️ No pending posts for '{SERVICE_TYPE}'")
            return []
        
        print(f"Found {len(all_posts)} pending posts with service_type '{SERVICE_TYPE}'")
        
        # Filter for due posts
        due_posts = []
        for post in all_posts:
            post_date_full = post['scheduled_date']
            post_date = post_date_full.split('T')[0]
            post_time = post['scheduled_time']
            
            is_due = (post_date < current_date) or (post_date == current_date and post_time <= current_time)
            
            if is_due:
                print(f"✅ DUE: Post {post['id']} - Date: {post_date}, Time: {post_time}")
                due_posts.append(post)
        
        if not due_posts:
            print("⚠️ No posts due yet")
            return []
        
        print(f"\n📋 {len(due_posts)} posts are due for processing")
        
        # Claim the due posts (limit to max)
        posts_to_process = due_posts[:limit]
        claimed_ids = [post['id'] for post in posts_to_process]
        
        supabase.table('scheduled_posts')\
            .update({'post_status': 'pending'})\
            .in_('id', claimed_ids)\
            .eq('service_type', SERVICE_TYPE)\
            .execute()
        
        print(f"✅ Claimed {len(claimed_ids)} jobs\n")
        return posts_to_process
        
    except Exception as e:
        print(f"Error in claim_jobs: {str(e)}")
        raise


def process_post(post):
    """Process a single post"""
    now = datetime.now(timezone.utc)
    print(f"\n--- Processing Post {post['id']} ---")
    
    try:
        if not post.get('channel_group_id'):
            raise Exception('Missing channel_group_id')
        
        if not post.get('post_content') and not post.get('description') and not post.get('title'):
            raise Exception('Missing post content')
        
        post_result = post_to_telegram(post)
        
        if not post_result['success']:
            raise Exception(post_result.get('error', 'Failed to post to Telegram'))
        
        external_post_id = post_result.get('post_id', 'unknown')
        
        # Update scheduled_posts
        supabase.table('scheduled_posts')\
            .update({
                'posting_status': 'sent',
                'post_status': 'sent',
                'updated_at': now.isoformat()
            })\
            .eq('id', post['id'])\
            .eq('service_type', SERVICE_TYPE)\
            .execute()
        
        # Insert into dashboard_posts
        post_content = post.get('post_content', {})
        
        dashboard_post = {
            'scheduled_post_id': post['id'],
            'social_platform': post.get('social_platform'),
            'post_content': post.get('post_content'),
            'external_post_id': external_post_id,
            'posted_at': now.isoformat(),
            'url': f"https://t.me/c/{post['channel_group_id'].replace('-100', '')}/{external_post_id}" if external_post_id != 'unknown' else post.get('url'),
            'channel_group_id': post.get('channel_group_id'),
            'thread_id': post.get('thread_id'),
            'character_profile': post.get('character_profile') or post_content.get('character_profile'),
            'name': post.get('name') or post_content.get('name'),
            'username': post.get('username') or post_content.get('username'),
            'role': post.get('role') or post_content.get('role'),
            'character_avatar': post.get('character_avatar') or post_content.get('character_avatar'),
            'title': post.get('title') or post_content.get('title'),
            'description': post.get('description') or post_content.get('description'),
            'hashtags': post.get('hashtags') or post_content.get('hashtags'),
            'keywords': post.get('keywords') or post_content.get('keywords'),
            'cta': post.get('cta') or post_content.get('cta'),
            'theme': post.get('theme') or post_content.get('theme'),
            'audience': post.get('audience') or post_content.get('audience'),
            'voice_style': post.get('voice_style') or post_content.get('voice_style'),
            'media_type': post.get('media_type') or post_content.get('media_type'),
            'template_type': post.get('template_type') or post_content.get('template_type'),
            'scheduled_date': post.get('scheduled_date'),
            'scheduled_time': post.get('scheduled_time'),
            'user_id': post.get('user_id'),
            'created_by': post.get('created_by'),
            'content_id': post.get('content_id'),
            'platform_id': post.get('platform_id'),
            'media_files': post.get('media_files') or post_content.get('media_files'),
            'selected_platforms': post.get('selected_platforms') or post_content.get('selected_platforms')
        }
        
        try:
            supabase.table('dashboard_posts').insert(dashboard_post).execute()
            print(f"✅ Inserted into dashboard_posts")
        except Exception as e:
            print(f"⚠️ Failed to insert into dashboard_posts: {str(e)}")
        
        # Delete from scheduled_posts
        try:
            supabase.table('scheduled_posts')\
                .delete()\
                .eq('id', post['id'])\
                .eq('service_type', SERVICE_TYPE)\
                .execute()
            print(f"✅ Deleted post {post['id']} from scheduled_posts")
        except Exception as e:
            print(f"⚠️ Failed to delete from scheduled_posts: {str(e)}")
        
        print(f"✅ Post {post['id']} completed successfully")
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Failed to process post {post['id']}: {error_message}")
        
        max_retries = 3
        new_attempts = (post.get('attempts') or 0) + 1
        should_retry = new_attempts < max_retries
        
        update_data = {
            'post_status': 'failed',
            'attempts': new_attempts
        }
        
        if not should_retry:
            update_data['posting_status'] = 'failed'
        
        try:
            supabase.table('scheduled_posts')\
                .update(update_data)\
                .eq('id', post['id'])\
                .eq('service_type', SERVICE_TYPE)\
                .execute()
        except Exception as fail_error:
            print(f"Failed to update error status: {str(fail_error)}")
        
        raise


def process_jobs():
    """Process all due jobs"""
    start_time = datetime.now(timezone.utc)
    print(f"\n{'='*60}")
    print(f"Processing Started: {start_time.isoformat()}")
    print(f"{'='*60}\n")
    
    errors = []
    succeeded = 0
    failed = 0
    
    try:
        posts = claim_jobs(50)
        
        if not posts:
            return {
                'total_claimed': 0,
                'succeeded': 0,
                'failed': 0,
                'errors': [],
                'timestamp': start_time.isoformat()
            }
        
        for post in posts:
            try:
                process_post(post)
                succeeded += 1
            except Exception as e:
                failed += 1
                errors.append(f"Post {post['id']}: {str(e)}")
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds() * 1000
        
        print(f"\n{'='*60}")
        print(f"Processing Completed")
        print(f"Duration: {duration}ms")
        print(f"✅ Succeeded: {succeeded}")
        print(f"❌ Failed: {failed}")
        print(f"{'='*60}\n")
        
        return {
            'total_claimed': len(posts),
            'succeeded': succeeded,
            'failed': failed,
            'errors': errors,
            'timestamp': start_time.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Fatal error in process_jobs: {str(e)}")
        
        return {
            'total_claimed': 0,
            'succeeded': succeeded,
            'failed': failed,
            'errors': [str(e)] + errors,
            'timestamp': start_time.isoformat()
        }

# ============================================
# SCHEDULER LOOP
# ============================================

def scheduler_loop():
    """Background loop checking execution times"""
    global last_execution
    
    print(f"🕐 Scheduler started for '{SERVICE_TYPE}' at {EXECUTION_TIMES}")
    
    while True:
        try:
            now = datetime.now(WEST)
            current_time = now.strftime("%H:%M")
            execution_key = f"{now.strftime('%Y-%m-%d')}_{current_time}"
            
            if current_time in EXECUTION_TIMES and last_execution != execution_key:
                print(f"\n⏰ Execution time reached ({current_time})")
                last_execution = execution_key
                process_jobs()
            
            time.sleep(60)
            
        except Exception as e:
            print(f"⚠️ Scheduler error: {str(e)}")
            time.sleep(60)


def start_scheduler():
    """Start scheduler in background thread"""
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print(f"✅ Background scheduler thread started")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠️ Shutting down...")
        exit(0)


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    start_scheduler()
    
