-- 021_usage_priced_actuals.sql
-- S4 r4 (reviewer M1): separately-labeled computed cost. Providers report
-- token counts but no cost on most APIs; pricing those tokens at the
-- CONFIGURED vendor list price settles caps accurately without ever
-- falsifying actual_cents (provider-reported only).
ALTER TABLE buffer_blaster.usage_events
  ADD COLUMN IF NOT EXISTS priced_actual_cents integer
    CHECK (priced_actual_cents IS NULL OR priced_actual_cents >= 0),
  ADD COLUMN IF NOT EXISTS cost_provenance text
    CHECK (cost_provenance IS NULL OR cost_provenance IN
           ('provider_reported', 'computed_from_provider_tokens', 'reservation_estimate'));

COMMENT ON COLUMN buffer_blaster.usage_events.priced_actual_cents IS
  'Cost computed from provider-reported token counts at the configured vendor list price. Never a provider-reported actual; actual_cents stays provider-only.';
COMMENT ON COLUMN buffer_blaster.usage_events.cost_provenance IS
  'provider_reported (actual_cents from the provider) | computed_from_provider_tokens (priced_actual_cents) | reservation_estimate (upper-bound reservation kept when cost is unknown).';
