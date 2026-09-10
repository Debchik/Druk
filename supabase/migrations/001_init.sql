create extension if not exists pgcrypto;

create type public.task_status as enum ('planned','in_progress','done');
create type public.program_status as enum ('considering','preparing','submitted','next_stage','accepted','rejected');
create type public.file_scope as enum ('project','program');

create table public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 200),
  created_at timestamptz not null default now()
);

create table public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete restrict,
  display_name text not null check (char_length(display_name) between 1 and 120),
  created_at timestamptz not null default now(),
  primary key (workspace_id,user_id)
);
create index workspace_members_user_idx on public.workspace_members(user_id);

create or replace function public.is_workspace_member(p_workspace_id uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists(select 1 from public.workspace_members wm where wm.workspace_id=p_workspace_id and wm.user_id=auth.uid());
$$;
revoke all on function public.is_workspace_member(uuid) from public;
grant execute on function public.is_workspace_member(uuid) to authenticated;

create or replace function public.is_workspace_member_text(p_workspace_id text)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists(select 1 from public.workspace_members wm where wm.workspace_id::text=p_workspace_id and wm.user_id=auth.uid());
$$;
revoke all on function public.is_workspace_member_text(text) from public;
grant execute on function public.is_workspace_member_text(text) to authenticated;

create or replace function public.set_updated_at()
returns trigger language plpgsql set search_path = '' as $$ begin new.updated_at=now(); return new; end $$;

create table public.project_settings (
  workspace_id uuid primary key references public.workspaces(id) on delete cascade,
  project_name text not null default 'Друк' check(char_length(project_name) between 1 and 200),
  description text, stage text, next_result text, landing_url text, telegram_url text,
  presentation_file_id uuid,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

create table public.weekly_focus_items (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  week_start date not null, text text not null check(char_length(text) between 1 and 500),
  assignee_id uuid references auth.users(id) on delete set null, done boolean not null default false,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(id,workspace_id), foreign key(workspace_id,assignee_id) references public.workspace_members(workspace_id,user_id)
);
create index weekly_focus_workspace_week_idx on public.weekly_focus_items(workspace_id,week_start desc);

create table public.meetings (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null default 'Встреча', meeting_date date not null, notes text not null default '',
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id)
);

create table public.tasks (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null check(char_length(title) between 1 and 240), description text,
  assignee_id uuid references auth.users(id) on delete set null, status public.task_status not null default 'planned',
  due_date date, planned_week date, blocked boolean not null default false, block_reason text, meeting_id uuid,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id),
  foreign key(workspace_id,assignee_id) references public.workspace_members(workspace_id,user_id),
  foreign key(meeting_id,workspace_id) references public.meetings(id,workspace_id)
);
create index tasks_workspace_active_idx on public.tasks(workspace_id,status,due_date);
create index tasks_workspace_week_idx on public.tasks(workspace_id,planned_week);

create table public.programs (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null check(char_length(name) between 1 and 240), url text, deadline date,
  status public.program_status not null default 'considering', next_step text, notes text, archived boolean not null default false,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id)
);
create index programs_workspace_deadline_idx on public.programs(workspace_id,archived,deadline);

create table public.program_checklist_items (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null, program_id uuid not null,
  text text not null check(char_length(text) between 1 and 500), done boolean not null default false,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id),
  foreign key(program_id,workspace_id) references public.programs(id,workspace_id) on delete cascade
);

create table public.answer_library (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  question text not null check(char_length(question) between 1 and 1000), answer text not null default '', keywords text not null default '',
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id)
);
create index answer_library_workspace_updated_idx on public.answer_library(workspace_id,updated_at desc);

create table public.program_answers (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null, program_id uuid not null,
  question text not null check(char_length(question) between 1 and 1000), answer text not null default '', source_answer_id uuid,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id),
  foreign key(program_id,workspace_id) references public.programs(id,workspace_id) on delete cascade,
  foreign key(source_answer_id,workspace_id) references public.answer_library(id,workspace_id)
);

create table public.files (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  scope public.file_scope not null, program_id uuid, display_name text not null check(char_length(display_name) between 1 and 300),
  original_name text not null check(char_length(original_name) between 1 and 300), storage_path text not null unique,
  mime_type text not null, size_bytes bigint not null check(size_bytes > 0), created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id),
  foreign key(program_id,workspace_id) references public.programs(id,workspace_id) on delete restrict,
  check((scope='project' and program_id is null) or (scope='program' and program_id is not null))
);
create index files_workspace_scope_idx on public.files(workspace_id,scope,created_at desc);

alter table public.project_settings add constraint project_settings_presentation_fk
  foreign key(presentation_file_id,workspace_id) references public.files(id,workspace_id);

create table public.program_file_links (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null, program_id uuid not null, file_id uuid not null,
  created_by uuid references auth.users(id) on delete set null, created_at timestamptz not null default now(),
  unique(program_id,file_id), unique(id,workspace_id),
  foreign key(program_id,workspace_id) references public.programs(id,workspace_id) on delete cascade,
  foreign key(file_id,workspace_id) references public.files(id,workspace_id) on delete cascade
);

create table public.program_submissions (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null, program_id uuid not null, snapshot jsonb not null,
  created_by uuid references auth.users(id) on delete set null, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(id,workspace_id), foreign key(program_id,workspace_id) references public.programs(id,workspace_id) on delete restrict
);

create table public.decisions (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null check(char_length(title) between 1 and 240), text text not null, decision_date date not null default current_date,
  meeting_id uuid, archived boolean not null default false, created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(id,workspace_id),
  foreign key(meeting_id,workspace_id) references public.meetings(id,workspace_id)
);

create table public.github_repositories (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null references public.workspaces(id) on delete cascade,
  full_name text not null check(full_name ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
  last_synced_at timestamptz, last_sync_error text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(workspace_id,full_name), unique(id,workspace_id)
);

create table public.github_issues (
  id uuid primary key default gen_random_uuid(), workspace_id uuid not null, repository_id uuid not null,
  github_id bigint not null unique, number integer not null, title text not null, state text not null check(state in ('open','closed')),
  url text not null, assignee text, labels jsonb not null default '[]'::jsonb, github_updated_at timestamptz,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(repository_id,number), unique(id,workspace_id),
  foreign key(repository_id,workspace_id) references public.github_repositories(id,workspace_id) on delete cascade
);
create index github_issues_workspace_state_idx on public.github_issues(workspace_id,state,github_updated_at desc);

create or replace function public.search_answers(p_workspace_id uuid,p_query text)
returns setof public.answer_library language sql stable security invoker set search_path='' as $$
  with tokens as (
    select token from regexp_split_to_table(lower(trim(coalesce(p_query,''))), E'\\s+') token where token<>''
  )
  select a.* from public.answer_library a
  where a.workspace_id=p_workspace_id and public.is_workspace_member(a.workspace_id)
    and not exists(select 1 from tokens t where position(t.token in lower(concat_ws(' ',a.question,a.answer,a.keywords)))=0)
  order by case when lower(a.question) like '%'||lower(trim(coalesce(p_query,'')))||'%' then 0 else 1 end,a.updated_at desc;
$$;
grant execute on function public.search_answers(uuid,text) to authenticated;

do $$ declare t text; begin
  foreach t in array array['project_settings','weekly_focus_items','meetings','tasks','programs','program_checklist_items','answer_library','program_answers','files','program_submissions','decisions','github_repositories','github_issues'] loop
    execute format('create trigger %I_updated_at before update on public.%I for each row execute function public.set_updated_at()',t,t);
  end loop;
end $$;

alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
create policy workspaces_select on public.workspaces for select to authenticated using(public.is_workspace_member(id));
create policy members_select on public.workspace_members for select to authenticated using(public.is_workspace_member(workspace_id));
grant select on public.workspaces,public.workspace_members to authenticated;

do $$ declare t text; begin
  foreach t in array array['project_settings','weekly_focus_items','meetings','tasks','programs','program_checklist_items','answer_library','program_answers','files','program_file_links','program_submissions','decisions','github_repositories','github_issues'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('create policy %I_select on public.%I for select to authenticated using(public.is_workspace_member(workspace_id))',t,t);
    execute format('create policy %I_insert on public.%I for insert to authenticated with check(public.is_workspace_member(workspace_id))',t,t);
    execute format('create policy %I_update on public.%I for update to authenticated using(public.is_workspace_member(workspace_id)) with check(public.is_workspace_member(workspace_id))',t,t);
    execute format('create policy %I_delete on public.%I for delete to authenticated using(public.is_workspace_member(workspace_id))',t,t);
    execute format('grant select,insert,update,delete on public.%I to authenticated',t);
  end loop;
end $$;

insert into storage.buckets(id,name,public,file_size_limit)
values('workspace-files','workspace-files',false,20971520)
on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit;

create policy workspace_files_select on storage.objects for select to authenticated using(
  bucket_id='workspace-files' and public.is_workspace_member_text((storage.foldername(name))[1])
);
create policy workspace_files_insert on storage.objects for insert to authenticated with check(
  bucket_id='workspace-files' and public.is_workspace_member_text((storage.foldername(name))[1])
);
create policy workspace_files_delete on storage.objects for delete to authenticated using(
  bucket_id='workspace-files' and public.is_workspace_member_text((storage.foldername(name))[1])
);
