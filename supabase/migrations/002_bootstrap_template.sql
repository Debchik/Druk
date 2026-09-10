-- Optional manual bootstrap template. Prefer scripts/bootstrap_workspace.py or the GitHub Actions workflow.
-- Replace placeholders only in a private SQL editor; do not commit real user UUIDs.
with w as (
  insert into public.workspaces(name) values ('Друк') returning id
), members as (
  insert into public.workspace_members(workspace_id,user_id,display_name)
  select id,'00000000-0000-0000-0000-000000000001'::uuid,'Сооснователь 1' from w
  union all
  select id,'00000000-0000-0000-0000-000000000002'::uuid,'Сооснователь 2' from w
  returning workspace_id
)
insert into public.project_settings(workspace_id,project_name,created_by)
select workspace_id,'Друк','00000000-0000-0000-0000-000000000001'::uuid from members limit 1;
