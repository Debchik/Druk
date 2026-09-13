from pathlib import Path


def replace(path: str, old: str, new: str, count: int = 1):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'missing pattern in {path}: {old[:160]!r}')
    p.write_text(s.replace(old, new, count))

app = 'frontend/src/App.tsx'

replace(
    app,
    "const issuesQ=useQuery<GithubIssue[]>({queryKey:['github-issues'],queryFn:()=>api('/github/issues'),retry:false,staleTime:60_000})",
    "const issuesQ=useQuery<GithubIssue[]>({queryKey:['github-issues'],queryFn:()=>api('/github/issues'),enabled:!archiveView,retry:false,staleTime:60_000})",
)
replace(
    app,
    "if(q.isLoading)return <Loading/>;if(q.error)return <ErrorBox error={q.error}/>;const {tasks,members}=q.data;const issues=issuesQ.data||[]",
    "if(q.isLoading)return <Loading/>;if(q.error)return <ErrorBox error={q.error}/>;const {tasks,members}=q.data;const issues=archiveView?[]:(issuesQ.data||[])",
)
replace(
    app,
    "<Card title={<>Задачи <span className=\"count\">{tasks.length+issues.length}</span></>} className=\"task-list-card\">",
    "<Card title={<>{archiveView?'Архив задач':'Задачи'} <span className=\"count\">{tasks.length+issues.length}</span></>} className=\"task-list-card\">",
)
replace(
    app,
    "<Button type=\"button\" kind=\"secondary\" onClick={onArchive}>{task.archived?'↩ Вернуть из архива':'▣ Архивировать'}</Button><Button type=\"button\" kind=\"danger\" onClick={onDelete}>Удалить</Button><span/>",
    "<Button type=\"button\" kind=\"secondary\" onClick={onArchive}>{task.archived?'↩ Вернуть из архива':'▣ Архивировать'}</Button>{task.archived&&<Button type=\"button\" kind=\"danger\" onClick={onDelete}>Удалить навсегда</Button>}<span/>",
)

replace(
    app,
    "<textarea value={answer} onChange={e=>setAnswer(e.target.value)} rows={4} placeholder=\"Ответ\"/>",
    "<div className=\"markdown-editor-split program-markdown-editor\"><textarea value={answer} onChange={e=>setAnswer(e.target.value)} rows={7} placeholder=\"Ответ в Markdown — можно вставлять таблицы, списки, заголовки…\"/><div className=\"markdown-preview\"><small>Предпросмотр Markdown</small><Markdown text={answer}/></div></div>",
)
replace(
    app,
    "{answersEditing?<textarea className=\"program-answer-editor\" rows={6} value={answerDrafts[a.id]?.answer??a.answer} onChange={e=>setAnswerDrafts({...answerDrafts,[a.id]:{question:answerDrafts[a.id]?.question??a.question,answer:e.target.value}})}/>:<Markdown text={a.answer}/>}",
    "{answersEditing?<div className=\"markdown-editor-split program-markdown-editor compact-edit\"><textarea className=\"program-answer-editor\" rows={8} value={answerDrafts[a.id]?.answer??a.answer} onChange={e=>setAnswerDrafts({...answerDrafts,[a.id]:{question:answerDrafts[a.id]?.question??a.question,answer:e.target.value}})}/><div className=\"markdown-preview\"><small>Предпросмотр Markdown</small><Markdown text={answerDrafts[a.id]?.answer??a.answer}/></div></div>:<Markdown text={a.answer}/>}",
)

css = Path('frontend/src/stability.css')
s = css.read_text()
extra = '''
/* markdown-program-editor-v2 */
.program-answer-form .markdown-editor-split{grid-column:1/-1;width:100%}
.program-answer-form .markdown-editor-split textarea{min-height:190px;resize:vertical}
.program-answer-form .markdown-preview{min-height:190px;max-height:360px}
.program-answers .program-markdown-editor{margin:8px 0 10px}
.program-answers .program-markdown-editor textarea{min-height:210px;resize:vertical}
.program-answers .program-markdown-editor .markdown-preview{min-height:210px;max-height:420px}
.task-list-card .task-table::-webkit-scrollbar,.board-col::-webkit-scrollbar{width:9px;height:9px}
.task-list-card .task-table::-webkit-scrollbar-thumb,.board-col::-webkit-scrollbar-thumb{background:#cdd8c9;border-radius:999px;border:2px solid transparent;background-clip:padding-box}
[data-theme="dark"] .task-list-card .task-row.table-head{background:var(--panel-bg,#1f2420)}
@media(max-width:900px){.program-answer-form .markdown-preview,.program-answers .program-markdown-editor .markdown-preview{max-height:300px}}
'''
if 'markdown-program-editor-v2' not in s:
    css.write_text(s + extra)
