import logging
from datetime import datetime, timezone

def send_due_messages_job(supabase, bot, GROUP_CHAT_IDS):
    now_utc = datetime.now(timezone.utc)
    logging.info("Job triggered at %s", now_utc.isoformat())
    try:
        # Fetch due and unsent messages
        response = (
            supabase.table("message")
            .select("*")
            .lte("scheduled_at", now_utc.isoformat())
            .eq("sent", False)
            .execute()
        )
        messages = response.data
        logging.info("Fetched %d due messages.", len(messages))

        if not messages:
            logging.warning("No due messages found.")
            return

        for msg in messages:
            group_key = msg.get("group_channel")
            chat_id = GROUP_CHAT_IDS.get(group_key)
            if not chat_id:
                logging.error("Unknown group_channel: %s for message ID %s", group_key, msg["id"])
                continue

            try:
                logging.info("Sending message ID %s to group %s (%s): %r", msg["id"], group_key, chat_id, msg["content"])
                bot.send_message(chat_id=chat_id, text=msg["content"])
                # Mark as sent
                supabase.table("message").update({"sent": True}).eq("id", msg["id"]).execute()
                logging.info("Marked message ID %s as sent.", msg["id"])
            except Exception as e:
                logging.exception("Failed to send message ID %s: %s", msg["id"], e)
    except Exception as e:
        logging.exception("Error in send_due_messages_job: %s", e)
