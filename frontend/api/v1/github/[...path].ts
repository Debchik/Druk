import { createClient } from '@supabase/supabase-js'

const supabaseUrl=process.env.SUPABASE_URL||process.env.VITE_SUPABASE_URL
const publishableKey=process.env.SUPABASE_PUBLISHABLE_KEY||process.env.VITE_SUPABASE_PUBLISHABLE_KEY
const githubToken=process.env.GITHUB_TOKEN

function error(res:any,status:number,code:string,message:string,details:any={}){return res.status(status).json({error:{code,message,details}})}

async function ctx(req:any,res:any){
  const auth=String(req.headers.authorization||'')
  if(!auth.toLowerCase().startsWith('bearer '))return {response:error(res,401,'UNAUTHENTICATED','Требуется вход')}
  if(!supabaseUrl||!publishableKey)return {response:error(res,500,'SERVER_CONFIG','Supabase не настроен на Vercel')}
  const token=auth.slice(7)
  const supabase=createClient(supabaseUrl,publishableKey,{global:{headers:{Authorization:auth}},auth:{persistSession:false,autoRefreshToken:false}})
  const {data:{user},error:userError}=await supabase.auth.getUser(token)
  if(userError||!user)return {response:error(res,401,'INVALID_SESSION','Сессия недействительна')}
  const {data:members,error:memberError}=await supabase.from('workspace_members').select('workspace_id').eq('user_id',user.id).limit(2)
  if(memberError)return {response:error(res,500,'SUPABASE_ERROR',memberError.message)}
  if(!members?.length)return {response:error(res,403,'NOT_A_MEMBER','Нет доступа к рабочему пространству')}
  if(members.length>1)return {response:error(res,409,'MULTIPLE_WORKSPACES','Пользователь состоит более чем в одном workspace')}
  return {supabase,user,workspaceId:members[0].workspace_id}
}

async function githubIssues(fullName:string){
  if(!githubToken)throw new Error('GITHUB_TOKEN is not configured')
  const rows:any[]=[]
  for(let page=1;page<=10;page++){
    const response=await fetch(`https://api.github.com/repos/${fullName}/issues?state=all&per_page=100&page=${page}`,{headers:{Authorization:`Bearer ${githubToken}`,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Druk-Internal'}})
    if(!response.ok)throw new Error(`GitHub ${response.status}: ${await response.text()}`)
    const chunk=await response.json();rows.push(...chunk.filter((x:any)=>!x.pull_request));if(chunk.length<100)break
  }
  return rows
}

export default async function handler(req:any,res:any){
  res.setHeader('Cache-Control','no-store')
  const context=await ctx(req,res);if(context.response)return context.response
  const {supabase,user,workspaceId}=context
  const path=Array.isArray(req.query.path)?req.query.path:[req.query.path].filter(Boolean)
  try{
    if(path.length===1&&path[0]==='repositories'){
      if(req.method==='GET'){
        const {data,error:e}=await supabase.from('github_repositories').select('*').eq('workspace_id',workspaceId).order('created_at',{ascending:false});if(e)throw e;return res.status(200).json(data)
      }
      if(req.method==='POST'){
        const fullName=String(req.body?.full_name||'').trim();if(!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(fullName))return error(res,422,'INVALID_REPOSITORY','Укажите репозиторий в формате owner/name')
        const {data,error:e}=await supabase.from('github_repositories').insert({workspace_id:workspaceId,full_name:fullName,created_by:user.id}).select().single();if(e)throw e;return res.status(201).json(data)
      }
    }
    if(path.length===1&&path[0]==='issues'&&req.method==='GET'){
      const {data,error:e}=await supabase.from('github_issues').select('*').eq('workspace_id',workspaceId).order('github_updated_at',{ascending:false}).limit(500);if(e)throw e;return res.status(200).json(data)
    }
    if(path.length===3&&path[0]==='repositories'&&path[2]==='sync'&&req.method==='POST'){
      const repoId=path[1]
      const {data:repo,error:repoError}=await supabase.from('github_repositories').select('*').eq('id',repoId).eq('workspace_id',workspaceId).maybeSingle();if(repoError)throw repoError;if(!repo)return error(res,404,'NOT_FOUND','Репозиторий не найден')
      try{
        const issues=await githubIssues(repo.full_name)
        if(issues.length){
          const payload=issues.map((issue:any)=>({workspace_id:workspaceId,repository_id:repo.id,github_id:issue.id,number:issue.number,title:issue.title,state:issue.state,url:issue.html_url,assignee:issue.assignee?.login||null,labels:(issue.labels||[]).map((l:any)=>typeof l==='string'?l:{name:l.name,color:l.color}),github_updated_at:issue.updated_at}))
          const {error:e}=await supabase.from('github_issues').upsert(payload,{onConflict:'repository_id,number'});if(e)throw e
        }
        const now=new Date().toISOString();const {error:e}=await supabase.from('github_repositories').update({last_synced_at:now,last_sync_error:null}).eq('id',repo.id).eq('workspace_id',workspaceId);if(e)throw e
        return res.status(200).json({synced:issues.length,last_synced_at:now})
      }catch(e:any){await supabase.from('github_repositories').update({last_sync_error:String(e?.message||e).slice(0,1000)}).eq('id',repo.id).eq('workspace_id',workspaceId);throw e}
    }
    return error(res,404,'NOT_FOUND','Маршрут не найден')
  }catch(e:any){return error(res,500,e?.code||'SERVER_ERROR',e?.message||'Ошибка серверной функции')}
}
