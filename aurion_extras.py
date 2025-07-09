import logging
from datetime import datetime, timezone

# Map your group/channel keys (from Supabase message table) to Telegram chat IDs
GROUP_CHAT_IDS = {
    "group 1": -1002393705231,    # Example: replace with your actual group names/IDs
    "group 2": -1002377255109,
    # Add more as needed
}

async def send_due_messages_job(context):
    supabase = context.job.data
    now_utc = datetime.now(timezone.utc).isoformat()
    try:
        # Get messages due to be sent (scheduled time passed and not sent yet)
        result = supabase.table("message").select("*").lte("schedule_at", now_utc).is_("sent", False).execute()
        messages = result.data or []
    except Exception as e:
        logging.error(f"Supabase error in get_due_messages: {e}")
        return

    for msg in messages:
        group_key = msg.get("group_channel")
        chat_id = GROUP_CHAT_IDS.get(group_key)
        content = msg.get("content")
        if not group_key or chat_id is None or not content:
            continue
        try:
            await context.bot.send_message(chat_id=chat_id, text=content)
        except Exception as e:
            logging.error(f"Failed to send message: {e}")
        try:
            supabase.table("message").update({"sent": True}).eq("id", msg["id"]).execute()
        except Exception as e:
            logging.error(f"Failed to mark message as sent: {e}")
