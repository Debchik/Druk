alter table public.tasks
  add column if not exists archived boolean not null default false;

create index if not exists tasks_workspace_archived_idx
  on public.tasks(workspace_id, archived, status, due_date);
