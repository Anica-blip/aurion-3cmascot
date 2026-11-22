-- ROLLBACK for 20261121_drop_old_cron_runner_functions.sql
-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)
-- Recreates the five functions exactly as they were on 21 Nov 2026.
-- Note: the original grants were not captured; re-run the security advisor after restoring.

CREATE OR REPLACE FUNCTION public.comprehensive_scheduled_posts_check()
 RETURNS TABLE(pending_posts_count bigint, processing_posts_count bigint, completed_posts_count bigint, oldest_pending_post timestamp with time zone, newest_pending_post timestamp with time zone)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    log_message TEXT;
BEGIN
    -- Log the diagnostic run
    log_message = format(
        'Diagnostic run at %s: ',
        NOW()
    );

    -- Perform the comprehensive check
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE status = 'pending') as pending_posts_count,
        COUNT(*) FILTER (WHERE status = 'processing') as processing_posts_count,
        COUNT(*) FILTER (WHERE status = 'completed') as completed_posts_count,
        MIN(scheduled_time) FILTER (WHERE status = 'pending') as oldest_pending_post,
        MAX(scheduled_time) FILTER (WHERE status = 'pending') as newest_pending_post
    FROM scheduled_posts;

    -- Log additional details
    INSERT INTO public.diagnostic_logs (
        log_type,
        message
    ) VALUES (
        'scheduled_posts_check',
        log_message
    );
END;
$function$;

CREATE OR REPLACE FUNCTION public.log_post_attempt(p_post_id text, p_status text, p_error_message text DEFAULT NULL::text, p_scheduled_time timestamp with time zone DEFAULT NULL::timestamp with time zone)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
    INSERT INTO post_attempt_logs (
        post_id,
        status,
        error_message,
        scheduled_time
    ) VALUES (
        p_post_id,
        p_status,
        p_error_message,
        COALESCE(p_scheduled_time, NOW())
    );
END;
$function$;

CREATE OR REPLACE FUNCTION public.move_sent_posts_to_dashboard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Only move posts that are newly marked as sent
  IF NEW.posting_status = 'sent' AND (OLD.posting_status IS DISTINCT FROM 'sent') THEN
    INSERT INTO dashboard_posts (
      id,
      user_id,
      platform,
      content,
      media_url,
      scheduled_time,
      created_at,
      updated_at,
      status,
      tags,
      campaign_name,
      post_type,
      metadata,
      notes
    )
    VALUES (
      NEW.id,
      NEW.user_id,
      NEW.platform,
      NEW.content,
      NEW.media_url,
      NEW.scheduled_time,
      COALESCE(NEW.created_at, NOW()),
      NOW(),
      NEW.status,
      NEW.tags,
      NEW.campaign_name,
      NEW.post_type,
      NEW.metadata,
      NEW.notes
    )
    ON CONFLICT (id) DO NOTHING;

    -- Remove the row from scheduled_posts (soft delete action)
    DELETE FROM scheduled_posts WHERE id = NEW.id;
  END IF;

  RETURN NEW;
END;
$function$;

CREATE OR REPLACE FUNCTION public.retry_failed_posts(max_retries integer DEFAULT 3)
 RETURNS TABLE(post_id text, current_status text, retry_result text)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
    RETURN QUERY
    WITH failed_posts AS (
        SELECT
            id::TEXT AS post_id,  -- Cast to TEXT
            posting_status,
            COALESCE(attempt_count, 0) AS current_attempts
        FROM scheduled_posts
        WHERE
            posting_status = 'failed'
            AND COALESCE(attempt_count, 0) < max_retries
    )
    UPDATE scheduled_posts sp
    SET
        posting_status = 'pending',
        attempt_count = COALESCE(sp.attempt_count, 0) + 1,
        last_attempt_at = NOW()
    FROM failed_posts fp
    WHERE sp.id::TEXT = fp.post_id
    RETURNING
        sp.id::TEXT AS post_id,
        sp.posting_status AS current_status,
        'Queued for retry' AS retry_result;
END;
$function$;

CREATE OR REPLACE FUNCTION public.runner_mark_attempt(p_id uuid, p_new_status text, p_increment_attempt boolean, p_retry_count integer DEFAULT NULL::integer, p_failure_reason text DEFAULT NULL::text, p_error_message text DEFAULT NULL::text, p_posting_status text DEFAULT NULL::text, p_post_status text DEFAULT NULL::text)
 RETURNS scheduled_posts
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_updated public.scheduled_posts%ROWTYPE;
BEGIN
  -- Validate input
  IF p_id IS NULL THEN
    RAISE EXCEPTION 'p_id cannot be null';
  END IF;

  -- Perform atomic update
  UPDATE public.scheduled_posts
  SET
    attempt_count = CASE WHEN p_increment_attempt THEN COALESCE(attempt_count, 0) + 1 ELSE attempt_count END,
    last_attempt_at = NOW(),
    status = COALESCE(p_new_status, status),
    retry_count = COALESCE(p_retry_count, retry_count),
    failure_reason = COALESCE(p_failure_reason, failure_reason),
    error_message = COALESCE(p_error_message, error_message),
    posting_status = COALESCE(p_posting_status, posting_status),
    post_status = COALESCE(p_post_status, post_status),
    updated_at = NOW()
  WHERE id = p_id
  RETURNING * INTO v_updated;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'scheduled_posts row with id % not found', p_id;
  END IF;

  RETURN v_updated;
END;
$function$;
