export type Json = Record<string, any>
export class ApiError extends Error {
  status: number
  code: string
  fieldErrors: Record<string, string>
  constructor(status: number, code: string, message: string, fieldErrors: Record<string, string> = {}) { super(message); this.status = status; this.code = code; this.fieldErrors = fieldErrors }
}
export async function api<T = any>(path: string, options: RequestInit = {}, token?: string, auth?: string): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('X-Session-Token', token)
  if (auth) headers.set('Authorization', `Basic ${auth}`)
  let response: Response
  try { response = await fetch(`/api${path}`, { ...options, headers }) }
  catch { throw new ApiError(0, 'NETWORK_ERROR', 'サーバーに接続できません。起動状態と接続をご確認ください。') }
  const contentType = response.headers.get('content-type') || ''
  const data = contentType.includes('json') ? await response.json() : await response.text()
  if (!response.ok) throw new ApiError(response.status, data?.error?.code || 'API_ERROR', data?.error?.message || (typeof data?.detail === 'string' ? data.detail : Array.isArray(data?.detail) ? '入力内容を確認してください。必須項目または形式に誤りがあります。' : `リクエストに失敗しました (${response.status})`), data?.error?.field_errors || {})
  return data as T
}
export const post = (body?: unknown): RequestInit => ({ method: 'POST', ...(body === undefined ? {} : { body: JSON.stringify(body) }) })
export const errorText = (error: unknown) => error instanceof Error ? error.message : '処理に失敗しました。'
export const fmtMoney = (value: unknown) => Number.isFinite(Number(value)) && value !== null && value !== '' ? `${new Intl.NumberFormat('ja-JP').format(Number(value))} 円` : '資料をご確認ください'
export const fmtDate = (value: unknown) => value ? new Date(String(value)).toLocaleString('ja-JP', {year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) : '—'
