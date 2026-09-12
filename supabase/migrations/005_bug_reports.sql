create table if not exists public.bug_reports (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  description text not null check (char_length(description) between 3 and 5000),
  page_url text,
  user_agent text,
  screenshot_path text,
  status text not null default 'open' check (status in ('open','in_progress','resolved')),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists bug_reports_workspace_created_idx
  on public.bug_reports(workspace_id, created_at desc);

alter table public.bug_reports enable row level security;

drop policy if exists bug_reports_select on public.bug_reports;
create policy bug_reports_select on public.bug_reports
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

drop policy if exists bug_reports_insert on public.bug_reports;
create policy bug_reports_insert on public.bug_reports
  for insert to authenticated
  with check (public.is_workspace_member(workspace_id) and created_by = auth.uid());

drop policy if exists bug_reports_update on public.bug_reports;
create policy bug_reports_update on public.bug_reports
  for update to authenticated
  using (public.is_workspace_member(workspace_id))
  with check (public.is_workspace_member(workspace_id));

grant select, insert, update on public.bug_reports to authenticated;

create trigger bug_reports_updated_at
before update on public.bug_reports
for each row execute function public.set_updated_at();
