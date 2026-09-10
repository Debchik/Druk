import { z } from 'zod'
import { env, supabase } from './supabase'

export class ApiError extends Error {
  status: number
  code: string
  details: unknown
  constructor(status: number, code: string, message: string, details: unknown = {}) {
    super(message); this.status=status; this.code=code; this.details=details
  }
}

export async function api<T>(path: string, init: RequestInit = {}, schema?: z.ZodType<T>): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new ApiError(401, 'UNAUTHENTICATED', 'Требуется вход')
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type','application/json')
  const res = await fetch(`${env.VITE_API_URL}${path}`, {...init, headers})
  if (res.status === 204) return undefined as T
  const payload: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const e = payload as {error?:{code?:string;message?:string;details?:unknown}} | null
    throw new ApiError(res.status, e?.error?.code || 'API_ERROR', e?.error?.message || 'Ошибка запроса', e?.error?.details)
  }
  if (!schema) return payload as T
  const parsed = schema.safeParse(payload)
  if (!parsed.success) throw new ApiError(502,'INVALID_API_RESPONSE','Сервер вернул данные неожиданного формата',parsed.error.flatten())
  return parsed.data
}

export const json = (method: string, body?: unknown): RequestInit => ({method, body: body === undefined ? undefined : JSON.stringify(body)})
