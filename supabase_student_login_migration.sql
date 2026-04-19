-- Run once in the Supabase SQL Editor.
-- Adds student login fields. Admins can reset passwords, but old passwords are not displayed.

alter table public.students
add column if not exists login_account text;

-- Legacy plaintext password column. Existing plaintext passwords are migrated to
-- login_password_hash after a successful student login.
alter table public.students
add column if not exists login_password text;

alter table public.students
add column if not exists login_password_hash text;

create unique index if not exists students_login_account_key
on public.students (login_account)
where login_account is not null and login_account <> '';
