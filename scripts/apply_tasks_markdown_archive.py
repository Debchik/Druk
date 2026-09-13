from pathlib import Path


def rep(path, old, new, n=1):
    p=Path(path);s=p.read_text()
    if old not in s: raise SystemExit(f'missing pattern in {path}: {old[:120]!r}')
    p.write_text(s.replace(old,new,n))

# App imports + types
rep('frontend/src/App.tsx',"import { weekStart } from './lib/date'", "import { weekStart } from './lib/date'\nimport Markdown from './Markdown'")
rep('frontend/src/App.tsx',"type Task={id:string;title:string;description?:string|null;assignee_id?:string|null;status:'planned'|'in_progress'|'done';due_date?:string|null;planned_week?:string|null;blocked:boolean;block_reason?:string|null;updated_at:string}","type Task={id:string;title:string;description?:string|null;assignee_id?:string|null;status:'planned'|'in_progress'|'done';due_date?:string|null;planned_week?:string|null;blocked:boolean;block_reason?:string|null;archived?:boolean;updated_at:string}")

# Tasks default done visible + archive view
rep('frontend/src/App.tsx',"const qc=useQueryClient();const [mine,setMine]=useState(false),[showDone,setShowDone]=useState(false),[view,setView]=useState<'list'|'board'>('list'),[title,setTitle]=useState(''),[description,setDescription]=useState(''),[assignee,setAssignee]=useState(''),[due,setDue]=useState(''),[selected,setSelected]=useState<Task|null>(null)","const qc=useQueryClient();const [mine,setMine]=useState(false),[showDone,setShowDone]=useState(true),[archiveView,setArchiveView]=useState(false),[view,setView]=useState<'list'|'board'>('list'),[title,setTitle]=useState(''),[description,setDescription]=useState(''),[assignee,setAssignee]=useState(''),[due,setDue]=useState(''),[selected,setSelected]=useState<Task|null>(null)")
rep('frontend/src/App.tsx',"const q=useQuery<any>({queryKey:['tasks-rich',mine,showDone],queryFn:async()=>{const [tasks,members]=await Promise.all([api(`/tasks?mine=${mine}&include_done=${showDone}`),api('/team')]);return {tasks,members}}})", "const q=useQuery<any>({queryKey:['tasks-rich',mine,showDone,archiveView],queryFn:async()=>{const [tasks,members]=await Promise.all([api(`/tasks?mine=${mine}&include_done=${archiveView?true:showDone}&archived=${archiveView}`),api('/team')]);return {tasks,members}}})")
rep('frontend/src/App.tsx',"<button onClick={()=>setShowDone(!showDone)}>{showDone?'Скрыть готовые':'Показывать готовые'}</button><span/>","<button className={showDone&&!archiveView?'active':''} onClick={()=>setShowDone(!showDone)} disabled={archiveView}>{showDone?'✓ Готовые показаны':'Показать готовые'}</button><button className={archiveView?'active':''} onClick={()=>{setArchiveView(!archiveView);setSelected(null)}}>▣ {archiveView?'Вернуться к задачам':'Архив'}</button><span/>")
rep('frontend/src/App.tsx',"{selected&&<TaskModal key={selected.id} task={selected} members={members} saving={patch.isPending} onClose={()=>setSelected(null)} onSave={data=>patch.mutate({id:selected.id,data})} onDelete={()=>{if(confirm('Удалить задачу?'))remove.mutate(selected.id)}}/>}","{selected&&<TaskModal key={selected.id} task={selected} members={members} saving={patch.isPending} onClose={()=>setSelected(null)} onSave={data=>patch.mutate({id:selected.id,data})} onArchive={()=>patch.mutate({id:selected.id,data:{archived:!selected.archived}},{onSuccess:()=>setSelected(null)})} onDelete={()=>{if(confirm('Удалить задачу без возможности восстановления?'))remove.mutate(selected.id)}}/>}")

old="function TaskModal({task,members,saving,onClose,onSave,onDelete}:{task:Task;members:Member[];saving:boolean;onClose:()=>void;onSave:(data:any)=>void;onDelete:()=>void})"
new="function TaskModal({task,members,saving,onClose,onSave,onArchive,onDelete}:{task:Task;members:Member[];saving:boolean;onClose:()=>void;onSave:(data:any)=>void;onArchive:()=>void;onDelete:()=>void})"
rep('frontend/src/App.tsx',old,new)
rep('frontend/src/App.tsx',"<footer><Button type=\"button\" kind=\"danger\" onClick={onDelete}>Удалить</Button><span/><Button type=\"button\" kind=\"secondary\" onClick={onClose}>Закрыть</Button><Button disabled={!form.title.trim()||saving}>{saving?'Сохраняем…':'Сохранить изменения'}</Button></footer>","<footer><Button type=\"button\" kind=\"secondary\" onClick={onArchive}>{task.archived?'↩ Вернуть из архива':'▣ Архивировать'}</Button><Button type=\"button\" kind=\"danger\" onClick={onDelete}>Удалить</Button><span/><Button type=\"button\" kind=\"secondary\" onClick={onClose}>Закрыть</Button><Button disabled={!form.title.trim()||saving}>{saving?'Сохраняем…':'Сохранить изменения'}</Button></footer>")

# Markdown rendering in program answers, answer library and materials
rep('frontend/src/App.tsx',"<p>{a.answer||'Ответ пока пуст.'}</p>","<Markdown text={a.answer}/>")
rep('frontend/src/App.tsx',"<div className=\"answer-body\">{answer.answer}</div>","<div className=\"answer-body\"><Markdown text={answer.answer}/></div>")
rep('frontend/src/App.tsx',"<p>{a.answer||'Ответ пока пуст.'}</p><footer><button onClick={()=>void navigator.clipboard.writeText(a.answer)}>","<Markdown text={a.answer} compact/><footer><button onClick={()=>void navigator.clipboard.writeText(a.answer)}>")
rep('frontend/src/App.tsx',"{editing?<textarea className=\"answer-editor\" rows={13} value={draft.answer} onChange={e=>setDraft({...draft,answer:e.target.value})}/>:<div className=\"answer-body\"><Markdown text={answer.answer}/></div>}","{editing?<div className=\"markdown-editor-split\"><textarea className=\"answer-editor\" rows={13} value={draft.answer} onChange={e=>setDraft({...draft,answer:e.target.value})}/><div className=\"markdown-preview\"><small>Предпросмотр Markdown</small><Markdown text={draft.answer}/></div></div>:<div className=\"answer-body\"><Markdown text={answer.answer}/></div>}")

# Direct Supabase queries: hide archived except archive mode and dashboard
rep('frontend/src/lib/api.ts',"table('tasks').select('*').eq('workspace_id',ws).neq('status','done').order", "table('tasks').select('*').eq('workspace_id',ws).eq('archived',false).neq('status','done').order")
old="const mine=url.searchParams.get('mine')==='true',include=url.searchParams.get('include_done')==='true',status=url.searchParams.get('status'),assignee=url.searchParams.get('assignee_id'),week=url.searchParams.get('week_start');if(mine)q=q.eq('assignee_id',c.id);else if(assignee)q=q.eq('assignee_id',assignee);if(status)q=q.eq('status',status);else if(!include)q=q.neq('status','done');if(week)q=q.eq('planned_week',week);return dataOf(await q.order"
new="const mine=url.searchParams.get('mine')==='true',include=url.searchParams.get('include_done')==='true',archived=url.searchParams.get('archived')==='true',status=url.searchParams.get('status'),assignee=url.searchParams.get('assignee_id'),week=url.searchParams.get('week_start');q=q.eq('archived',archived);if(mine)q=q.eq('assignee_id',c.id);else if(assignee)q=q.eq('assignee_id',assignee);if(status)q=q.eq('status',status);else if(!include)q=q.neq('status','done');if(week)q=q.eq('planned_week',week);return dataOf(await q.order"
rep('frontend/src/lib/api.ts',old,new)

# FastAPI parity for later self-hosting
rep('backend/app/schemas.py',"    block_reason: str | None = Field(default=None, max_length=500)\n\n\nclass TaskPatch", "    block_reason: str | None = Field(default=None, max_length=500)\n    archived: bool = False\n\n\nclass TaskPatch")
rep('backend/app/schemas.py',"    block_reason: str | None = Field(default=None, max_length=500)\n    expected_updated_at", "    block_reason: str | None = Field(default=None, max_length=500)\n    archived: bool | None = None\n    expected_updated_at")
rep('backend/app/core.py',"db.select(\"tasks\", filters={\"workspace_id\": user.workspace_id, \"status\": \"neq.done\"}", "db.select(\"tasks\", filters={\"workspace_id\": user.workspace_id, \"archived\": \"eq.false\", \"status\": \"neq.done\"}")
rep('backend/app/core.py',"async def list_tasks(mine: bool = False, assignee_id: str | None = None, status: str | None = None, week_start: date | None = None, include_done: bool = False, user: CurrentUser = Depends(current_user)):\n    filters: dict = {\"workspace_id\": user.workspace_id}", "async def list_tasks(mine: bool = False, assignee_id: str | None = None, status: str | None = None, week_start: date | None = None, include_done: bool = False, archived: bool = False, user: CurrentUser = Depends(current_user)):\n    filters: dict = {\"workspace_id\": user.workspace_id, \"archived\": \"eq.true\" if archived else \"eq.false\"}")

# Prefetch the actual default tasks view
rep('frontend/src/lib/prefetch.ts',"['tasks-rich', false, false]", "['tasks-rich', false, true, false]")
rep('frontend/src/lib/prefetch.ts',"api('/tasks?mine=false&include_done=false')", "api('/tasks?mine=false&include_done=true&archived=false')")

# CSS imports + cache version
rep('frontend/src/main.tsx',"import './stability.css'", "import './stability.css'\nimport './markdown.css'")
rep('frontend/src/main.tsx',"const CACHE_PREFIX='druk-query-cache:v4:'", "const CACHE_PREFIX='druk-query-cache:v6:'")

# Append task scrolling / markdown editor styling
p=Path('frontend/src/stability.css')
s=p.read_text()
extra='''\n/* tasks-archive-markdown-v1 */\n.task-list-card .task-table{max-height:620px;overflow:auto;scrollbar-gutter:stable;border-radius:8px}\n.task-list-card .task-row.table-head{position:sticky;top:0;z-index:4;background:var(--panel-bg,#fff)}\n.board-col{max-height:680px;overflow-y:auto;scrollbar-gutter:stable}\n.board-col>h3{position:sticky;top:0;z-index:3;background:inherit;padding-bottom:7px}\n.toolbar button:disabled{opacity:.45;cursor:not-allowed}\n.markdown-editor-split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;align-items:start}\n.markdown-preview{min-height:250px;max-height:430px;overflow:auto;border:1px solid #dde4da;border-radius:9px;padding:10px;background:var(--panel-bg,#fff)}\n.markdown-preview>small{display:block;color:#89918b;margin-bottom:8px;font-size:9px;text-transform:uppercase;letter-spacing:.04em}\n.program-answers .markdown-body{margin:7px 0 8px}\n.program-material-card>.markdown-body{display:-webkit-box;-webkit-line-clamp:7;-webkit-box-orient:vertical;overflow:hidden}\n@media(max-width:900px){.markdown-editor-split{grid-template-columns:1fr}.task-list-card .task-table{max-height:70vh}}\n'''
if 'tasks-archive-markdown-v1' not in s:p.write_text(s+extra)
