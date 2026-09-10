export function weekStart(d=new Date()) { const x=new Date(d); const day=(x.getDay()+6)%7; x.setDate(x.getDate()-day); return x.toISOString().slice(0,10) }
export const fmtDate=(v?:string|null)=>v?new Intl.DateTimeFormat('ru-RU').format(new Date(`${v}T00:00:00`)):'—'
