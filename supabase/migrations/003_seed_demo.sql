-- 003_seed_demo.sql
-- Demo seed: two clients + a few content units so the dashboard and public
-- surfaces have real-looking data with no live backend.
-- Safe to re-run (ON CONFLICT).

INSERT INTO public.clients (slug, name, niche, shopify_url)
VALUES
  ('cella-coffee', 'Cella Coffee Roasters', 'food-beverage', 'https://cella-coffee.myshopify.com'),
  ('lumen-skincare', 'Lumen Skincare', 'beauty-skincare', 'https://lumen-skincare.myshopify.com')
ON CONFLICT (slug) DO NOTHING;

-- Create the isolated schemas for both demo clients.
SELECT public.create_client_schema('cella-coffee');
SELECT public.create_client_schema('lumen-skincare');

-- A demo blog post row (the MDX files in content/blog/ are the source of truth
-- for the public blog; this row is for any API-driven display).
INSERT INTO public.blog_posts (slug, title, excerpt, category, published, published_at, reading_time)
VALUES
  ('product-descriptions-that-convert',
   'The Shopify description fix most stores skip',
   'Your product page is doing too much. Here is the three-line pattern that lifts add-to-cart.',
   'shopify-growth', true, '2026-06-15', 4),
  ('tiktok-hook-formulas',
   'Five TikTok hooks that still work in 2026',
   'The first two seconds decide everything.',
   'social-strategy', true, '2026-06-18', 5)
ON CONFLICT (slug) DO NOTHING;

-- Bead for the seed.
INSERT INTO public.beads (action, scope, description, reversible)
VALUES ('seed-demo', 'demo',
        'Seeded two demo clients + blog posts for local/dashboard preview', true);
