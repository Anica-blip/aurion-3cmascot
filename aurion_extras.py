import logging
from datetime import datetime, timezone

def get_due_messages(supabase):
    """
    Fetch scheduled messages from the 'message' table in Supabase that are due to be sent and not yet marked as sent.
    Returns a list of message dicts.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    try:
        result = (
            supabase.table("message")
            .select("*")
            .lte("schedule_at", now_utc)
            .is_("sent", False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logging.error(f"Supabase error in get_due_messages: {e}")
        return []

async def send_due_messages_job(context, supabase, group_chat_ids):
    """
    Sends all due scheduled messages to their corresponding Telegram groups.
    Marks them as sent in the Supabase table.
    """
    messages = get_due_messages(supabase)
    for msg in messages:
        group = msg.get("group_channel")
        chat_id = group_chat_ids.get(group)
        content = msg.get("content")
        if chat_id and content:
            try:
                await context.bot.send_message(chat_id=chat_id, text=content)
                supabase.table("message").update({"sent": True}).eq("id", msg["id"]).execute()
                logging.info(f"Sent message {msg['id']} to {group}")
            except Exception as e:
                logging.error(f"Failed to send message {msg['id']} to {group}: {e}")

# Example usage (to be called from main.py):
# from aurion_extras import send_due_messages_job
# app.job_queue.run_repeating(lambda context: send_due_messages_job(context, supabase, GROUP_CHAT_IDS), interval=60)
