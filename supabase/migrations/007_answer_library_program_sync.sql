-- Keep answer_library as the central knowledge base for every answer written inside a program.
-- Each program_answers row gets its own mirrored answer_library row, even when it was
-- originally copied from another library answer. This preserves program-specific variants.

alter table public.answer_library
  add column if not exists source_program_answer_id uuid references public.program_answers(id) on delete set null,
  add column if not exists source_program_id uuid references public.programs(id) on delete set null;

create unique index if not exists answer_library_source_program_answer_uidx
  on public.answer_library(source_program_answer_id)
  where source_program_answer_id is not null;

create index if not exists answer_library_source_program_idx
  on public.answer_library(workspace_id, source_program_id);

create or replace function public.sync_program_answer_to_library()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_library_id uuid;
  v_program_name text;
begin
  select p.name into v_program_name
  from public.programs p
  where p.id = new.program_id;

  select a.id into v_library_id
  from public.answer_library a
  where a.source_program_answer_id = new.id
  limit 1;

  if v_library_id is null then
    insert into public.answer_library (
      workspace_id,
      question,
      answer,
      keywords,
      created_by,
      source_program_answer_id,
      source_program_id
    ) values (
      new.workspace_id,
      new.question,
      new.answer,
      concat('Программа, ', coalesce(v_program_name, 'Без названия')),
      new.created_by,
      new.id,
      new.program_id
    );
  else
    update public.answer_library
    set question = new.question,
        answer = new.answer,
        keywords = concat('Программа, ', coalesce(v_program_name, 'Без названия')),
        source_program_id = new.program_id,
        updated_at = now()
    where id = v_library_id;
  end if;

  return new;
end;
$$;

revoke all on function public.sync_program_answer_to_library() from public;

-- Backfill every answer that already exists in a program.
insert into public.answer_library (
  workspace_id,
  question,
  answer,
  keywords,
  created_by,
  source_program_answer_id,
  source_program_id
)
select
  pa.workspace_id,
  pa.question,
  pa.answer,
  concat('Программа, ', coalesce(p.name, 'Без названия')),
  pa.created_by,
  pa.id,
  pa.program_id
from public.program_answers pa
left join public.programs p on p.id = pa.program_id
where not exists (
  select 1
  from public.answer_library a
  where a.source_program_answer_id = pa.id
);

drop trigger if exists program_answers_sync_library on public.program_answers;
create trigger program_answers_sync_library
after insert or update of question, answer, program_id
on public.program_answers
for each row
execute function public.sync_program_answer_to_library();
