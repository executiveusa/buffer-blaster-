from pathlib import Path


def test_supabase_migration_prefixes_are_unique_and_buffer_blaster_schema_precedes_indexes():
    migrations = sorted(Path("supabase/migrations").glob("*.sql"))
    prefixes = [path.name.split("_", 1)[0] for path in migrations]
    assert len(prefixes) == len(set(prefixes)), f"duplicate migration prefixes: {prefixes}"

    names = [path.name for path in migrations]
    schema_files = [name for name in names if "buffer_blaster_schema" in name]
    index_files = [name for name in names if "buffer_blaster_beta_scale" in name]
    assert schema_files, "missing canonical buffer_blaster schema migration"
    assert index_files, "missing buffer_blaster beta scale migration"
    assert names.index(schema_files[0]) < names.index(index_files[0])
