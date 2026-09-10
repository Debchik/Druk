import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './styles.css'

const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:15000,retry:(n,e)=>{const status=(e as {status?:number}).status;return !status||![401,403,422].includes(status)&&n<2}}}})
createRoot(document.getElementById('root')!).render(<StrictMode><QueryClientProvider client={queryClient}><HashRouter><App queryClient={queryClient}/></HashRouter></QueryClientProvider></StrictMode>)
