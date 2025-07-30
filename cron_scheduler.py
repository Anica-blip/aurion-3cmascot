import requests
import json
import os
from datetime import datetime

# Bot's Supabase credentials
BOT_SUPABASE_URL = "https://cgxjqsbrditbteqhdyus.supabase.co"
BOT_SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNneGpxc2JyZGl0YnRlcWhkeXVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTExMTY1ODEsImV4cCI6MjA2NjY5MjU4MX0.xUDy5ic-r52kmRtocdcW8Np9-lczjMZ6YKPXc03rIG4"

# Bot's edge function URL
EDGE_FUNCTION_URL = f"{BOT_SUPABASE_URL}/functions/v1/scheduled-posts-cron"

def call_scheduled_posts_cron():
    """Call the Supabase edge function to process scheduled posts"""
    try:
        print(f"[{datetime.now()}] Calling scheduled posts cron...")
        
        headers = {
            'Authorization': f'Bearer {BOT_SUPABASE_ANON_KEY}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(EDGE_FUNCTION_URL, headers=headers, json={})
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cron job successful: {result}")
            
            # Process the posts returned by the edge function
            if 'results' in result:
                for post_result in result['results']:
                    if post_result['status'] == 'sent' and 'data' in post_result:
                        process_post_for_telegram(post_result['data'])
            
            return result
        else:
            print(f"❌ Cron job failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error calling cron job: {str(e)}")
        return None

def process_post_for_telegram(post_data):
    """Process a post and send it to Telegram"""
    try:
        print(f"📤 Processing post for Telegram: {post_data['id']}")
        
        # Extract post details
        description = post_data.get('description', '')
        media = post_data.get('media')
        character = post_data.get('character')
        
        # Build the message
        message_text = description
        
        # Add character info if available
        if character:
            message_text = f"[{character.get('name', 'Bot')}] {message_text}"
        
        print(f"📝 Message: {message_text}")
        
        # Check if there's media to send
        if media and media.get('file_url'):
            print(f"🖼️ Media URL: {media['file_url']}")
            print(f"📁 Media Type: {media.get('file_type', 'unknown')}")
            
            # Here you can integrate with your existing Telegram bot code
            # to send the image + caption to your groups
            send_media_to_telegram(media['file_url'], message_text, media.get('file_type'))
        else:
            # Text-only post
            send_text_to_telegram(message_text)
            
    except Exception as e:
        print(f"❌ Error processing post: {str(e)}")

def send_media_to_telegram(file_url, caption, file_type):
    """Send media to Telegram - integrate with your existing bot"""
    # TODO: Integrate with your existing Telegram bot code
    # This is where you'll use your bot's send_photo() or send_document() methods
    print(f"🚀 Would send media: {file_url} with caption: {caption}")
    pass

def send_text_to_telegram(text):
    """Send text message to Telegram - integrate with your existing bot"""
    # TODO: Integrate with your existing Telegram bot code
    print(f"🚀 Would send text: {text}")
    pass

if __name__ == "__main__":
    call_scheduled_posts_cron()
