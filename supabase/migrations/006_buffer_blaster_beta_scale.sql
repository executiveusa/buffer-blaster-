-- Buffer Blaster beta hot-path indexes.
-- Additive only. These cover FK joins used by campaign -> creative -> approval -> publish -> receipt flows.

create index if not exists bb_approvals_content_workspace_fk_idx
  on buffer_blaster.approvals (content_item_id, workspace_id);

create index if not exists bb_campaigns_client_workspace_fk_idx
  on buffer_blaster.campaigns (client_id, workspace_id);

create index if not exists bb_creative_jobs_campaign_workspace_fk_idx
  on buffer_blaster.creative_jobs (campaign_id, workspace_id);

create index if not exists bb_content_items_campaign_workspace_fk_idx
  on buffer_blaster.content_items (campaign_id, workspace_id);

create index if not exists bb_content_items_creative_job_workspace_fk_idx
  on buffer_blaster.content_items (creative_job_id, workspace_id);

create index if not exists bb_publish_jobs_content_workspace_fk_idx
  on buffer_blaster.publish_jobs (content_item_id, workspace_id);

create index if not exists bb_publish_jobs_approval_workspace_fk_idx
  on buffer_blaster.publish_jobs (approval_id, workspace_id);

create index if not exists bb_publish_jobs_channel_workspace_fk_idx
  on buffer_blaster.publish_jobs (channel_connection_id, workspace_id);

create index if not exists bb_publish_receipts_job_workspace_fk_idx
  on buffer_blaster.publish_receipts (publish_job_id, workspace_id);

create index if not exists bb_model_runs_job_workspace_fk_idx
  on buffer_blaster.model_runs (creative_job_id, workspace_id);

create index if not exists bb_performance_events_content_workspace_fk_idx
  on buffer_blaster.performance_events (content_item_id, workspace_id);

create index if not exists bb_messages_conversation_workspace_fk_idx
  on buffer_blaster.messages (conversation_id, workspace_id);

create index if not exists bb_channel_connections_client_workspace_fk_idx
  on buffer_blaster.channel_connections (client_id, workspace_id);

create index if not exists bb_source_assets_client_workspace_fk_idx
  on buffer_blaster.source_assets (client_id, workspace_id);

create index if not exists bb_ugc_characters_client_workspace_fk_idx
  on buffer_blaster.ugc_characters (client_id, workspace_id);
