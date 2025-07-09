import logging
from datetime import datetime, timezone

# Map group_channel names in Supabase to their Telegram numeric chat IDs
GROUP_CHAT_IDS = {
    "group 1": -1002393705231,   # 💭 3C Thread To Success Group
    "group 2": -1002377255109,   # 3C Community ClubHouse Hub
    # Add more as needed, e.g., "channel": <numeric_id>
}

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

def send_due_messages_job(context, supabase):
    """
    Sends all due scheduled messages to their referenced group.
    Marks them as sent in the Supabase table.
    """
    messages = get_due_messages(supabase)
    for msg in messages:
        group_key = msg.get("group_channel")
        chat_id = GROUP_CHAT_IDS.get(group_key)
        content = msg.get("content")

        if not group_key or chat_id is None:
            logging.warning(f"Unknown or unmapped group_channel '{group_key}' for message ID {msg.get('id')}. Skipping.")
            continue
        if not content:
            logging.warning(f"No content for message ID {msg.get('id')}. Skipping.")
            continue

        try:
            context.bot.send_message(chat_id=chat_id, text=content)
            logging.info(f"Sent scheduled message (id={msg.get('id')}) to group '{group_key}' (chat_id={chat_id})")
        except Exception as e:
            logging.error(f"Failed to send message (id={msg.get('id')}) to group '{group_key}' (chat_id={chat_id}): {e}")

        # Mark as sent after sending attempt
        try:
            supabase.table("message").update({"sent": True}).eq("id", msg["id"]).execute()
        except Exception as e:
            logging.error(f"Failed to mark message (id={msg.get('id')}) as sent in DB: {e}")

if __name__ == "__main__":
    print("This module is designed for import and use by the main bot, not for standalone use.")
