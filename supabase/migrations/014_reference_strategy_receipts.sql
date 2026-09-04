-- 014_reference_strategy_receipts.sql
-- Additive support for replay-safe reference-ad strategy aggregates.

ALTER TABLE buffer_blaster.strategy_receipts
  ADD COLUMN IF NOT EXISTS idempotency_key text;

ALTER TABLE buffer_blaster.strategy_receipts
  ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
  ALTER TABLE buffer_blaster.strategy_receipts
    ADD CONSTRAINT strategy_receipts_idempotency_length_check
    CHECK (idempotency_key IS NULL OR char_length(idempotency_key) BETWEEN 8 AND 128);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER TABLE buffer_blaster.strategy_receipts
    ADD CONSTRAINT strategy_receipts_metadata_object_check
    CHECK (jsonb_typeof(metadata) = 'object');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS strategy_receipts_workspace_idempotency_uq
  ON buffer_blaster.strategy_receipts (workspace_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;
