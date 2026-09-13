import type { QueryClient } from '@tanstack/react-query'
import { api } from './api'

const prefetch = (qc: QueryClient, queryKey: readonly unknown[], queryFn: () => Promise<unknown>) =>
  qc.prefetchQuery({ queryKey, queryFn, staleTime: 5 * 60_000 }).catch(() => undefined)

export function prefetchWorkspace(qc: QueryClient) {
  const jobs = [
    () => prefetch(qc, ['me'], () => api('/me')),
    () => prefetch(qc, ['topbar-attention'], async () => {
      const [tasks, programs, events] = await Promise.all([
        api('/tasks?include_done=false'), api('/programs'), api('/events'),
      ])
      return { tasks, programs, events }
    }),
    () => prefetch(qc, ['dashboard-rich'], async () => {
      const [base, analytics, links, members, programs] = await Promise.all([
        api('/dashboard'), api('/analytics'), api('/links'), api('/team'), api('/programs'),
      ])
      return { base, analytics, links, members, programs }
    }),
    () => prefetch(qc, ['tasks-rich', false, false], async () => {
      const [tasks, members, issues] = await Promise.all([
        api('/tasks?mine=false&include_done=false'), api('/team'), api('/github/issues'),
      ])
      return { tasks, members, issues }
    }),
    () => prefetch(qc, ['programs-rich'], async () => {
      const [programs, events] = await Promise.all([api('/programs?include_archived=true'), api('/events')])
      return { programs, events }
    }),
    () => prefetch(qc, ['events-rich'], async () => {
      const [events, programs, members] = await Promise.all([api('/events'), api('/programs'), api('/team')])
      return { events, programs, members }
    }),
    () => prefetch(qc, ['files-rich'], async () => {
      const [files, settings, programs] = await Promise.all([api('/files'), api('/settings'), api('/programs')])
      return { files, settings, programs }
    }),
    () => prefetch(qc, ['answers-rich', ''], async () => {
      const [answers, programs] = await Promise.all([api('/answers'), api('/programs')])
      return { answers, programs }
    }),
    () => prefetch(qc, ['settings-rich'], async () => {
      const [settings, members, links, repos, invites] = await Promise.all([
        api('/settings'), api('/team'), api('/links'), api('/github/repositories'), api('/invites'),
      ])
      return { settings, members, links, repos, invites }
    }),
  ]

  // Warm the current shell first, then fill the rest of the app without blocking first paint.
  void Promise.all(jobs.slice(0, 3).map(job => job())).finally(() => {
    const run = () => jobs.slice(3).reduce((p, job) => p.then(() => job()), Promise.resolve())
    if ('requestIdleCallback' in window) (window as any).requestIdleCallback(run, { timeout: 1500 })
    else window.setTimeout(run, 250)
  })
}
