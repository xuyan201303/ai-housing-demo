import { useEffect, useState } from 'react'
import Customer from './Customer'
import Admin from './Admin'
import Staff from './Staff'
import { api, errorText } from './api'
import type { Json } from './api'
export function Icon({ name, size = 20 }: { name: string, size?: number }) {
  const paths: Record<string,string> = {home:'M3 11l9-8 9 8M5 9v12h14V9M9 21v-8h6v8',arrow:'M5 12h14m-6-6 6 6-6 6',mic:'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3ZM5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8',chat:'M21 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 19 0Z',file:'M6 2h8l5 5v15H6ZM14 2v6h5M9 12h7m-7 4h7',check:'m5 12 4 4L19 6',people:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM20 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8',clock:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM12 7v5l3 2',send:'m22 2-7 20-4-9L2 9 22 2ZM22 2 11 13',upload:'M12 16V3m-5 5 5-5 5 5M3 16v5h18v-5',lock:'M6 10h12v11H6ZM8 10V6a4 4 0 0 1 8 0v4',close:'m6 6 12 12M6 18 18 6',money:'M3 6h18v12H3ZM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM6 9v6m12-6v6',location:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM12 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z'}
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.file}/></svg>
}
export function Brand({ dark = false }: { dark?: boolean }) { return <a className={`brand ${dark ? 'dark' : ''}`} href="/"><span className="brand-mark"><Icon name="home" size={23}/></span><span>SANZO<span className="brand-sub">HOUSING CONCIERGE</span></span></a> }
export function Alert({ message, tone = 'error' }: { message: string, tone?: 'error'|'info'|'success' }) { return message ? <div className={`alert ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>{message}</div> : null }
export function SourceList({ references = [] }: { references?: Json[] }) {
  const unique = references.filter((ref,index,refs) => refs.findIndex(r => `${r.document_id}-${r.filename}-${r.location}` === `${ref.document_id}-${ref.filename}-${ref.location}`) === index)
  if (!unique.length) return null
  return <div className="sources"><span>参照資料</span>{unique.map((ref,index) => <div key={index} className="source"><Icon name="file" size={14}/><span>{ref.filename || ref.source_name || '確認済み資料'}{ref.location && <small> · {ref.location}</small>}</span>{ref.source_url && <a href={ref.source_url} target="_blank" rel="noreferrer">原情報 ↗</a>}</div>)}</div>
}
export function Protected({ role, children }: {role:'admin'|'staff',children:(auth:string, logout:()=>void)=>React.ReactNode}) {
  const [auth,setAuth] = useState('')
  const [password,setPassword] = useState('')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  async function login(event:React.FormEvent) {
    event.preventDefault(); setBusy(true);setError('')
    const credential = btoa(`${role}:${password}`)
    try { await api(role === 'admin' ? '/admin/documents' : '/staff/calls', {}, undefined, credential);setAuth(credential);setPassword('') }
    catch(error) {setError(errorText(error))} finally {setBusy(false)}
  }
  if(auth) return children(auth,()=>setAuth(''))
  return <div className="login-shell"><Brand/><form className="login-card" onSubmit={login}><span className="eyebrow">SANZO DEMO / {role.toUpperCase()}</span><span className="login-icon"><Icon name="lock" size={27}/></span><h1>{role === 'admin' ? '管理者ログイン' : 'スタッフログイン'}</h1><p>資料の管理・接客対応にはアクセス認証が必要です。</p><label>パスワード<input type="password" autoComplete="current-password" value={password} onChange={event=>setPassword(event.target.value)} required autoFocus/></label><Alert message={error}/><button className="button primary wide" disabled={busy}>{busy ? '認証しています…' : 'ログイン'}<Icon name="arrow" size={17}/></button><a className="back-link" href="/">お客様ページに戻る</a></form></div>
}
export default function App() {
  const [health,setHealth]=useState<Json|null>(null)
  const [error,setError]=useState('')
  useEffect(()=>{api<Json>('/health').then(setHealth).catch(error=>setError(errorText(error)))},[])
  const isolationNotice=health?.demo_mode==='test'?<aside role="note" style={{padding:'10px 20px',background:'#fff4d8',borderBottom:'1px solid #e6d4a3',color:'#65521f',fontSize:12,lineHeight:1.7}}><strong>隔離検証データ / TEST</strong> — 通常運用データではありません。Customer の文字回答は実資料と業務Toolsを読む TEST provider です。実AI・日本語音声の検証ではありません。接客は「文字で開始」を使用してください。</aside>:null
  if(location.pathname.startsWith('/admin')) return <>{isolationNotice}<Protected role="admin">{(auth,logout)=><Admin auth={auth} logout={logout} health={health}/>}</Protected></>
  if(location.pathname.startsWith('/staff')) return <>{isolationNotice}<Protected role="staff">{(auth,logout)=><Staff auth={auth} logout={logout}/>}</Protected></>
  return <>{isolationNotice}<Customer health={health} connectionError={error}/></>
}
