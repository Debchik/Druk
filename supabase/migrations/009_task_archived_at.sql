alter table public.tasks
  add column if not exists archived_at timestamptz;

update public.tasks
set archived_at = coalesce(archived_at, updated_at, created_at, now())
where archived = true and archived_at is null;

create or replace function public.set_task_archived_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  if new.archived = true and (tg_op = 'INSERT' or old.archived = false) then
    new.archived_at = coalesce(new.archived_at, now());
  elsif new.archived = false then
    new.archived_at = null;
  end if;
  return new;
end;
$$;

drop trigger if exists tasks_set_archived_at on public.tasks;
create trigger tasks_set_archived_at
before insert or update of archived on public.tasks
for each row execute function public.set_task_archived_at();

create index if not exists tasks_workspace_archived_at_idx
  on public.tasks(workspace_id, archived, archived_at desc);
