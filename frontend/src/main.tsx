import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, dehydrate, hydrate } from '@tanstack/react-query'
import { HashRouter } from 'react-router-dom'
import App from './App'
import { supabase } from './lib/supabase'
import { prefetchWorkspace } from './lib/prefetch'
import { applyGeneratedArtwork } from './generatedArtwork'
import './styles.css'
import './artwork.css'
import './stability.css'
import './generated-art.css'

applyGeneratedArtwork()

const CACHE_MAX_AGE=24*60*60_000
const CACHE_PREFIX='druk-query-cache:v4:'
const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:5*60_000,gcTime:CACHE_MAX_AGE,refetchOnWindowFocus:false,refetchOnReconnect:true,retry:(n,e)=>{const status=(e as {status?:number}).status;return (!status||![401,403,404,409,422].includes(status))&&n<2}}}})
let activeUser:string|null=null
let saveTimer:number|undefined

function restore(uid:string){
  try{
    const raw=localStorage.getItem(CACHE_PREFIX+uid);if(!raw)return
    const cached=JSON.parse(raw);if(!cached?.savedAt||Date.now()-cached.savedAt>CACHE_MAX_AGE){localStorage.removeItem(CACHE_PREFIX+uid);return}
    hydrate(queryClient,cached.state)
  }catch{localStorage.removeItem(CACHE_PREFIX+uid)}
}
function persist(){
  if(!activeUser)return
  try{localStorage.setItem(CACHE_PREFIX+activeUser,JSON.stringify({savedAt:Date.now(),state:dehydrate(queryClient)}))}catch{/* cache is an optimization only */}
}
queryClient.getQueryCache().subscribe(()=>{
  if(!activeUser)return
  if(saveTimer)window.clearTimeout(saveTimer)
  saveTimer=window.setTimeout(persist,300)
})

async function bootstrap(){
  const {data:{session}}=await supabase.auth.getSession()
  if(session){activeUser=session.user.id;restore(activeUser)}

  supabase.auth.onAuthStateChange((event,next)=>{
    const nextUser=next?.user.id||null
    if(event==='SIGNED_OUT'){
      if(activeUser)localStorage.removeItem(CACHE_PREFIX+activeUser)
      activeUser=null
      return
    }
    if(nextUser&&nextUser!==activeUser){activeUser=nextUser;restore(nextUser);prefetchWorkspace(queryClient)}
  })

  createRoot(document.getElementById('root')!).render(
    <StrictMode><QueryClientProvider client={queryClient}><HashRouter><App queryClient={queryClient}/></HashRouter></QueryClientProvider></StrictMode>,
  )
  if(session)prefetchWorkspace(queryClient)
}

void bootstrap()
