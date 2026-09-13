from pathlib import Path


def replace_once(path: str, old: str, new: str):
    p=Path(path); s=p.read_text()
    if old not in s:
        raise SystemExit(f'Expected block not found in {path}: {old[:120]!r}')
    p.write_text(s.replace(old,new,1))

# 1) Keep reads that do not need a secret on the direct Supabase path.
p=Path('frontend/src/lib/api.ts'); s=p.read_text()
needle="  if(p==='/files'){\n"
insert="""  if(p==='/github/repositories'){
    if(method==='GET')return dataOf(await table('github_repositories').select('*').eq('workspace_id',ws).order('created_at',{ascending:false}))
    if(method==='POST'){
      const fullName=String(b.full_name||'').trim()
      if(!/^[A-Za-z0-9_.-]+\\/[A-Za-z0-9_.-]+$/.test(fullName))throw new ApiError(422,'INVALID_REPOSITORY','Укажите репозиторий в формате owner/name')
      return oneOf(await table('github_repositories').insert({workspace_id:ws,full_name:fullName,created_by:c.id}).select().single())
    }
  }
  if(p==='/github/issues'&&method==='GET')return dataOf(await table('github_issues').select('*').eq('workspace_id',ws).order('github_updated_at',{ascending:false}).limit(500))
  if(p==='/program-materials'&&method==='GET'){
    const [answersResult,programsResult]=await Promise.all([
      table('program_answers').select('id,program_id,question,answer,updated_at,source_answer_id').eq('workspace_id',ws).order('updated_at',{ascending:false}),
      table('programs').select('id,name').eq('workspace_id',ws),
    ])
    const names=new Map(dataOf<any[]>(programsResult).map(x=>[x.id,x.name]))
    return dataOf<any[]>(answersResult).map(x=>({...x,program_name:names.get(x.program_id)||'Программа'}))
  }

"""
if "p==='/program-materials'" not in s:
    if needle not in s: raise SystemExit('api insertion point not found')
    p.write_text(s.replace(needle,insert+needle,1))

# 2) Make GitHub optional on Tasks/Settings and surface program answers under Materials.
app=Path('frontend/src/App.tsx'); a=app.read_text()
old="type ProgramDetail={program:Program;checklist:Array<{id:string;text:string;done:boolean;created_at?:string}>;answers:Array<{id:string;question:string;answer:string;source_answer_id?:string|null;updated_at:string}>;files:Array<{id:string;file_id:string;files:FileRow}>;submissions:Array<{id:string;created_at:string;snapshot:unknown}>}"
new=old+"\ntype ProgramMaterial={id:string;program_id:string;program_name:string;question:string;answer:string;updated_at:string}"
if 'type ProgramMaterial=' not in a:
    if old not in a: raise SystemExit('ProgramDetail type block not found')
    a=a.replace(old,new,1)

old=" const q=useQuery<any>({queryKey:['tasks-rich',mine,showDone],queryFn:async()=>{const [tasks,members,issues]=await Promise.all([api(`/tasks?mine=${mine}&include_done=${showDone}`),api('/team'),api('/github/issues')]);return {tasks,members,issues}}})"
new=""" const q=useQuery<any>({queryKey:['tasks-rich',mine,showDone],queryFn:async()=>{const [tasks,members]=await Promise.all([api(`/tasks?mine=${mine}&include_done=${showDone}`),api('/team')]);return {tasks,members}}})
 const issuesQ=useQuery<GithubIssue[]>({queryKey:['github-issues'],queryFn:()=>api('/github/issues'),retry:false,staleTime:60_000})"""
if old not in a: raise SystemExit('Tasks query block not found')
a=a.replace(old,new,1)
old="if(q.isLoading)return <Loading/>;if(q.error)return <ErrorBox error={q.error}/>;const {tasks,members,issues}=q.data"
new="if(q.isLoading)return <Loading/>;if(q.error)return <ErrorBox error={q.error}/>;const {tasks,members}=q.data;const issues=issuesQ.data||[]"
if old not in a: raise SystemExit('Tasks destructuring block not found')
a=a.replace(old,new,1)

old=" const qc=useQueryClient();const q=useQuery<any>({queryKey:['settings-rich'],queryFn:async()=>{const [settings,members,links,repos,invites]=await Promise.all([api('/settings'),api('/team'),api('/links'),api('/github/repositories'),api('/invites')]);return {settings,members,links,repos,invites}}});const [form,setForm]=useState<any>(null),[invite,setInvite]=useState({email:'',display_name:'',role:'member'}),[repo,setRepo]=useState('')"
new=""" const qc=useQueryClient();const q=useQuery<any>({queryKey:['settings-rich'],queryFn:async()=>{const [settings,members,links,invites]=await Promise.all([api('/settings'),api('/team'),api('/links'),api('/invites')]);return {settings,members,links,invites}}});const repoQ=useQuery<Repo[]>({queryKey:['github-repositories'],queryFn:()=>api('/github/repositories'),retry:false,staleTime:60_000});const [form,setForm]=useState<any>(null),[invite,setInvite]=useState({email:'',display_name:'',role:'member'}),[repo,setRepo]=useState('')"""
if old not in a: raise SystemExit('Settings query block not found')
a=a.replace(old,new,1)
a=a.replace("const addRepo=useMutation({mutationFn:()=>api('/github/repositories',json('POST',{full_name:repo})),onSuccess:()=>{setRepo('');void qc.invalidateQueries({queryKey:['settings-rich']})}})","const addRepo=useMutation({mutationFn:()=>api('/github/repositories',json('POST',{full_name:repo})),onSuccess:()=>{setRepo('');void qc.invalidateQueries({queryKey:['github-repositories']})}})",1)
a=a.replace("const sync=useMutation({mutationFn:(id:string)=>api(`/github/repositories/${id}/sync`,json('POST')),onSuccess:()=>void qc.invalidateQueries({queryKey:['settings-rich']})})","const sync=useMutation({mutationFn:(id:string)=>api(`/github/repositories/${id}/sync`,json('POST')),onSuccess:()=>void qc.invalidateQueries({queryKey:['github-repositories']})})",1)
old="{q.data.repos.map((r:Repo)=>"
new="{repoQ.error&&<div className=\"github-inline-warning\">GitHub временно недоступен. Остальные настройки работают независимо.</div>}{(repoQ.data||[]).map((r:Repo)=>"
if old not in a: raise SystemExit('Settings repo rendering block not found')
a=a.replace(old,new,1)

old="const q=useQuery<any>({queryKey:['files-rich'],queryFn:async()=>{const [files,settings,programs]=await Promise.all([api('/files'),api('/settings'),api('/programs')]);return {files,settings,programs}}})"
new="const q=useQuery<any>({queryKey:['files-rich'],queryFn:async()=>{const [files,settings,programs,programMaterials]=await Promise.all([api('/files'),api('/settings'),api('/programs'),api('/program-materials')]);return {files,settings,programs,programMaterials}}})"
if old not in a: raise SystemExit('Files query block not found')
a=a.replace(old,new,1)
old="const settings:Settings=q.data.settings||{};const visible=files.filter"
new="const settings:Settings=q.data.settings||{};const materials:ProgramMaterial[]=q.data.programMaterials||[];const visibleMaterials=materials.filter(x=>(x.question+' '+x.answer+' '+x.program_name).toLowerCase().includes(search.toLowerCase()));const visible=files.filter"
if old not in a: raise SystemExit('Files data block not found')
a=a.replace(old,new,1)
old='<Card title={<>Все файлы <span className="count">{visible.length}</span></>}'
materials='''<Card title={<>Ответы из программ <span className="count">{visibleMaterials.length}</span></>} action={<Link to="/programs">Все программы →</Link>}><div className="program-materials-grid">{visibleMaterials.slice(0,12).map(a=><article className="program-material-card" key={a.id}><header><div><b>{a.question}</b><small>{a.program_name}</small></div><Chip tone="green">Ответ</Chip></header><p>{a.answer||'Ответ пока пуст.'}</p><footer><button onClick={()=>void navigator.clipboard.writeText(a.answer)}>⧉ Копировать</button><Link to={`/programs/${a.program_id}`}>Открыть программу →</Link></footer></article>)}{!visibleMaterials.length&&<Empty>Ответов из программ пока нет.</Empty>}</div></Card>'''
if old not in a: raise SystemExit('Files table insertion point not found')
a=a.replace(old,materials+old,1)
app.write_text(a)

# 3) Future self-hosted FastAPI keeps the same materials contract.
p=Path('backend/app/extended.py'); s=p.read_text()
needle='@router.get("/analytics")\n'
route='''@router.get("/program-materials")
async def program_materials(user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    answers = await db.select(
        "program_answers",
        filters={"workspace_id": user.workspace_id},
        select="id,program_id,question,answer,updated_at,source_answer_id",
        order="updated_at.desc",
    )
    programs = await db.select(
        "programs",
        filters={"workspace_id": user.workspace_id},
        select="id,name",
    )
    names = {row["id"]: row["name"] for row in programs}
    for row in answers:
        row["program_name"] = names.get(row.get("program_id"), "Программа")
    return answers


'''
if '@router.get("/program-materials")' not in s:
    if needle not in s: raise SystemExit('FastAPI insertion point not found')
    p.write_text(s.replace(needle,route+needle,1))

# 4) Prefetch must never make GitHub availability part of app navigation latency.
p=Path('frontend/src/lib/prefetch.ts'); s=p.read_text()
s=s.replace("api('/tasks?mine=false&include_done=false'), api('/team'), api('/github/issues'),","api('/tasks?mine=false&include_done=false'), api('/team'), api('/github/issues').catch(() => []),")
s=s.replace("api('/settings'), api('/team'), api('/links'), api('/github/repositories'), api('/invites'),","api('/settings'), api('/team'), api('/links'), api('/github/repositories').catch(() => []), api('/invites'),")
p.write_text(s)
