-- Run against a disposable database or inside a transaction.
-- These assertions verify metadata-level isolation without creating auth users.

begin;

do $$
declare
  unprotected_count integer;
  anon_grant_count integer;
  cross_schema_fk_count integer;
begin
  select count(*) into unprotected_count
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'creator_studio'
    and c.relkind = 'r'
    and (not c.relrowsecurity or not c.relforcerowsecurity);

  if unprotected_count <> 0 then
    raise exception 'Creator Studio contains tables without enabled and forced RLS';
  end if;

  select count(*) into anon_grant_count
  from information_schema.role_table_grants
  where table_schema = 'creator_studio'
    and grantee in ('anon', 'PUBLIC');

  if anon_grant_count <> 0 then
    raise exception 'Anonymous or PUBLIC grants exist in creator_studio';
  end if;

  select count(*) into cross_schema_fk_count
  from pg_constraint con
  join pg_class src on src.oid = con.conrelid
  join pg_namespace src_ns on src_ns.oid = src.relnamespace
  join pg_class dst on dst.oid = con.confrelid
  join pg_namespace dst_ns on dst_ns.oid = dst.relnamespace
  where con.contype = 'f'
    and src_ns.nspname = 'creator_studio'
    and dst_ns.nspname not in ('creator_studio', 'auth');

  if cross_schema_fk_count <> 0 then
    raise exception 'Creator Studio contains an unapproved cross-app foreign key';
  end if;
end
$$;

rollback;
