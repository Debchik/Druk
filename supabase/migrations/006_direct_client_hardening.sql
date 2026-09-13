create or replace function public.can_delete_workspace_object(p_name text)
returns boolean
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_workspace uuid;
  v_file_id uuid;
  v_second_segment text;
begin
  v_workspace := split_part(p_name, '/', 1)::uuid;
  v_second_segment := split_part(p_name, '/', 2);

  if not exists (
    select 1
    from public.workspace_members wm
    where wm.workspace_id = v_workspace
      and wm.user_id = auth.uid()
  ) then
    return false;
  end if;

  -- Bug-report screenshots are not represented by rows in public.files.
  if v_second_segment = 'bug-reports' then
    return true;
  end if;

  v_file_id := regexp_replace(p_name, '^.*/', '')::uuid;

  return not exists (
    select 1
    from public.program_submissions ps
    where ps.workspace_id = v_workspace
      and ps.snapshot::text like '%' || v_file_id::text || '%'
  );
exception
  when others then
    return false;
end;
$$;

revoke all on function public.can_delete_workspace_object(text) from public, anon;
grant execute on function public.can_delete_workspace_object(text) to authenticated;

drop policy if exists workspace_files_delete on storage.objects;
create policy workspace_files_delete on storage.objects
for delete to authenticated
using (
  bucket_id = 'workspace-files'
  and public.can_delete_workspace_object(name)
);
