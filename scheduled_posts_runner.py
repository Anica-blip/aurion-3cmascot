"""
Render Background Worker - Direct PostgreSQL Connection
Service Type: Render Background/Aurion
Bot Token: TELEGRAM_BOT_TOKEN (Aurion bot)
TIMEZONE: WEST (UTC+1)
"""
import os
import time
import json
import threading
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# ============================================
# ENVIRONMENT VARIABLES
# ============================================
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
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
# DATABASE CONNECTION
# ============================================
def get_db_connection():
    """Create a new PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        raise

print(f"[{datetime.now(WEST).isoformat()}] Render Background Worker initialized")
print(f"Database: PostgreSQL Direct Connection")
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


def send_telegram_video(chat_id, video_url, caption, thread_id=None):
    """Send video to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    
    payload = {
        'chat_id': chat_id,
        'video': video_url,
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


def send_telegram_animation(chat_id, animation_url, caption, thread_id=None):
    """Send animation/GIF to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAnimation"
    
    payload = {
        'chat_id': chat_id,
        'animation': animation_url,
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


def send_telegram_document(chat_id, document_url, caption, thread_id=None):
    """Send document to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    
    payload = {
        'chat_id': chat_id,
        'document': document_url,
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


def detect_media_type(media_url, media_item=None):
    """Detect media type from URL extension or media_item type field"""
    # First check if media_item has explicit type field
    if media_item and isinstance(media_item, dict):
        media_type = media_item.get('type') or media_item.get('media_type') or media_item.get('mediaType')
        if media_type:
            media_type_lower = media_type.lower()
            if 'video' in media_type_lower:
                return 'video'
            elif 'gif' in media_type_lower or 'animation' in media_type_lower:
                return 'animation'
            elif 'image' in media_type_lower or 'photo' in media_type_lower:
                return 'photo'
            elif 'document' in media_type_lower or 'file' in media_type_lower:
                return 'document'
    
    # Fall back to URL extension detection
    if not isinstance(media_url, str):
        return 'photo'  # Default
    
    media_url_lower = media_url.lower()
    
    # Video extensions
    if any(ext in media_url_lower for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']):
        return 'video'
    
    # Animation/GIF extensions
    if '.gif' in media_url_lower:
        return 'animation'
    
    # Document extensions
    if any(ext in media_url_lower for ext in ['.pdf', '.doc', '.docx', '.txt', '.zip', '.rar', '.csv', '.xls', '.xlsx']):
        return 'document'
    
    # Image extensions (default)
    if any(ext in media_url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.svg']):
        return 'photo'
    
    # Default to photo if no match
    return 'photo'


def parse_media_file(media_item):
    """Parse media file from various JSON structures"""
    if isinstance(media_item, str):
        # Direct URL string
        return media_item
    
    if isinstance(media_item, dict):
        # Try various common key names
        return (
            media_item.get('url') or 
            media_item.get('src') or 
            media_item.get('supabaseUrl') or 
            media_item.get('file_url') or
            media_item.get('media_url') or
            media_item.get('path') or
            None
        )
    
    return None


def post_to_telegram(post):
    """Post content to Telegram based on media type"""
    try:
        chat_id = post['channel_group_id']
        thread_id = post.get('thread_id')
        caption = build_caption(post)
        
        if len(caption) > 1024:
            raise Exception(f"Caption too long ({len(caption)} chars). Please shorten content to under 1024 characters.")
        
        # Parse media_files from various sources
        media_files = []
        
        if post.get('media_files'):
            if isinstance(post['media_files'], list):
                media_files = post['media_files']
            elif isinstance(post['media_files'], str):
                # If media_files is a JSON string, try to parse it
                try:
                    media_files = json.loads(post['media_files'])
                except:
                    pass
        
        # Fallback to post_content.media_files
        if not media_files:
            post_content = post.get('post_content', {})
            if post_content.get('media_files'):
                if isinstance(post_content['media_files'], list):
                    media_files = post_content['media_files']
                elif isinstance(post_content['media_files'], str):
                    try:
                        media_files = json.loads(post_content['media_files'])
                    except:
                        pass
        
        # If we have media, send with appropriate method
        if media_files:
            first_media = media_files[0]
            media_url = parse_media_file(first_media)
            
            if not media_url:
                raise Exception('Could not extract media URL from media_files')
            
            if not isinstance(media_url, str):
                raise Exception('Invalid media URL format')
            
            # Detect media type
            media_type = detect_media_type(media_url, first_media)
            
            print(f"📎 Detected media type: {media_type}")
            print(f"🔗 Media URL: {media_url}")
            
            # Send based on media type
            if media_type == 'video':
                print(f"🎥 Uploading video to Telegram")
                result = send_telegram_video(chat_id, media_url, caption, thread_id)
            elif media_type == 'animation':
                print(f"🎬 Uploading animation/GIF to Telegram")
                result = send_telegram_animation(chat_id, media_url, caption, thread_id)
            elif media_type == 'document':
                print(f"📄 Uploading document to Telegram")
                result = send_telegram_document(chat_id, media_url, caption, thread_id)
            else:  # photo
                print(f"🖼️ Uploading photo to Telegram")
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
# CORE PROCESSING FUNCTIONS (PostgreSQL)
# ============================================

def claim_jobs(limit=50):
    """Query and claim jobs from scheduled_posts table"""
    conn = None
    cursor = None
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query scheduled_posts with PostgreSQL
        query = """
            SELECT * FROM scheduled_posts 
            WHERE service_type = %s 
            AND posting_status = 'scheduled'
            AND scheduled_date = %s
            AND scheduled_time <= %s
            ORDER BY scheduled_time ASC
            LIMIT %s
        """
        
        cursor.execute(query, (SERVICE_TYPE, current_date, current_time, limit))
        posts = cursor.fetchall()
        
        if not posts:
            print("No pending jobs found")
            return []
        
        print(f"Found {len(posts)} pending job(s)")
        
        # Claim jobs by updating status to 'processing'
        post_ids = [post['id'] for post in posts]
        
        update_query = """
            UPDATE scheduled_posts 
            SET posting_status = 'processing'
            WHERE id = ANY(%s) AND service_type = %s
        """
        
        cursor.execute(update_query, (post_ids, SERVICE_TYPE))
        conn.commit()
        
        print(f"✅ Claimed {len(posts)} job(s) for processing")
        
        # Convert RealDictRow to regular dict for easier handling
        posts_to_process = [dict(post) for post in posts]
        
        return posts_to_process
        
    except Exception as e:
        print(f"Error in claim_jobs: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def process_post(post):
    """Process a single post"""
    conn = None
    cursor = None
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update scheduled_posts
        update_query = """
            UPDATE scheduled_posts
            SET posting_status = 'sent', post_status = 'sent', updated_at = %s
            WHERE id = %s AND service_type = %s
        """
        
        cursor.execute(update_query, (now.isoformat(), post['id'], SERVICE_TYPE))
        conn.commit()
        
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
            insert_query = """
                INSERT INTO dashboard_posts (
                    scheduled_post_id, social_platform, post_content, external_post_id, posted_at, url,
                    channel_group_id, thread_id, character_profile, name, username, role, character_avatar,
                    title, description, hashtags, keywords, cta, theme, audience, voice_style, media_type,
                    template_type, scheduled_date, scheduled_time, user_id, created_by, content_id, 
                    platform_id, media_files, selected_platforms
                ) VALUES (
                    %(scheduled_post_id)s, %(social_platform)s, %(post_content)s, %(external_post_id)s, 
                    %(posted_at)s, %(url)s, %(channel_group_id)s, %(thread_id)s, %(character_profile)s, 
                    %(name)s, %(username)s, %(role)s, %(character_avatar)s, %(title)s, %(description)s, 
                    %(hashtags)s, %(keywords)s, %(cta)s, %(theme)s, %(audience)s, %(voice_style)s, 
                    %(media_type)s, %(template_type)s, %(scheduled_date)s, %(scheduled_time)s, %(user_id)s, 
                    %(created_by)s, %(content_id)s, %(platform_id)s, %(media_files)s, %(selected_platforms)s
                )
            """
            
            cursor.execute(insert_query, dashboard_post)
            conn.commit()
            print(f"✅ Inserted into dashboard_posts")
        except Exception as e:
            print(f"⚠️ Failed to insert into dashboard_posts: {str(e)}")
            conn.rollback()
        
        # Delete from scheduled_posts
        try:
            delete_query = """
                DELETE FROM scheduled_posts
                WHERE id = %s AND service_type = %s
            """
            
            cursor.execute(delete_query, (post['id'], SERVICE_TYPE))
            conn.commit()
            print(f"✅ Deleted post {post['id']} from scheduled_posts")
        except Exception as e:
            print(f"⚠️ Failed to delete from scheduled_posts: {str(e)}")
            conn.rollback()
        
        print(f"✅ Post {post['id']} completed successfully")
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Failed to process post {post['id']}: {error_message}")
        
        max_retries = 3
        new_attempts = (post.get('attempts') or 0) + 1
        should_retry = new_attempts < max_retries
        
        try:
            if not conn:
                conn = get_db_connection()
                cursor = conn.cursor()
            
            update_data = {
                'post_status': 'failed',
                'attempts': new_attempts
            }
            
            if not should_retry:
                update_data['posting_status'] = 'failed'
            
            update_query = """
                UPDATE scheduled_posts
                SET post_status = %s, attempts = %s
            """
            params = [update_data['post_status'], update_data['attempts']]
            
            if not should_retry:
                update_query += ", posting_status = %s"
                params.append(update_data['posting_status'])
            
            update_query += " WHERE id = %s AND service_type = %s"
            params.extend([post['id'], SERVICE_TYPE])
            
            cursor.execute(update_query, params)
            conn.commit()
        except Exception as fail_error:
            print(f"Failed to update error status: {str(fail_error)}")
            if conn:
                conn.rollback()
        
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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
    """Start scheduler in background thread (non-blocking when imported)"""
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print(f"✅ Background scheduler thread started for '{SERVICE_TYPE}'")


def start_scheduler_blocking():
    """Start scheduler and keep main thread alive (for standalone mode)"""
    start_scheduler()
    
    # Keep main thread alive
    try:
        print("🔄 Running in standalone mode - press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠️ Shutting down...")
        exit(0)


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    start_scheduler_blocking()
    
