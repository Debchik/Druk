from pathlib import Path
import base64

app = Path('frontend/src/App.tsx')
text = app.read_text()

# Dashboard: load all programs for an interactive deadline calendar.
old = "const q=useQuery<any>({queryKey:['dashboard-rich'],queryFn:async()=>{const [base,analytics,links,members]=await Promise.all([api('/dashboard'),api('/analytics'),api('/links'),api('/team')]);return {base,analytics,links,members}}});const qc=useQueryClient()"
new = "const q=useQuery<any>({queryKey:['dashboard-rich'],queryFn:async()=>{const [base,analytics,links,members,programs]=await Promise.all([api('/dashboard'),api('/analytics'),api('/links'),api('/team'),api('/programs')]);return {base,analytics,links,members,programs}}});const qc=useQueryClient()"
text = text.replace(old, new)
text = text.replace("const {base,analytics,links,members}=q.data;", "const {base,analytics,links,members,programs}=q.data;")

# Hero: keep both background and img rendering so it survives browser/layout regressions.
text = text.replace(
    '<div className="hero-visual"><img src={asset(\'hero-home.webp\')} alt=""/></div>',
    '<div className="hero-visual" style={{backgroundImage:`url(${asset(\'hero-home.webp\')})`}}><img src={asset(\'hero-home.webp\')} alt=""/></div>'
)

# Replace the cramped deadline table on the dashboard with a proper interactive calendar.
start = text.find('<Card title="Дедлайны программ" action={<Link to="/programs">Смотреть все →</Link>}>')
end_marker = '</Card></div>\n <Card title="Последние решения"'
if start != -1:
    end = text.find(end_marker, start)
    if end != -1:
        text = text[:start] + '<DeadlineCalendar programs={programs}/></div>\n <Card title="Последние решения"' + text[end + len(end_marker):]

calendar_component = r'''
function DeadlineCalendar({programs}:{programs:Program[]}){
 const todayStr=new Date().toISOString().slice(0,10),withDeadlines=programs.filter(p=>p.deadline&&!p.archived).sort((a,b)=>(a.deadline||'').localeCompare(b.deadline||''));
 const initial=withDeadlines.find(p=>(p.deadline||'')>=todayStr)?.deadline||withDeadlines[0]?.deadline||todayStr;
 const initialDate=new Date(initial+'T12:00:00');const [month,setMonth]=useState(()=>new Date(initialDate.getFullYear(),initialDate.getMonth(),1));const [selected,setSelected]=useState(initial);
 const year=month.getFullYear(),mon=month.getMonth(),days=new Date(year,mon+1,0).getDate(),offset=(new Date(year,mon,1).getDay()+6)%7;
 const key=`${year}-${String(mon+1).padStart(2,'0')}`;const deadlines=withDeadlines.filter(p=>p.deadline?.startsWith(key));const marked=new Map<number,Program[]>();deadlines.forEach(p=>{const d=Number(p.deadline!.slice(-2));marked.set(d,[...(marked.get(d)||[]),p])});
 const selectedPrograms=withDeadlines.filter(p=>p.deadline===selected);const monthName=month.toLocaleDateString('ru-RU',{month:'long',year:'numeric'});
 const choose=(d:number)=>setSelected(`${key}-${String(d).padStart(2,'0')}`);
 return <Card title="Календарь дедлайнов" action={<Link to="/programs">Все программы →</Link>}><div className="deadline-calendar"><div className="deadline-calendar-head"><button onClick={()=>setMonth(new Date(year,mon-1,1))}>‹</button><b>{monthName}</b><button onClick={()=>setMonth(new Date(year,mon+1,1))}>›</button></div><div className="deadline-weekdays">{['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].map(x=><span key={x}>{x}</span>)}</div><div className="deadline-days">{Array.from({length:offset}).map((_,i)=><span key={`e${i}`}/>) }{Array.from({length:days},(_,i)=>i+1).map(d=>{const date=`${key}-${String(d).padStart(2,'0')}`,count=marked.get(d)?.length||0;return <button key={d} className={cx(date===selected&&'selected',date===todayStr&&'today',count>0&&'has-deadline')} onClick={()=>choose(d)}><span>{d}</span>{count>0&&<i>{count}</i>}</button>})}</div><div className="deadline-day-details"><div className="deadline-selected-title"><b>{new Date(selected+'T12:00:00').toLocaleDateString('ru-RU',{day:'numeric',month:'long'})}</b><span>{selectedPrograms.length?`${selectedPrograms.length} дедлайн${selectedPrograms.length===1?'':'а'}`:'Нет дедлайнов'}</span></div>{selectedPrograms.length?<div className="deadline-events">{selectedPrograms.map(p=><Link to={`/programs/${p.id}`} key={p.id}><span className="deadline-dot"/><div><b>{p.name}</b><small>{p.next_step||'Открыть программу'}</small></div><Chip tone={p.deadline&&p.deadline<todayStr?'red':'amber'}>{p.deadline&&p.deadline<todayStr?'Просрочено':'Дедлайн'}</Chip></Link>)}</div>:<div className="deadline-empty">На этот день ничего не запланировано. Выберите день с зелёной точкой.</div>}</div></div></Card>
}
'''
if 'function DeadlineCalendar(' not in text:
    anchor = "function formatSeconds(n:number){if(!n)return '0 мин';const m=Math.floor(n/60),s=Math.round(n%60);return `${m} мин ${s} сек`}"
    text = text.replace(anchor, anchor + '\n' + calendar_component)

# Checklist: fix tiny text field, make checkbox optimistic, and make add action explicit.
old_add = "const addCheck=useMutation({mutationFn:()=>api(`/programs/${id}/checklist`,json('POST',{text:newCheck})),onSuccess:()=>{setNewCheck('');void qc.invalidateQueries({queryKey:['program-detail-rich',id]})}})"
new_add = "const addCheck=useMutation({mutationFn:()=>api(`/programs/${id}/checklist`,json('POST',{text:newCheck.trim()})),onSuccess:(created:any)=>{setNewCheck('');qc.setQueryData<any>(['program-detail-rich',id],(old:any)=>old?{...old,detail:{...old.detail,checklist:[...(old.detail.checklist||[]),created]}}:old)},onSettled:()=>void qc.invalidateQueries({queryKey:['program-detail-rich',id]})})"
text = text.replace(old_add, new_add)
old_check = "const check=useMutation({mutationFn:({cid,done}:{cid:string;done:boolean})=>api(`/checklist/${cid}`,json('PATCH',{done})),onSuccess:()=>void qc.invalidateQueries({queryKey:['program-detail-rich',id]})})"
new_check = "const check=useMutation({mutationFn:({cid,done}:{cid:string;done:boolean})=>api(`/checklist/${cid}`,json('PATCH',{done})),onMutate:async({cid,done})=>{await qc.cancelQueries({queryKey:['program-detail-rich',id]});const prev=qc.getQueryData<any>(['program-detail-rich',id]);qc.setQueryData<any>(['program-detail-rich',id],(old:any)=>old?{...old,detail:{...old.detail,checklist:(old.detail.checklist||[]).map((c:any)=>c.id===cid?{...c,done}:c)}}:old);return {prev}},onError:(_e,_v,ctx:any)=>{if(ctx?.prev)qc.setQueryData(['program-detail-rich',id],ctx.prev)},onSettled:()=>void qc.invalidateQueries({queryKey:['program-detail-rich',id]})})"
text = text.replace(old_check, new_check)
text = text.replace("onChange={()=>check.mutate({cid:c.id,done:!c.done})}", "onChange={e=>check.mutate({cid:c.id,done:e.target.checked})}")
old_form = '<form className="inline-form" onSubmit={e=>{e.preventDefault();if(newCheck.trim())addCheck.mutate()}}><input value={newCheck} onChange={e=>setNewCheck(e.target.value)} placeholder="Добавить пункт..."/><Button>＋</Button></form>'
new_form = '<form className="checklist-add-form" onSubmit={e=>{e.preventDefault();if(newCheck.trim())addCheck.mutate()}}><input className="checklist-new-input" value={newCheck} onChange={e=>setNewCheck(e.target.value)} placeholder="Например: заполнить форму заявки"/><Button disabled={!newCheck.trim()||addCheck.isPending}><Icon name="plus"/>{addCheck.isPending?\'Добавляем…\':\'Добавить\'}</Button></form>{(addCheck.error||check.error)&&<small className="checklist-error">Не удалось сохранить изменение. Попробуйте ещё раз.</small>}'
text = text.replace(old_form, new_form)

app.write_text(text)

css = Path('frontend/src/styles.css')
s = css.read_text()
s = s.replace('.checklist input{width:15px;height:15px;accent-color:#4a8435}', '.checklist input[type="checkbox"]{width:17px;height:17px;accent-color:#4a8435;cursor:pointer}')
marker = '/* dashboard-calendar-checklist-favicon-v1 */'
extra = r'''
/* dashboard-calendar-checklist-favicon-v1 */
.hero-visual{position:relative!important;min-width:0!important;min-height:100%!important;background-size:cover!important;background-position:center center!important;background-repeat:no-repeat!important}.hero-visual img{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;display:block!important;object-fit:cover!important;object-position:center center!important;opacity:1!important;visibility:visible!important}
.checklist label{cursor:pointer}.checklist label:hover{background:#f8faf7}.checklist-add-form{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid #edf0ed}.checklist-new-input{width:100%!important;height:42px!important;min-width:0!important;border-radius:10px!important;padding:10px 12px!important}.checklist-add-form .btn{height:42px;white-space:nowrap}.checklist-error{display:block;color:#c54040;font-size:9.5px;margin-top:7px}
.deadline-calendar{display:grid;grid-template-columns:minmax(250px,.82fr) minmax(280px,1.18fr);gap:14px}.deadline-calendar-head{grid-column:1;display:grid;grid-template-columns:34px 1fr 34px;align-items:center;text-align:center;margin-bottom:7px}.deadline-calendar-head button{width:32px;height:32px;border:1px solid #e1e6de;border-radius:8px;background:#fff;color:#4c5d4b;font-size:20px}.deadline-calendar-head b{text-transform:capitalize;font-size:13px}.deadline-weekdays,.deadline-days{grid-column:1;display:grid;grid-template-columns:repeat(7,1fr);gap:5px;text-align:center}.deadline-weekdays span{font-size:9px;color:#929791;padding:3px}.deadline-days button,.deadline-days>span{aspect-ratio:1;min-width:0;border:0;background:transparent;border-radius:9px;position:relative;display:grid;place-items:center;color:#37413a;font-size:10px}.deadline-days button:hover{background:#f0f6ed}.deadline-days button.selected{background:#3f7c2b;color:#fff}.deadline-days button.today:not(.selected){box-shadow:inset 0 0 0 1px #78a76a}.deadline-days button.has-deadline:not(.selected){background:#edf5e8;color:#2f6f24;font-weight:700}.deadline-days button i{position:absolute;right:2px;top:2px;min-width:13px;height:13px;border-radius:999px;background:#4b8a38;color:#fff;font-size:7px;font-style:normal;display:grid;place-items:center}.deadline-days button.selected i{background:#fff;color:#3f7c2b}.deadline-day-details{grid-column:2;grid-row:1/4;border-left:1px solid #edf0ec;padding-left:14px;min-width:0}.deadline-selected-title{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:9px}.deadline-selected-title b{font-size:13px}.deadline-selected-title span{font-size:9px;color:#858c87}.deadline-events{display:grid;gap:7px}.deadline-events a{display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:8px;align-items:center;text-decoration:none;border:1px solid #e6e9e4;border-radius:9px;padding:9px;background:#fff}.deadline-events a:hover{background:#f9fbf8}.deadline-events a>div{display:grid;gap:2px}.deadline-events b{font-size:10.5px}.deadline-events small{font-size:9px;color:#838a85}.deadline-dot{width:8px;height:8px;border-radius:50%;background:#4d8937}.deadline-empty{border:1px dashed #dfe5dc;border-radius:9px;padding:18px;color:#8a918c;font-size:10px;line-height:1.45;text-align:center}
@media(max-width:1180px){.deadline-calendar{grid-template-columns:1fr}.deadline-day-details{grid-column:1;grid-row:auto;border-left:0;border-top:1px solid #edf0ec;padding-left:0;padding-top:12px}.deadline-calendar-head,.deadline-weekdays,.deadline-days{grid-column:1}}
@media(max-width:680px){.checklist-add-form{grid-template-columns:1fr}.checklist-add-form .btn{width:100%}}
'''
if marker not in s:
    s += '\n' + extra
css.write_text(s)

# Use the generated transparent Druk as a real favicon.
fav = Path('frontend/public/favicon.png')
fav.write_bytes(base64.b64decode(Path('scripts/favicon.b64').read_text().strip()))
index = Path('frontend/index.html')
h = index.read_text()
h = h.replace('type="image/webp" href="%BASE_URL%druk.webp"', 'type="image/png" href="%BASE_URL%favicon.png"')
h = h.replace('href="%BASE_URL%druk.webp"', 'href="%BASE_URL%favicon.png"')
index.write_text(h)
