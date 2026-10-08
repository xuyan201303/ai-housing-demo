import { Icon } from './App'
import type { CustomerSource } from './customerTypes'

export default function CustomerSources({references=[]}:{references?:CustomerSource[]}) {
  const unique=references.filter((ref,index,all)=>all.findIndex(r=>r.label===ref.label && r.url===ref.url)===index)
  if(!unique.length)return null
  return <div className="sources"><span>参照資料</span>{unique.map((ref,index)=><div key={index} className="source"><Icon name="file" size={14}/><span>{ref.label}</span>{ref.url&&<a href={ref.url} target="_blank" rel="noreferrer">原情報 ↗</a>}</div>)}</div>
}
