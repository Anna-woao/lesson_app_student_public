-- Run once in the Supabase SQL Editor.
-- Persists admin Excel import templates in Supabase instead of local disk.

create table if not exists public.vocab_import_templates (
    name text primary key,
    mapping jsonb not null default '{}'::jsonb,
    sheet_name text,
    data_start_row integer not null default 1,
    updated_at timestamptz not null default timezone('utc', now())
);

create or replace function public.touch_vocab_import_templates_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists trg_vocab_import_templates_updated_at on public.vocab_import_templates;

create trigger trg_vocab_import_templates_updated_at
before update on public.vocab_import_templates
for each row
execute function public.touch_vocab_import_templates_updated_at();
