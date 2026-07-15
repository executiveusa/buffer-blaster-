-- 004_blog_posts.sql
-- Blog posts table (not in the original buffer-blaster 001 schema).
-- The public blog reads from MDX files in content/blog/ at build time;
-- this table is for any API-driven blog management on the VPS.

CREATE TABLE IF NOT EXISTS public.blog_posts (
  id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug         text UNIQUE NOT NULL,
  title        text NOT NULL,
  excerpt      text,
  content      text,
  category     text,
  published    boolean DEFAULT false,
  published_at timestamptz,
  reading_time int,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

ALTER TABLE public.blog_posts ENABLE ROW LEVEL SECURITY;

-- Published posts are publicly readable.
DROP POLICY IF EXISTS "public_read_published" ON public.blog_posts;
CREATE POLICY "public_read_published" ON public.blog_posts
  FOR SELECT USING (published = true);

-- Service role can do everything.
DROP POLICY IF EXISTS "service_all_blog" ON public.blog_posts;
CREATE POLICY "service_all_blog" ON public.blog_posts
  FOR ALL USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
