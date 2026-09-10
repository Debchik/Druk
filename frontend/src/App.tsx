import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import type { QueryClient } from '@tanstack/react-query'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, NavLink, Navigate, Route, Routes, useParams } from 'react-router-dom'
import { z } from 'zod'
import { api, ApiError, json } from './lib/api'
import { supabase } from './lib/supabase'
import { Answer, Dashboard, Decision, FileRow, Me, Meeting, Member, Program, Settings, Task, type ProgramRow, type TaskRow } from './lib/models'
import { fmtDate, weekStart } from './lib/date'

const A=z.array(Answer), F=z.array(FileRow), M=z.array(Meeting), D=z.array(Decision), T=z.array(Task), P=z.array(Program), Members=z.array(Member)
const statusName:Record<string,string>={planned:'Запланировано',in_progress:'В работе',done:'Готово',considering:'Рассматриваем',preparing:'Готовим',submitted:'Подали',next_stage:'Следующий этап',accepted:'Приняты',rejected:'Отказ'}

function Loading(){return <div className="state">Загрузка…</div>}
function ErrorBox({error}:{error:unknown}){return <div className="state error">{error instanceof Error?error.message:'Ошибка запроса'}</div>}
function Page({title,action,children}:{title:string;action?:ReactNode;children:ReactNode}){return <><header className="page-head"><div><h1>{title}</h1></div>{action}</header>{children}</>}
function Empty({children}:{children:ReactNode}){return <div className="empty">{children}</div>}

function Shell(){
 const nav=[['/','Главная'],['/tasks','Задачи'],['/programs','Программы'],['/answers','База ответов'],['/files','Файлы'],['/meetings','Встречи и решения'],['/settings','Настройки']]
 return <div className="shell"><aside><div className="brand"><img src={`${import.meta.env.BASE_URL}druk.webp`} alt=""/><div><strong>Друк</strong><span>командное пространство</span></div></div><nav>{nav.map(([to,label])=><NavLink key={to} to={to} end={to==='/' }>{label}</NavLink>)}</nav></aside><main><Routes><Route index element={<DashboardPage/>}/><Route path="tasks" element={<TasksPage/>}/><Route path="programs" element={<ProgramsPage/>}/><Route path="programs/:id" element={<ProgramPage/>}/><Route path="answers" element={<AnswersPage/>}/><Route path="files" element={<FilesPage/>}/><Route path="meetings" element={<MeetingsPage/>}/><Route path="settings" element={<SettingsPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></main></div>
}

export default function App({queryClient}:{queryClient:QueryClient}){
 const [ready,setReady]=useState(false),[signed,setSigned]=useState(false)
 useEffect(()=>{void supabase.auth.getSession().then(({data})=>{setSigned(Boolean(data.session));setReady(true)});const {data}=supabase.auth.onAuthStateChange((_event,session)=>{setSigned(Boolean(session));if(!session)queryClient.clear()});return()=>data.subscription.unsubscribe()},[queryClient])
 if(!ready)return <Loading/>
 if(!signed)return <Login/>
 return <Gate/>
}

function Gate(){
 const q=useQuery({queryKey:['me'],queryFn:()=>api('/me',{},Me)})
 if(q.isLoading)return <Loading/>
 if(q.error){const denied=q.error instanceof ApiError&&q.error.status===403;return <div className="auth"><div className="auth-card"><h1>{denied?'Нет доступа':'Ошибка входа'}</h1><p>{denied?'Аккаунт создан, но не добавлен в workspace Друка.':q.error.message}</p><button onClick={()=>void supabase.auth.signOut()}>Выйти</button></div></div>}
 return <Shell/>
}

function Login(){
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError('');const {error:err}=await supabase.auth.signInWithPassword({email,password});if(err)setError(err.message);setBusy(false)}
 return <div className="auth"><div className="auth-card"><img className="hero-character" src={`${import.meta.env.BASE_URL}druk.webp`} alt="Друк"/><p className="eyebrow">Внутренняя платформа</p><h1>Рабочее пространство Друка</h1><p>Доступ только для двух сооснователей.</p><form onSubmit={submit}><label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required autoComplete="email"/></label><label>Пароль<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required autoComplete="current-password"/></label>{error&&<div className="field-error">{error}</div>}<button disabled={busy}>{busy?'Входим…':'Войти'}</button></form></div></div>
}

function DashboardPage(){
 const q=useQuery({queryKey:['dashboard'],queryFn:()=>api('/dashboard',{},Dashboard)})
 if(q.isLoading)return <Loading/>;if(q.error)return <ErrorBox error={q.error}/>;const x=q.data!
 return <Page title="Главная"><section className="hero"><div><p className="eyebrow">Сейчас</p><h2>{x.settings?.project_name||'Друк'}</h2><p>{x.settings?.description||'Добавьте краткое описание проекта в настройках.'}</p><div className="chips"><span>{x.settings?.stage||'Этап не указан'}</span><span>{x.settings?.next_result||'Ближайший результат не указан'}</span></div></div><img src={`${import.meta.env.BASE_URL}druk.webp`} alt=""/></section><div className="grid two"><Card title="Фокус недели">{x.focus.length?x.focus.slice(0,3).map(v=><Row key={v.id} title={v.text} meta={`${v.week_start}${v.done?' · готово':''}`}/>):<Empty>Фокус ещё не задан.</Empty>}</Card><Card title="Активные задачи">{x.tasks.length?x.tasks.slice(0,6).map(v=><Row key={v.id} title={v.title} meta={`${statusName[v.status]}${v.due_date?' · '+fmtDate(v.due_date):''}`}/>):<Empty>Активных задач нет.</Empty>}<Link className="text-link" to="/tasks">Все задачи →</Link></Card><Card title="Ближайшие программы">{x.programs.length?x.programs.slice(0,5).map(v=><Row key={v.id} title={v.name} meta={`${statusName[v.status]}${v.deadline?' · '+fmtDate(v.deadline):''}`}/>):<Empty>Программ пока нет.</Empty>}<Link className="text-link" to="/programs">Все программы →</Link></Card><Card title="Последние решения">{x.decisions.length?x.decisions.map(v=><Row key={v.id} title={v.title} meta={fmtDate(v.decision_date)}/>):<Empty>Решения ещё не зафиксированы.</Empty>}</Card></div></Page>
}
function Card({title,children}:{title:string;children:ReactNode}){return <section className="card"><h2>{title}</h2>{children}</section>}
function Row({title,meta,children}:{title:string;meta?:string;children?:ReactNode}){return <div className="row"><div><strong>{title}</strong>{meta&&<span>{meta}</span>}</div>{children}</div>}

function TasksPage(){
 const qc=useQueryClient(),[title,setTitle]=useState(''),[showDone,setShowDone]=useState(false)
 const q=useQuery({queryKey:['tasks',showDone],queryFn:()=>api(`/tasks?include_done=${showDone}`,{},T)})
 const add=useMutation({mutationFn:()=>api<TaskRow>('/tasks',json('POST',{title,planned_week:weekStart()}),Task),onSuccess:()=>{setTitle('');void qc.invalidateQueries({queryKey:['tasks']});void qc.invalidateQueries({queryKey:['dashboard']})}})
 const setStatus=useMutation({mutationFn:({id,status}:{id:string;status:string})=>api(`/tasks/${id}`,json('PATCH',{status}),Task),onSuccess:()=>{void qc.invalidateQueries({queryKey:['tasks']});void qc.invalidateQueries({queryKey:['dashboard']})}})
 return <Page title="Задачи" action={<label className="toggle"><input type="checkbox" checked={showDone} onChange={e=>setShowDone(e.target.checked)}/>Показывать готовые</label>}><form className="quick" onSubmit={e=>{e.preventDefault();if(title.trim())add.mutate()}}><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Новая задача" maxLength={240}/><button disabled={!title.trim()||add.isPending}>Добавить</button></form>{q.isLoading?<Loading/>:q.error?<ErrorBox error={q.error}/>:<section className="card list">{q.data!.length?q.data!.map(t=><Row key={t.id} title={t.title} meta={`${statusName[t.status]}${t.blocked?' · заблокировано':''}${t.due_date?' · до '+fmtDate(t.due_date):''}`}><select aria-label={`Статус ${t.title}`} value={t.status} onChange={e=>setStatus.mutate({id:t.id,status:e.target.value})}><option value="planned">Запланировано</option><option value="in_progress">В работе</option><option value="done">Готово</option></select></Row>):<Empty>Задач пока нет.</Empty>}</section>}</Page>
}

function ProgramsPage(){
 const qc=useQueryClient(),[name,setName]=useState(''),[search,setSearch]=useState('')
 const q=useQuery({queryKey:['programs'],queryFn:()=>api('/programs',{},P)})
 const add=useMutation({mutationFn:()=>api<ProgramRow>('/programs',json('POST',{name}),Program),onSuccess:()=>{setName('');void qc.invalidateQueries({queryKey:['programs']});void qc.invalidateQueries({queryKey:['dashboard']})}})
 const visible=(q.data||[]).filter(p=>p.name.toLowerCase().includes(search.toLowerCase()))
 return <Page title="Программы"><form className="quick" onSubmit={e=>{e.preventDefault();if(name.trim())add.mutate()}}><input value={name} onChange={e=>setName(e.target.value)} placeholder="Название программы"/><button disabled={!name.trim()||add.isPending}>Добавить</button></form><input className="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Поиск по названию"/>{q.isLoading?<Loading/>:q.error?<ErrorBox error={q.error}/>:<section className="card list">{visible.length?visible.map(p=><Link className="program-row" key={p.id} to={`/programs/${p.id}`}><div><strong>{p.name}</strong><span>{statusName[p.status]}{p.deadline?` · дедлайн ${fmtDate(p.deadline)}`:''}</span></div><b>→</b></Link>):<Empty>Подходящих программ нет.</Empty>}</section>}</Page>
}

const ProgramDetail=z.object({program:Program,checklist:z.array(z.object({id:z.string(),text:z.string(),done:z.boolean()}).passthrough()),answers:z.array(z.object({id:z.string(),question:z.string(),answer:z.string(),updated_at:z.string()}).passthrough()),files:z.array(z.unknown()),submissions:z.array(z.object({id:z.string(),created_at:z.string(),snapshot:z.unknown()}).passthrough())})
function ProgramPage(){
 const {id}=useParams(),qc=useQueryClient(),[check,setCheck]=useState(''),[question,setQuestion]=useState(''),[answer,setAnswer]=useState('')
 const q=useQuery({queryKey:['program',id],enabled:Boolean(id),queryFn:()=>api(`/programs/${id}`,{},ProgramDetail)})
 const addCheck=useMutation({mutationFn:()=>api(`/programs/${id}/checklist`,json('POST',{text:check})),onSuccess:()=>{setCheck('');void qc.invalidateQueries({queryKey:['program',id]})}})
 const addAnswer=useMutation({mutationFn:()=>api(`/programs/${id}/answers`,json('POST',{question,answer})),onSuccess:()=>{setQuestion('');setAnswer('');void qc.invalidateQueries({queryKey:['program',id]})}})
 const snap=useMutation({mutationFn:()=>api(`/programs/${id}/submissions`,json('POST')),onSuccess:()=>void qc.invalidateQueries({queryKey:['program',id]})})
 if(q.isLoading)return <Loading/>;if(q.error)return <ErrorBox error={q.error}/>;const x=q.data!
 return <Page title={x.program.name} action={<Link className="button secondary" to="/programs">← Назад</Link>}><div className="grid two"><Card title="Общая информация"><p>Статус: <b>{statusName[x.program.status]}</b></p><p>Дедлайн: <b>{fmtDate(x.program.deadline)}</b></p><p>{x.program.next_step||'Следующий шаг не указан.'}</p></Card><Card title="Чек-лист"><form className="quick compact" onSubmit={e=>{e.preventDefault();if(check.trim())addCheck.mutate()}}><input value={check} onChange={e=>setCheck(e.target.value)} placeholder="Новый пункт"/><button>+</button></form>{x.checklist.length?x.checklist.map(c=><Row key={c.id} title={c.text} meta={c.done?'Готово':'Не выполнено'}/>):<Empty>Пунктов нет.</Empty>}</Card></div><Card title="Ответы для заявки"><form className="stack" onSubmit={e=>{e.preventDefault();if(question.trim())addAnswer.mutate()}}><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Вопрос"/><textarea value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Ответ" rows={4}/><button disabled={!question.trim()}>Добавить ответ</button></form>{x.answers.map(a=><div className="answer" key={a.id}><strong>{a.question}</strong><p>{a.answer||'Ответ пока пуст.'}</p><button className="small secondary" onClick={()=>void navigator.clipboard.writeText(a.answer)}>Копировать</button></div>)}</Card><Card title="Отправленные версии"><button onClick={()=>snap.mutate()} disabled={snap.isPending}>Зафиксировать текущую версию</button><p className="muted">Снимок сохраняет текущие поля программы, ответы и ссылки на файлы.</p>{x.submissions.map(s=><Row key={s.id} title="Зафиксированная заявка" meta={new Date(s.created_at).toLocaleString('ru-RU')}/>)}</Card></Page>
}

function AnswersPage(){
 const qc=useQueryClient(),[qtext,setQtext]=useState(''),[question,setQuestion]=useState(''),[answer,setAnswer]=useState(''),[keywords,setKeywords]=useState('')
 const q=useQuery({queryKey:['answers',qtext],queryFn:()=>api(`/answers${qtext.trim()?`?q=${encodeURIComponent(qtext.trim())}`:''}`,{},A)})
 const add=useMutation({mutationFn:()=>api('/answers',json('POST',{question,answer,keywords}),Answer),onSuccess:()=>{setQuestion('');setAnswer('');setKeywords('');void qc.invalidateQueries({queryKey:['answers']})}})
 return <Page title="База ответов"><input className="search" value={qtext} onChange={e=>setQtext(e.target.value)} placeholder="Искать по вопросу, ответу и ключевым словам"/><Card title="Новый ответ"><form className="stack" onSubmit={e=>{e.preventDefault();if(question.trim())add.mutate()}}><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Вопрос / название"/><textarea value={answer} onChange={e=>setAnswer(e.target.value)} rows={5} placeholder="Текст ответа"/><input value={keywords} onChange={e=>setKeywords(e.target.value)} placeholder="Ключевые слова через запятую"/><div className="form-foot"><span>{answer.length} символов</span><button disabled={!question.trim()||add.isPending}>Сохранить</button></div></form></Card>{q.isLoading?<Loading/>:q.error?<ErrorBox error={q.error}/>:<section className="answers">{q.data!.length?q.data!.map(a=><article className="card answer" key={a.id}><h2>{a.question}</h2><p>{a.answer||'Пустой ответ'}</p><div className="form-foot"><span>{a.answer.length} символов · {a.keywords||'без ключевых слов'}</span><button className="small secondary" onClick={()=>void navigator.clipboard.writeText(a.answer)}>Копировать</button></div></article>):<Empty>Ничего не найдено.</Empty>}</section>}</Page>
}

function FilesPage(){
 const qc=useQueryClient(),q=useQuery({queryKey:['files'],queryFn:()=>api('/files',{},F)}),[file,setFile]=useState<File|null>(null)
 const upload=useMutation({mutationFn:async()=>{if(!file)return;const form=new FormData();form.set('file',file);form.set('scope','project');return api('/files',{method:'POST',body:form},FileRow)},onSuccess:()=>{setFile(null);void qc.invalidateQueries({queryKey:['files']})}})
 async function open(id:string){const x=await api(`/files/${id}/signed-url`,json('POST'),z.object({url:z.string().url(),expires_in:z.number()}));window.open(x.url,'_blank','noopener,noreferrer')}
 return <Page title="Файлы"><div className="upload"><input type="file" onChange={e=>setFile(e.target.files?.[0]||null)}/><button disabled={!file||upload.isPending} onClick={()=>upload.mutate()}>Загрузить</button><span>До 20 MiB · PDF, Office, TXT/CSV, PNG/JPEG/WebP</span></div>{q.isLoading?<Loading/>:q.error?<ErrorBox error={q.error}/>:<section className="card list">{q.data!.length?q.data!.map(f=><Row key={f.id} title={f.display_name} meta={`${(f.size_bytes/1024/1024).toFixed(2)} MiB · ${f.scope==='project'?'общий':'программа'}`}><button className="small secondary" onClick={()=>void open(f.id)}>Открыть</button></Row>):<Empty>Файлов пока нет.</Empty>}</section>}</Page>
}

function MeetingsPage(){
 const qc=useQueryClient(),meet=useQuery({queryKey:['meetings'],queryFn:()=>api('/meetings',{},M)}),dec=useQuery({queryKey:['decisions'],queryFn:()=>api('/decisions',{},D)})
 const [title,setTitle]=useState('Встреча'),[meetingDate,setMeetingDate]=useState(new Date().toISOString().slice(0,10)),[notes,setNotes]=useState(''),[dtitle,setDtitle]=useState(''),[dtext,setDtext]=useState('')
 const addM=useMutation({mutationFn:()=>api('/meetings',json('POST',{title,meeting_date:meetingDate,notes}),Meeting),onSuccess:()=>{setNotes('');void qc.invalidateQueries({queryKey:['meetings']})}})
 const addD=useMutation({mutationFn:()=>api('/decisions',json('POST',{title:dtitle,text:dtext}),Decision),onSuccess:()=>{setDtitle('');setDtext('');void qc.invalidateQueries({queryKey:['decisions']});void qc.invalidateQueries({queryKey:['dashboard']})}})
 return <Page title="Встречи и решения"><div className="grid two"><Card title="Новая встреча"><form className="stack" onSubmit={e=>{e.preventDefault();addM.mutate()}}><input value={title} onChange={e=>setTitle(e.target.value)}/><input type="date" value={meetingDate} onChange={e=>setMeetingDate(e.target.value)}/><textarea value={notes} onChange={e=>setNotes(e.target.value)} rows={4} placeholder="Свободные заметки"/><button>Сохранить встречу</button></form></Card><Card title="Новое решение"><form className="stack" onSubmit={e=>{e.preventDefault();if(dtitle.trim()&&dtext.trim())addD.mutate()}}><input value={dtitle} onChange={e=>setDtitle(e.target.value)} placeholder="Короткий заголовок"/><textarea value={dtext} onChange={e=>setDtext(e.target.value)} rows={4} placeholder="Что решили и почему"/><button disabled={!dtitle.trim()||!dtext.trim()}>Зафиксировать</button></form></Card></div><div className="grid two"><Card title="Встречи">{meet.isLoading?<Loading/>:meet.error?<ErrorBox error={meet.error}/>:meet.data!.length?meet.data!.map(m=><Row key={m.id} title={m.title} meta={fmtDate(m.meeting_date)}/>):<Empty>Встреч ещё нет.</Empty>}</Card><Card title="Решения">{dec.isLoading?<Loading/>:dec.error?<ErrorBox error={dec.error}/>:dec.data!.length?dec.data!.map(d=><Row key={d.id} title={d.title} meta={fmtDate(d.decision_date)}/>):<Empty>Решений ещё нет.</Empty>}</Card></div></Page>
}

const Repo=z.object({id:z.string().uuid(),full_name:z.string(),last_synced_at:z.string().nullable().optional(),last_sync_error:z.string().nullable().optional()}).passthrough()
function SettingsPage(){
 const qc=useQueryClient(),s=useQuery({queryKey:['settings'],queryFn:()=>api('/settings',{},Settings.nullable())}),members=useQuery({queryKey:['members'],queryFn:()=>api('/members',{},Members)}),repos=useQuery({queryKey:['repos'],queryFn:()=>api('/github/repositories',{},z.array(Repo))})
 const [project,setProject]=useState('Друк'),[description,setDescription]=useState(''),[landing,setLanding]=useState(''),[telegram,setTelegram]=useState(''),[repo,setRepo]=useState('')
 useEffect(()=>{if(s.data){setProject(s.data.project_name);setDescription(s.data.description||'');setLanding(s.data.landing_url||'');setTelegram(s.data.telegram_url||'')}},[s.data])
 const save=useMutation({mutationFn:()=>api('/settings',json('PATCH',{project_name:project,description,landing_url:landing||null,telegram_url:telegram||null,expected_updated_at:s.data?.updated_at}),Settings),onSuccess:()=>{void qc.invalidateQueries({queryKey:['settings']});void qc.invalidateQueries({queryKey:['dashboard']})}})
 const addRepo=useMutation({mutationFn:()=>api('/github/repositories',json('POST',{full_name:repo}),Repo),onSuccess:()=>{setRepo('');void qc.invalidateQueries({queryKey:['repos']})}})
 const sync=useMutation({mutationFn:(id:string)=>api(`/github/repositories/${id}/sync`,json('POST')),onSuccess:()=>void qc.invalidateQueries({queryKey:['repos']})})
 return <Page title="Настройки"><div className="grid two"><Card title="Проект"><form className="stack" onSubmit={e=>{e.preventDefault();save.mutate()}}><label>Название<input value={project} onChange={e=>setProject(e.target.value)}/></label><label>Описание<textarea rows={4} value={description} onChange={e=>setDescription(e.target.value)}/></label><label>Лендинг<input type="url" value={landing} onChange={e=>setLanding(e.target.value)} placeholder="https://…"/></label><label>Telegram<input type="url" value={telegram} onChange={e=>setTelegram(e.target.value)} placeholder="https://t.me/…"/></label><button disabled={save.isPending}>Сохранить</button></form></Card><Card title="Участники">{members.isLoading?<Loading/>:members.error?<ErrorBox error={members.error}/>:members.data!.map(m=><Row key={m.user_id} title={m.display_name}/>)}</Card></div><Card title="GitHub Issues"><form className="quick" onSubmit={e=>{e.preventDefault();if(repo.trim())addRepo.mutate()}}><input value={repo} onChange={e=>setRepo(e.target.value)} placeholder="owner/repository"/><button disabled={!repo.trim()}>Добавить</button></form>{repos.data?.map(r=><Row key={r.id} title={r.full_name} meta={r.last_sync_error?`Ошибка: ${r.last_sync_error}`:r.last_synced_at?`Синхронизировано ${new Date(r.last_synced_at).toLocaleString('ru-RU')}`:'Ещё не синхронизировано'}><button className="small secondary" onClick={()=>sync.mutate(r.id)}>Синхронизировать</button></Row>)}{repos.error&&<ErrorBox error={repos.error}/>}</Card><Card title="Сессия и данные"><div className="actions"><a className="button secondary" href="#" onClick={e=>{e.preventDefault();void api('/export').then(data=>{const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='druk-workspace.json';a.click();URL.revokeObjectURL(a.href)})}}>Экспорт JSON</a><button className="danger" onClick={()=>void supabase.auth.signOut()}>Выйти</button></div></Card></Page>
}
