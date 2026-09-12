create table if not exists public.entity_comments (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  entity_type text not null check (entity_type in ('answer','program_answer','file')),
  entity_id uuid not null,
  body text not null check (char_length(body) between 1 and 10000),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (id, workspace_id)
);

create index if not exists entity_comments_target_idx
  on public.entity_comments(workspace_id, entity_type, entity_id, created_at asc);

alter table public.entity_comments enable row level security;

drop policy if exists entity_comments_select on public.entity_comments;
drop policy if exists entity_comments_insert on public.entity_comments;
drop policy if exists entity_comments_update on public.entity_comments;
drop policy if exists entity_comments_delete on public.entity_comments;

create policy entity_comments_select on public.entity_comments
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy entity_comments_insert on public.entity_comments
  for insert to authenticated
  with check (public.is_workspace_member(workspace_id) and created_by = auth.uid());

create policy entity_comments_update on public.entity_comments
  for update to authenticated
  using (public.is_workspace_member(workspace_id) and created_by = auth.uid())
  with check (public.is_workspace_member(workspace_id) and created_by = auth.uid());

create policy entity_comments_delete on public.entity_comments
  for delete to authenticated
  using (public.is_workspace_member(workspace_id) and created_by = auth.uid());

grant select, insert, update, delete on public.entity_comments to authenticated;

drop trigger if exists entity_comments_updated_at on public.entity_comments;
create trigger entity_comments_updated_at
  before update on public.entity_comments
  for each row execute function public.set_updated_at();
