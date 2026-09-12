alter table public.workspace_members
  add column role text not null default 'member' check (role in ('cofounder','manager','member','guest'));

update public.workspace_members set role='cofounder' where role='member';

alter table public.meetings
  add column start_time time,
  add column end_time time,
  add column event_type text not null default 'meeting' check (event_type in ('meeting','interview','demo','pitch','webinar','consultation','deadline','external')),
  add column mode text not null default 'online' check (mode in ('online','offline')),
  add column location text,
  add column program_id uuid,
  add column participants uuid[] not null default '{}';

alter table public.meetings
  add constraint meetings_program_fk
  foreign key(program_id) references public.programs(id) on delete set null;

create index meetings_workspace_date_idx on public.meetings(workspace_id,meeting_date,start_time);

create table public.project_links (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null check(char_length(title) between 1 and 120),
  url text not null check(char_length(url) between 4 and 2000),
  kind text not null default 'other' check(kind in ('landing','telegram','presentation','other')),
  position integer not null default 0,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(workspace_id,kind),
  unique(id,workspace_id)
);

create trigger project_links_updated_at before update on public.project_links
for each row execute function public.set_updated_at();

create table public.workspace_invites (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  email text not null,
  display_name text not null default 'Участник',
  role text not null default 'member' check(role in ('cofounder','manager','member','guest')),
  status text not null default 'pending' check(status in ('pending','accepted','cancelled')),
  invited_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  accepted_at timestamptz,
  unique(workspace_id,email),
  unique(id,workspace_id)
);
create index workspace_invites_workspace_status_idx on public.workspace_invites(workspace_id,status,created_at desc);

create table public.product_metrics_daily (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  metric_date date not null default current_date,
  users_total bigint not null default 0 check(users_total >= 0),
  messages_total bigint not null default 0 check(messages_total >= 0),
  dialogs_total bigint not null default 0 check(dialogs_total >= 0),
  weekly_active bigint not null default 0 check(weekly_active >= 0),
  avg_session_seconds integer not null default 0 check(avg_session_seconds >= 0),
  retention_7d numeric(6,2) not null default 0 check(retention_7d between 0 and 100),
  registration_conversion numeric(6,2) not null default 0 check(registration_conversion between 0 and 100),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(workspace_id,metric_date),
  unique(id,workspace_id)
);
create index product_metrics_workspace_date_idx on public.product_metrics_daily(workspace_id,metric_date desc);
create trigger product_metrics_daily_updated_at before update on public.product_metrics_daily
for each row execute function public.set_updated_at();

create table public.client_feedback (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  quote text not null check(char_length(quote) between 1 and 2000),
  author_name text not null check(char_length(author_name) between 1 and 120),
  author_role text,
  sentiment text not null default 'positive' check(sentiment in ('positive','constructive','neutral')),
  tags text[] not null default '{}',
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id,workspace_id)
);
create index client_feedback_workspace_created_idx on public.client_feedback(workspace_id,created_at desc);
create trigger client_feedback_updated_at before update on public.client_feedback
for each row execute function public.set_updated_at();

alter table public.project_links enable row level security;
alter table public.workspace_invites enable row level security;
alter table public.product_metrics_daily enable row level security;
alter table public.client_feedback enable row level security;

do $$ declare t text; begin
  foreach t in array array['project_links','workspace_invites','product_metrics_daily','client_feedback'] loop
    execute format('create policy %I_select on public.%I for select to authenticated using(public.is_workspace_member(workspace_id))',t,t);
    execute format('create policy %I_insert on public.%I for insert to authenticated with check(public.is_workspace_member(workspace_id))',t,t);
    execute format('create policy %I_update on public.%I for update to authenticated using(public.is_workspace_member(workspace_id)) with check(public.is_workspace_member(workspace_id))',t,t);
    execute format('create policy %I_delete on public.%I for delete to authenticated using(public.is_workspace_member(workspace_id))',t,t);
    execute format('grant select,insert,update,delete on public.%I to authenticated',t);
  end loop;
end $$;

create policy members_update on public.workspace_members for update to authenticated using(public.is_workspace_member(workspace_id)) with check(public.is_workspace_member(workspace_id));
grant select,update on public.workspace_members to authenticated;

create or replace function public.add_workspace_member_by_email(
  p_workspace_id uuid,
  p_email text,
  p_display_name text,
  p_role text default 'member'
) returns jsonb
language plpgsql
security definer
set search_path=''
as $$
declare
  target_user uuid;
  invite_id uuid;
begin
  if not exists(
    select 1 from public.workspace_members wm
    where wm.workspace_id=p_workspace_id and wm.user_id=auth.uid()
  ) then
    raise exception 'not a workspace member';
  end if;

  if p_role not in ('cofounder','manager','member','guest') then
    raise exception 'invalid role';
  end if;

  select u.id into target_user
  from auth.users u
  where lower(u.email)=lower(trim(p_email))
  limit 1;

  if target_user is not null then
    insert into public.workspace_members(workspace_id,user_id,display_name,role)
    values(p_workspace_id,target_user,coalesce(nullif(trim(p_display_name),''),'Участник'),p_role)
    on conflict(workspace_id,user_id) do update
      set display_name=excluded.display_name, role=excluded.role;

    update public.workspace_invites
       set status='accepted', accepted_at=now()
     where workspace_id=p_workspace_id and lower(email)=lower(trim(p_email));

    return jsonb_build_object('status','accepted','user_id',target_user);
  end if;

  insert into public.workspace_invites(workspace_id,email,display_name,role,invited_by)
  values(p_workspace_id,lower(trim(p_email)),coalesce(nullif(trim(p_display_name),''),'Участник'),p_role,auth.uid())
  on conflict(workspace_id,email) do update
    set display_name=excluded.display_name, role=excluded.role, status='pending', invited_by=auth.uid()
  returning id into invite_id;

  return jsonb_build_object('status','pending','invite_id',invite_id);
end $$;

revoke all on function public.add_workspace_member_by_email(uuid,text,text,text) from public, anon;
grant execute on function public.add_workspace_member_by_email(uuid,text,text,text) to authenticated;

insert into public.project_links(workspace_id,title,url,kind,position,created_by)
select ps.workspace_id,'Лендинг Друка',ps.landing_url,'landing',10,ps.created_by
from public.project_settings ps
where nullif(trim(ps.landing_url),'') is not null
on conflict(workspace_id,kind) do nothing;

insert into public.project_links(workspace_id,title,url,kind,position,created_by)
select ps.workspace_id,'Друк в Telegram',ps.telegram_url,'telegram',20,ps.created_by
from public.project_settings ps
where nullif(trim(ps.telegram_url),'') is not null
on conflict(workspace_id,kind) do nothing;
