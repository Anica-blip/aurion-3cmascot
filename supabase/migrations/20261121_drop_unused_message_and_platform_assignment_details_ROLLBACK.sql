-- ROLLBACK for 20261121_drop_unused_message_and_platform_assignment_details.sql
-- Project: 3C Control Center (uqyqpwhkzlhqxcqajhkn)
-- Recreates the empty structure as it was on 21 Nov 2026, including the original access policies.
-- Both tables were empty, so there is no data to restore.
-- Note: the original policies were very open ("allow all"); only restore them if the tables are needed again,
-- and re-run the security advisor afterwards.

CREATE TABLE public.message (
  id bigint NOT NULL,
  content text,
  frequency text,
  group_channel text,
  title jsonb,
  notes text,
  scheduled_at timestamptz DEFAULT now(),
  sent boolean DEFAULT false,
  thread_id text,
  CONSTRAINT message_pkey PRIMARY KEY (id)
);
ALTER TABLE public.message ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow read to everyone" ON public.message FOR SELECT TO public USING (true);

CREATE TABLE public.platform_assignment_details (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  scheduled_post_id uuid NOT NULL,
  platform_id text NOT NULL,
  platform_name text NOT NULL,
  platform_icon text,
  assignment_status text NOT NULL DEFAULT 'pending',
  sent_at timestamptz,
  retry_count integer DEFAULT 0,
  last_retry_at timestamptz,
  external_post_id text,
  user_id uuid NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  delivery_status text,
  CONSTRAINT platform_assignment_details_pkey PRIMARY KEY (id),
  CONSTRAINT chk_assignment_status CHECK (assignment_status = ANY (ARRAY['pending','sent','failed','cancelled'])),
  CONSTRAINT platform_assignment_details_scheduled_post_id_fkey FOREIGN KEY (scheduled_post_id) REFERENCES public.scheduled_posts(id) ON DELETE CASCADE,
  CONSTRAINT platform_assignment_details_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);
ALTER TABLE public.platform_assignment_details ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all operations on platform_assignment_details" ON public.platform_assignment_details FOR ALL TO public USING (true) WITH CHECK (true);
CREATE POLICY "Allow authenticated users" ON public.platform_assignment_details FOR SELECT TO anon, authenticated, service_role USING ((SELECT auth.uid()) = user_id);
CREATE POLICY "Allow service_role FULL ACCESS" ON public.platform_assignment_details FOR ALL TO anon, authenticated, service_role USING ((SELECT auth.uid()) = user_id);
