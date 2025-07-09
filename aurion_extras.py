import logging
from datetime import datetime, timezone

# List of group chat IDs where Aurion is admin and should send scheduled messages.
GROUP_CHAT_IDS = [
    -1002393705231,   # 💭 3C Thread To Success Group
    -1002377255109    # 3C Community ClubHouse Hub
]

def get_due_messages(supabase):
    """
    Fetch scheduled messages from the 'message' table in Supabase
    that are due and not yet marked as sent.
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

async def send_due_messages_job(context, supabase):
    """
    Sends all due scheduled messages to both Telegram groups.
    Marks them as sent in the Supabase table.
    """
    messages = get_due_messages(supabase)
    for msg in messages:
        content = msg.get("content")
        if not content:
            logging.warning(f"No content for message ID {msg.get('id')}. Skipping.")
            continue
        for chat_id in GROUP_CHAT_IDS:
            try:
                await context.bot.send_message(chat_id=chat_id, text=content)
                logging.info(f"Sent scheduled message (id={msg.get('id')}) to group {chat_id}")
            except Exception as e:
                logging.error(f"Failed to send message (id={msg.get('id')}) to group {chat_id}: {e}")
        # Mark as sent
        try:
            supabase.table("message").update({"sent": True}).eq("id", msg["id"]).execute()
        except Exception as e:
            logging.error(f"Failed to mark message (id={msg.get('id')}) as sent in DB: {e}")
