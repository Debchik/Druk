from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Missing patch anchor: {label}")
    return text.replace(old, new, 1)


# Backend: generic comments for reusable answers, program answers and files.
extended_path = ROOT / "backend/app/extended.py"
extended = extended_path.read_text()

extended = replace_once(
    extended,
    "class FileLink(BaseModel):\n    file_id: str\n\n\n@router.get(\"/team\")",
    """class FileLink(BaseModel):
    file_id: str


CommentEntity = Literal[\"answer\", \"program_answer\", \"file\"]
COMMENT_TABLES: dict[str, str] = {
    \"answer\": \"answer_library\",
    \"program_answer\": \"program_answers\",
    \"file\": \"files\",
}


class CommentCreate(BaseModel):
    entity_type: CommentEntity
    entity_id: str
    body: str = Field(min_length=1, max_length=10000)


class CommentPatch(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


async def ensure_comment_target(db: SupabaseClient, user: CurrentUser, entity_type: str, entity_id: str):
    table = COMMENT_TABLES.get(entity_type)
    if not table:
        raise AppError(422, \"INVALID_COMMENT_TARGET\", \"Некорректный тип объекта комментария\")
    await owned(db, table, user, entity_id)


@router.get(\"/comments\")
async def list_comments(
    entity_type: CommentEntity = Query(...),
    entity_id: str = Query(...),
    user: CurrentUser = Depends(current_user),
):
    db = db_for(user)
    await ensure_comment_target(db, user, entity_type, entity_id)
    rows = await db.select(
        \"entity_comments\",
        filters={\"workspace_id\": user.workspace_id, \"entity_type\": entity_type, \"entity_id\": entity_id},
        order=\"created_at.asc\",
    )
    members = await db.select(
        \"workspace_members\",
        filters={\"workspace_id\": user.workspace_id},
        select=\"user_id,display_name\",
    )
    names = {row[\"user_id\"]: row[\"display_name\"] for row in members}
    for row in rows:
        row[\"author_name\"] = names.get(row.get(\"created_by\"), \"Участник\")
        row[\"can_edit\"] = row.get(\"created_by\") == user.id
    return rows


@router.post(\"/comments\", status_code=201)
async def create_comment(body: CommentCreate, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    await ensure_comment_target(db, user, body.entity_type, body.entity_id)
    rows = await db.insert(\"entity_comments\", {
        \"workspace_id\": user.workspace_id,
        \"entity_type\": body.entity_type,
        \"entity_id\": body.entity_id,
        \"body\": body.body.strip(),
        \"created_by\": user.id,
    })
    row = rows[0]
    row[\"author_name\"] = user.display_name
    row[\"can_edit\"] = True
    return row


@router.patch(\"/comments/{comment_id}\")
async def patch_comment(comment_id: str, body: CommentPatch, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    comment = await owned(db, \"entity_comments\", user, comment_id)
    if comment.get(\"created_by\") != user.id:
        raise AppError(403, \"COMMENT_FORBIDDEN\", \"Можно редактировать только свои комментарии\")
    rows = await db.patch(
        \"entity_comments\",
        {\"id\": comment_id, \"workspace_id\": user.workspace_id, \"created_by\": user.id},
        {\"body\": body.body.strip()},
    )
    return rows[0]


@router.delete(\"/comments/{comment_id}\", status_code=204)
async def delete_comment(comment_id: str, user: CurrentUser = Depends(current_user)):
    db = db_for(user)
    comment = await owned(db, \"entity_comments\", user, comment_id)
    if comment.get(\"created_by\") != user.id:
        raise AppError(403, \"COMMENT_FORBIDDEN\", \"Можно удалить только свой комментарий\")
    await db.delete(\"entity_comments\", {\"id\": comment_id, \"workspace_id\": user.workspace_id, \"created_by\": user.id})


@router.get(\"/team\")""",
    "comments backend",
)
extended_path.write_text(extended)


# Frontend application interactions.
app_path = ROOT / "frontend/src/App.tsx"
app = app_path.read_text()

app = replace_once(
    app,
    "type Metric={metric_date?:string;users_total:number;messages_total:number;dialogs_total:number;weekly_active:number;avg_session_seconds:number;retention_7d:number;registration_conversion:number;changes?:Record<string,number>}\n",
    "type Metric={metric_date?:string;users_total:number;messages_total:number;dialogs_total:number;weekly_active:number;avg_session_seconds:number;retention_7d:number;registration_conversion:number;changes?:Record<string,number>}\ntype CommentRow={id:string;body:string;created_by?:string|null;author_name?:string;can_edit?:boolean;created_at:string;updated_at:string}\n",
    "comment type",
)

button_anchor = "function Button({children,kind='primary',...props}:{children:ReactNode;kind?:'primary'|'secondary'|'danger'|'ghost'}&React.ButtonHTMLAttributes<HTMLButtonElement>){return <button {...props} className={cx('btn',kind,props.className)}>{children}</button>}\n"
comments_component = button_anchor + """
function CommentsPanel({entityType,entityId,compact=false}:{entityType:'answer'|'program_answer'|'file';entityId:string;compact?:boolean}){
 const qc=useQueryClient();const [text,setText]=useState('');const [editingId,setEditingId]=useState<string|null>(null);const [editText,setEditText]=useState('')
 const key=['comments',entityType,entityId]
 const q=useQuery<CommentRow[]>({queryKey:key,enabled:Boolean(entityId),queryFn:()=>api(`/comments?entity_type=${entityType}&entity_id=${encodeURIComponent(entityId)}`)})
 const add=useMutation({mutationFn:()=>api('/comments',json('POST',{entity_type:entityType,entity_id:entityId,body:text.trim()})),onSuccess:()=>{setText('');void qc.invalidateQueries({queryKey:key})}})
 const edit=useMutation({mutationFn:({id,body}:{id:string;body:string})=>api(`/comments/${id}`,json('PATCH',{body})),onSuccess:()=>{setEditingId(null);setEditText('');void qc.invalidateQueries({queryKey:key})}})
 const del=useMutation({mutationFn:(id:string)=>api(`/comments/${id}`,{method:'DELETE'}),onSuccess:()=>void qc.invalidateQueries({queryKey:key})})
 return <section className={cx('comments-panel',compact&&'compact')}><div className="comments-head"><b>Комментарии</b><span>{q.data?.length||0}</span></div>{q.isLoading?<div className="comments-empty">Загрузка…</div>:q.data?.length?<div className="comment-list">{q.data.map(c=><article key={c.id}><div><b>{c.author_name||'Участник'}</b><small>{new Date(c.created_at).toLocaleString('ru-RU')}</small></div>{editingId===c.id?<div className="comment-edit"><textarea rows={2} value={editText} onChange={e=>setEditText(e.target.value)}/><div><button onClick={()=>edit.mutate({id:c.id,body:editText.trim()})} disabled={!editText.trim()}>Сохранить</button><button onClick={()=>setEditingId(null)}>Отмена</button></div></div>:<p>{c.body}</p>}{c.can_edit&&editingId!==c.id&&<footer><button onClick={()=>{setEditingId(c.id);setEditText(c.body)}}>Изменить</button><button onClick={()=>{if(confirm('Удалить комментарий?'))del.mutate(c.id)}}>Удалить</button></footer>}</article>)}</div>:<div className="comments-empty">Комментариев пока нет.</div>}<form className="comment-form" onSubmit={e=>{e.preventDefault();if(text.trim())add.mutate()}}><textarea rows={compact?2:3} value={text} onChange={e=>setText(e.target.value)} placeholder="Комментарий, правка или замечание…"/><Button disabled={!text.trim()||add.isPending}>{add.isPending?'Добавляем…':'Добавить комментарий'}</Button></form></section>
}
"""
app = replace_once(app, button_anchor, comments_component, "comments component")

app = replace_once(
    app,
    "const [newCheck,setNewCheck]=useState(''),[question,setQuestion]=useState(''),[answer,setAnswer]=useState(''),[libOpen,setLibOpen]=useState(false)",
    "const [newCheck,setNewCheck]=useState(''),[question,setQuestion]=useState(''),[answer,setAnswer]=useState(''),[libOpen,setLibOpen]=useState(false),[answersEditing,setAnswersEditing]=useState(false),[answerDrafts,setAnswerDrafts]=useState<Record<string,{question:string;answer:string}>>({})",
    "program answer edit state",
)

app = replace_once(
    app,
    "const linkFile=useMutation({mutationFn:(file_id:string)=>api(`/programs/${id}/files/link`,json('POST',{file_id})),onSuccess:()=>void qc.invalidateQueries({queryKey:['program-detail-rich',id]})})\n if(q.isLoading)",
    "const linkFile=useMutation({mutationFn:(file_id:string)=>api(`/programs/${id}/files/link`,json('POST',{file_id})),onSuccess:()=>void qc.invalidateQueries({queryKey:['program-detail-rich',id]})})\n const saveAnswers=useMutation({mutationFn:()=>Promise.all(Object.entries(answerDrafts).map(([aid,value])=>api(`/program-answers/${aid}`,json('PATCH',value)))),onSuccess:()=>{setAnswersEditing(false);void qc.invalidateQueries({queryKey:['program-detail-rich',id]})}})\n if(q.isLoading)",
    "bulk answer mutation",
)

app = replace_once(
    app,
    '<Card title="Ответы для заявки" action={<div className="answer-tools"><button className="text-button" onClick={()=>setLibOpen(!libOpen)}>Найти в базе</button></div>}>',
    '<Card title="Ответы для заявки" action={<div className="answer-tools"><button className="text-button" onClick={()=>setLibOpen(!libOpen)}>Найти в базе</button><button className="text-button" onClick={()=>{if(answersEditing){saveAnswers.mutate()}else{setAnswerDrafts(Object.fromEntries(d.answers.map(a=>[a.id,{question:a.question,answer:a.answer}])));setAnswersEditing(true)}}} disabled={saveAnswers.isPending}>{answersEditing?(saveAnswers.isPending?\'Сохраняем…\':\'Сохранить все\'):\'Редактировать все\'}</button>{answersEditing&&<button className="text-button muted-action" onClick={()=>setAnswersEditing(false)}>Отмена</button>}</div>}>',
    "bulk answer controls",
)

old_program_answers = """<div className=\"program-answers\">{d.answers.map((a,i)=><article key={a.id}><div><b>{i+1}. {a.question}</b>{a.source_answer_id&&<Chip>Из базы ответов</Chip>}</div><p>{a.answer||'Ответ пока пуст.'}</p><footer><button onClick={()=>void navigator.clipboard.writeText(a.answer)}><Icon name=\"copy\"/>Копировать</button><button>✎ Адаптировать</button></footer></article>)}</div>"""
new_program_answers = """<div className=\"program-answers\">{d.answers.map((a,i)=><article key={a.id} className={answersEditing?'editing-answer':''}><div>{answersEditing?<input className=\"program-answer-question\" value={answerDrafts[a.id]?.question??a.question} onChange={e=>setAnswerDrafts({...answerDrafts,[a.id]:{question:e.target.value,answer:answerDrafts[a.id]?.answer??a.answer}})}/>:<b>{i+1}. {a.question}</b>}{a.source_answer_id&&<Chip>Из базы ответов</Chip>}</div>{answersEditing?<textarea className=\"program-answer-editor\" rows={6} value={answerDrafts[a.id]?.answer??a.answer} onChange={e=>setAnswerDrafts({...answerDrafts,[a.id]:{question:answerDrafts[a.id]?.question??a.question,answer:e.target.value}})}/>:<p>{a.answer||'Ответ пока пуст.'}</p>}<footer><button onClick={()=>void navigator.clipboard.writeText(answersEditing?(answerDrafts[a.id]?.answer??a.answer):a.answer)}><Icon name=\"copy\"/>Копировать</button>{!answersEditing&&<button onClick={()=>{setAnswerDrafts(Object.fromEntries(d.answers.map(x=>[x.id,{question:x.question,answer:x.answer}])));setAnswersEditing(true)}}>✎ Адаптировать</button>}</footer><CommentsPanel entityType=\"program_answer\" entityId={a.id} compact/></article>)}</div>"""
app = replace_once(app, old_program_answers, new_program_answers, "program answers UI")

app = replace_once(
    app,
    "function FileLine({file}:{file:FileRow}){return <div className=\"file-line\"><span className={`file-type ${file.original_name.split('.').pop()?.toLowerCase()}`}>{(file.original_name.split('.').pop()||'FILE').toUpperCase().slice(0,4)}</span><div><b>{file.display_name}</b><small>{file.scope==='program'?'Документ программы':'Общий файл'} · {bytes(file.size_bytes)}</small></div><span>{new Date(file.created_at).toLocaleDateString('ru-RU')}</span><Dots/></div>}",
    "function FileLine({file}:{file:FileRow}){const [open,setOpen]=useState(false);return <div className=\"file-line-wrap\"><div className=\"file-line\"><span className={`file-type ${file.original_name.split('.').pop()?.toLowerCase()}`}>{(file.original_name.split('.').pop()||'FILE').toUpperCase().slice(0,4)}</span><div><b>{file.display_name}</b><small>{file.scope==='program'?'Документ программы':'Общий файл'} · {bytes(file.size_bytes)}</small></div><span>{new Date(file.created_at).toLocaleDateString('ru-RU')}</span><button className=\"icon-btn file-comment-btn\" title=\"Комментарии\" onClick={()=>setOpen(!open)}>💬</button></div>{open&&<CommentsPanel entityType=\"file\" entityId={file.id} compact/>}</div>}",
    "program file comments",
)

app = replace_once(
    app,
    "const qc=useQueryClient();const [filter,setFilter]=useState('all'),[search,setSearch]=useState('');const q=useQuery<any>",
    "const qc=useQueryClient();const [filter,setFilter]=useState('all'),[search,setSearch]=useState(''),[commentFile,setCommentFile]=useState<string|null>(null);const q=useQuery<any>",
    "file comment state",
)

app = replace_once(
    app,
    '<button title="Сделать презентацией" onClick={()=>setPresentation.mutate(f.id)}>★</button><button onClick={()=>{if(confirm(\'Удалить файл?\'))del.mutate(f.id)}}>⋮</button>',
    '<button title="Комментарии" onClick={()=>setCommentFile(commentFile===f.id?null:f.id)}>💬</button><button title="Сделать презентацией" onClick={()=>setPresentation.mutate(f.id)}>★</button><button onClick={()=>{if(confirm(\'Удалить файл?\'))del.mutate(f.id)}}>⋮</button>',
    "file comment button",
)

app = replace_once(
    app,
    '<aside className="right-column"><Card title="Загрузить файлы">',
    '<aside className="right-column">{commentFile&&<Card title={<>Комментарии · <span className="comment-file-title">{files.find(f=>f.id===commentFile)?.display_name}</span></>}><CommentsPanel entityType="file" entityId={commentFile}/></Card>}<Card title="Загрузить файлы">',
    "file comments sidebar",
)

app = replace_once(
    app,
    "<div className=\"detail-actions\">{editing?<Button onClick={onSave}>Сохранить</Button>:<><Button kind=\"secondary\" onClick={()=>void navigator.clipboard.writeText(answer.answer)}><Icon name=\"copy\"/>Копировать</Button><Button kind=\"secondary\" onClick={onEdit}><Icon name=\"edit\"/>Изменить</Button><Button disabled={!program} onClick={()=>void addToProgram()}>➤ Использовать в программе</Button></>}</div></>}",
    "<div className=\"detail-actions\">{editing?<Button onClick={onSave}>Сохранить</Button>:<><Button kind=\"secondary\" onClick={()=>void navigator.clipboard.writeText(answer.answer)}><Icon name=\"copy\"/>Копировать</Button><Button kind=\"secondary\" onClick={onEdit}><Icon name=\"edit\"/>Изменить</Button><Button disabled={!program} onClick={()=>void addToProgram()}>➤ Использовать в программе</Button></>}</div>{('id' in answer)&&<CommentsPanel entityType=\"answer\" entityId={answer.id}/>}</>}",
    "answer comments",
)

app_path.write_text(app)


# Responsive hardening. App should fill wide monitors and never let event controls overflow their column.
css_path = ROOT / "frontend/src/styles.css"
css = css_path.read_text()
marker = "/* collaboration-responsive-v2 */"
if marker not in css:
    css += """

/* collaboration-responsive-v2 */
.comments-panel{margin-top:12px;padding-top:11px;border-top:1px solid #edf0ec;min-width:0}.comments-panel.compact{margin-top:9px;padding-top:8px}.comments-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.comments-head b{font-size:11px}.comments-head span{font-size:9px;color:#71806f;background:#edf4e9;border-radius:999px;padding:2px 7px}.comment-list{display:grid;gap:7px;margin-bottom:9px}.comment-list article{border:1px solid #e5e9e2;border-radius:8px;padding:8px;background:#fbfcfa}.comment-list article>div:first-child{display:flex;justify-content:space-between;gap:8px;align-items:center}.comment-list article b{font-size:9.5px}.comment-list article small{font-size:8px;color:#909691}.comment-list article p{margin:5px 0 0;font-size:9.5px;line-height:1.4;white-space:pre-wrap;color:#515a54}.comment-list footer{display:flex;gap:8px;margin-top:6px}.comment-list footer button,.comment-edit button{border:0;background:transparent;padding:0;color:#4a7e3e;font-size:8.5px}.comment-list footer button:last-child{color:#b85a5a}.comment-form{display:grid;gap:7px}.comment-form textarea{min-height:58px;font-size:10px}.comment-form .btn{justify-self:start;min-height:32px;padding:6px 10px;font-size:9.5px}.comments-empty{font-size:9.5px;color:#929892;padding:5px 0 9px}.comment-edit{display:grid!important;gap:5px;margin-top:6px}.comment-edit textarea{font-size:9.5px}.comment-edit>div{display:flex!important;gap:8px}.comment-file-title{font-weight:500;color:#69736b;max-width:170px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom}.file-line-wrap{border-bottom:1px solid #eef0ed}.file-line-wrap .file-line{border-bottom:0}.file-line-wrap>.comments-panel{padding:8px 6px 10px;margin:0}.file-comment-btn{font-size:11px}.answer-tools{gap:12px;align-items:center;flex-wrap:wrap}.muted-action{color:#8b918d!important}.program-answer-question{font-weight:700;font-size:11px;padding:7px 9px}.program-answer-editor{font-size:10.5px;line-height:1.5;margin-top:8px}.program-answers article.editing-answer{background:#fbfdf9;border-color:#cedfc7}.program-answers article>.comments-panel{margin-top:9px}.stack-form,.stack-form>*,.form-two,.form-two>*{min-width:0;max-width:100%}.form-two{grid-template-columns:repeat(2,minmax(0,1fr))}.events-layout .right-column,.events-layout .panel{min-width:0}.events-layout input[type=date],.events-layout input[type=time]{min-width:0;width:100%;padding-left:10px;padding-right:8px}

@media(min-width:961px){
 .app-shell{width:100%;max-width:none;margin:0;grid-template-columns:clamp(190px,13vw,250px) minmax(0,1fr);box-shadow:none}
 .content{padding:clamp(16px,1.2vw,30px);padding-bottom:40px}
 .topbar{padding-left:clamp(18px,1.3vw,32px);padding-right:clamp(20px,1.5vw,38px)}
 .global-search{width:clamp(360px,32vw,620px)}
 .tasks-layout,.program-layout,.events-layout,.program-detail-grid{grid-template-columns:minmax(0,1fr) clamp(300px,21vw,390px);gap:clamp(12px,1vw,20px)}
 .files-layout{grid-template-columns:minmax(0,1fr) clamp(280px,20vw,360px);gap:clamp(12px,1vw,20px)}
 .right-column{top:82px;min-width:0}
 .page-banner{grid-template-columns:minmax(0,1fr) clamp(300px,26vw,470px)}
 .settings-banner{grid-template-columns:minmax(0,1fr) clamp(300px,25vw,460px)}
 .home-hero{grid-template-columns:minmax(0,1.15fr) minmax(360px,.85fr);height:clamp(250px,16vw,330px)}
 .dashboard-grid{grid-template-columns:minmax(0,1.45fr) minmax(320px,.75fr)}
 .answers-layout{grid-template-columns:clamp(155px,11vw,210px) clamp(300px,23vw,420px) minmax(0,1fr)}
 .summary-cards{grid-template-columns:repeat(4,minmax(150px,1fr))}
 .deadline-cards{grid-template-columns:repeat(4,minmax(180px,1fr))}
 .metrics-grid{grid-template-columns:repeat(4,minmax(180px,1fr))}
 .feedback-grid{grid-template-columns:repeat(3,minmax(240px,1fr))}
 .event-row{grid-template-columns:20px 76px minmax(220px,2.2fr) minmax(86px,.65fr) minmax(90px,.7fr) minmax(105px,1fr) 86px 28px}
}
@media(min-width:1700px){
 .sidebar{padding-left:22px;padding-right:22px}.sidebar-art{margin-left:-22px;margin-right:-22px}
 .page-title h1{font-size:clamp(38px,2.2vw,48px)}
 .panel{padding:clamp(13px,.85vw,18px)}
 .panel-head h2,.section-row h2{font-size:clamp(16px,1vw,19px)}
 .program-head .title-line h1{font-size:clamp(31px,1.8vw,40px)}
}
@media(max-width:960px){
 .form-two{grid-template-columns:repeat(2,minmax(0,1fr))}
 .events-layout .right-column{width:100%}
 .comments-panel{max-width:100%}
}
@media(max-width:680px){
 .form-two{grid-template-columns:1fr}
 .comment-form .btn{width:100%}
}
"""
css_path.write_text(css)

# One-shot patch workflow cleans itself up after committing the real changes.
for rel in ["scripts/apply_collaboration_upgrade.py", ".github/workflows/apply-collaboration-upgrade.yml"]:
    p = ROOT / rel
    if p.exists():
        p.unlink()
