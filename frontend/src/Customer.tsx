import { useEffect, useRef, useState } from 'react'
import { Alert, Brand, Icon } from './App'
import SourceList from './CustomerSources'
import { api, errorText, fmtMoney, post } from './api'
import type { Json } from './api'
import type { CustomerSessionCreated, CustomerSessionWithToken, CustomerSession, CustomerAnswer, CustomerMessage, CustomerProperty, CustomerCandidate, CustomerStaffCall, MortgageDisplay, SourcesDisplay } from './customerTypes'
import Mortgage from './Mortgage'
import useVoice from './useVoice'
import Avatar from './Avatar'

const suggestions = ['住宅購入は何から始めればいいですか？', '購入前に確認することは？', '住宅ローンについて相談したい']
const stateLabels: Record<string,string> = {idle:'ご案内をお待ちしています',listening:'お話を伺っています',thinking:'確認しています',speaking:'ご案内しています'}
function textOf(message:{text?:string}) { return String(message.text ?? '') }
function PropertyIllustration() {
  return <div className="property-illustration"><svg viewBox="0 0 500 300" role="img" aria-label="住宅を表現したオリジナルイメージ"><defs><linearGradient id="sky" x2="0" y2="1"><stop stopColor="#e9eee5"/><stop offset="1" stopColor="#f7f5ed"/></linearGradient></defs><rect width="500" height="300" fill="url(#sky)"/><circle cx="401" cy="66" r="35" fill="#e4d8b9"/><path d="M0 247Q95 213 202 242T500 226V300H0" fill="#d6decd"/><path d="M75 205V100l152-44 121 52v143H75" fill="#f8f5ea"/><path d="m58 101 168-57 141 61-10 15L226 63 65 118" fill="#536255"/><path d="M226 63v186h122V108" fill="#e7e0cd"/><path d="M97 142h84v79H97" fill="#889b96"/><path d="M139 142v79M97 183h84" stroke="#eeeee2" strokeWidth="6"/><path d="M260 138h52v38h-52" fill="#8fa19a"/><path d="M282 138v38" stroke="#eeeee2" strokeWidth="5"/><path d="M255 194h31v55h-31" fill="#7d7766"/><path d="M75 252h291" stroke="#b0aa94" strokeWidth="9"/><path d="m290 260 61 40h77l-72-40" fill="#ece7d9"/><path d="M404 263V151" stroke="#73816a" strokeWidth="7"/><ellipse cx="405" cy="159" rx="39" ry="54" fill="#9dac8d"/><ellipse cx="43" cy="230" rx="29" ry="29" fill="#aebba0"/><ellipse cx="371" cy="248" rx="25" ry="17" fill="#a2b196"/></svg><span>表示イメージ／実際の物件とは異なります。</span></div>
}
function PropertyPanel({property,version,topic,setTopic}:{property:CustomerProperty,version:number|null,topic:string,setTopic:(topic:string)=>void}) {
    const equipment:string[]=Array.isArray(property.equipment)?property.equipment:property.equipment?[String(property.equipment)]:[]
  const surroundings:string[]=Array.isArray(property.surroundings)?property.surroundings:property.surroundings?[String(property.surroundings)]:[]
  const notes=(property.scope_notices || []).map(text=>({text}))
  const transportNotes=notes.filter(note=>/駅|徒歩|距離/.test(note.text))
  const fieldReference=(_field:string)=>property.references || []
  return <section className="property-panel">
    <div className="section-heading"><div><span className="eyebrow">YOUR NEXT HOME</span><h2>{property.property_name || '公開資料の準備中'}</h2></div><span className="version-tag">公開版 v{version}</span></div>
    <PropertyIllustration/>
    <>
      <div className="property-summary"><div><span className="muted-label">販売価格</span><strong>{fmtMoney(property.price)}</strong></div><div className="layout-summary"><span className="muted-label">間取り</span><strong>{property.layout || '記載なし'}</strong></div></div>
      <div className="property-address"><Icon name="location" size={17}/>{property.address || '住所は確認済み資料をご参照ください'}</div>
      <div className="tabs" role="tablist" aria-label="物件資料"><button role="tab" aria-selected={topic==='overview'} className={topic==='overview'?'active':''} onClick={()=>setTopic('overview')}>物件概要</button><button role="tab" aria-selected={topic==='equipment'} className={topic==='equipment'?'active':''} onClick={()=>setTopic('equipment')}>設備・周辺</button><button role="tab" aria-selected={topic==='sources'} className={topic==='sources'?'active':''} onClick={()=>setTopic('sources')}>参照資料</button></div>
      {topic==='overview'&&<dl className="property-facts">
        <div><dt>交通</dt><dd>{property.station || '記載なし'}{property.walking_minutes != null&&` 徒歩 ${property.walking_minutes} 分`}{transportNotes.map((note,index)=><p className="transport-scope-note" key={index}>{note.text}</p>)}<SourceList references={fieldReference('station')}/></dd></div>
        <div><dt>土地面積</dt><dd>{property.land_area != null?`${property.land_area} ㎡`:'記載なし'}</dd></div>
        <div><dt>建物面積</dt><dd>{property.building_area != null?`${property.building_area} ㎡`:'記載なし'}</dd></div>
        <div><dt>完成時期</dt><dd>{property.completion_date || '記載なし'}</dd></div>
        <div><dt>駐車場</dt><dd>{property.parking || '記載なし'}</dd></div>
      </dl>}
      {topic==='equipment'&&<div className="knowledge-list">
        <h3>確認済みの設備</h3>
        {equipment.length?<ul className="friendly-fact-list">{equipment.map((item,index)=><li key={index}><Icon name="check" size={13}/><span>{item}</span></li>)}</ul>:<p>設備の詳細は資料をご確認ください。</p>}
        <SourceList references={fieldReference('equipment')}/>
        <h3>周辺環境</h3>
        {surroundings.length?<ul className="friendly-fact-list surroundings-list">{surroundings.map((item,index)=><li key={index}><Icon name="location" size={14}/><span>{item}</span></li>)}</ul>:<p>周辺環境の詳細は、担当スタッフにご確認ください。</p>}
        {transportNotes.map((note,index)=><p className="transport-scope-note" key={index}>{note.text}</p>)}
        <SourceList references={fieldReference('surroundings')}/>
        {notes.filter(note=>!/駅|徒歩|距離/.test(note.text)).map((note,index)=><p className="small-note" key={index}>{note.text}</p>)}
      </div>}
      {topic==='sources'&&<div className="source-detail"><p className="small-note">管理者が確認・公開した資料を基にご案内します。</p><SourceList references={property.references || []}/><dl className="property-facts"><div><dt>確認日</dt><dd>{property.checked_at || '記載なし'}</dd></div><div><dt>有効期限</dt><dd>{property.valid_until || '記載なし'}</dd></div></dl>{notes.map((note,index)=><p className="small-note" key={index}>{note.text}</p>)}</div>}
    </>
  </section>
}
export default function Customer({health,connectionError}:{health:Json|null,connectionError:string}) {
  const [materials,setMaterials]=useState('')
  const materialEvent=useRef<number|undefined>(undefined)
  const [offers,setOffers]=useState<CustomerCandidate[]>([])
  const [session,setSession]=useState<CustomerSessionWithToken|null>(null)
  const [messages,setMessages]=useState<Array<Partial<CustomerMessage> & {pending?:boolean}>>([])
  const [error,setError]=useState('')
  const [busy,setBusy]=useState(false)
  const [text,setText]=useState('')
  const [topic,setTopic]=useState('overview')
  const [calling,setCalling]=useState(false)
  const [callReason,setCallReason]=useState('住宅購入について相談したい')
  const [staffOpen,setStaffOpen]=useState(false)
  const bottom=useRef<HTMLDivElement>(null)
  const closing=useRef(false)
  const voice=useVoice()
  const state=busy?'thinking':session?.mode==='voice'?voice.state:'idle'
  const property=session?.property || null
  const boundaryReady=health?.knowledge_boundary_version===2
  useEffect(()=>{
    const event=session?.display_events?.at(-1)
    if(!event || event.event_id===materialEvent.current)return
    materialEvent.current=event.event_id
    if(event.kind==='properties'){setOffers(event.properties);setMaterials('offers')}
    else setMaterials(event.kind==='mortgage' || event.kind==='products'?'loan':event.kind==='property' && property?'property':'sources')
  },[session?.display_events,property])
  const materialMessage=useRef<number|undefined>(undefined)
  useEffect(()=>{
    const answers=messages.filter(m=>m.role==='assistant')
    const message=answers.at(-1)
    if(!message?.event_id || materialMessage.current===message.event_id)return
    materialMessage.current=message.event_id
    if(!message.references?.length)return
    const previous=answers.at(-2)?.event_id || 0
    const linked=session?.display_events?.filter(e=>e.event_id>previous && e.event_id<message.event_id!).at(-1)
    if(session?.display_events?.some(e=>e.event_id>message.event_id! && ['mortgage','products'].includes(e.kind)))return
    if(linked?.kind==='mortgage'){setMaterials('loan');return}
    const question=textOf([...messages].reverse().find(m=>m.role==='user') || {})
    if(property && /価格|値段|設備|周辺|学校|駅|間取り|面積/.test(question) && !/ローン|返済|借入|金利|頭金/.test(question)){
      if(/設備|周辺|学校|近く/.test(question))setTopic('equipment')
      setMaterials('property');return
    }
    if(linked?.kind==='products'){setMaterials('loan');return}
    if(property && /号地|価格|設備|駅|面積/.test(message.text || '')){
      if(/設備|周辺|学校|近く/.test(message.text || ''))setTopic('equipment')
      setMaterials('property')
    }else setMaterials('sources')
  },[messages,session?.display_events,property])
  async function chooseProperty(id:string){if(!session)return;try{const data=await api<CustomerSession>(`/sessions/${session.id}/property`,post({property_id:id}),session.token);setSession(current=>current?({...current,...data}):null);setMaterials('property');setOffers([])}catch(error){setError(errorText(error))}}
  useEffect(()=>{
    if(!session?.id || session.status==='ended')return
    let alive=true
    const refresh=()=>{
      if(closing.current)return
      return api<CustomerSession>(`/sessions/${session.id}`,{},session.token).then(data=>{
      if(!alive || closing.current)return
      setMessages(data.messages || [])
      if(session.mode==='voice' && ['error','disconnected','closed'].includes(data.realtime?.status)){
        voice.stop();setError(data.realtime?.error?.message || '音声のサーバー制御接続が切れました。接客を終了して再接続してください。')
        api(`/sessions/${session.id}/end`,post(),session.token).catch(()=>{});setSession(null);return
      }
      setSession(current=>current && current.id===session.id?({...current,...data,token:current.token}):current)
    }).catch(error=>{if(alive && !closing.current)setError(errorText(error))})
    }
    const timer=setInterval(refresh,2000)
    return()=>{alive=false;clearInterval(timer)}
  },[session?.id,session?.mode,session?.status,session?.token,voice.stop])
  useEffect(()=>{
    if(closing.current || !voice.error || voice.status!=='error' || !session || session.mode!=='voice' || busy)return
    setError(voice.error);voice.stop()
    api(`/sessions/${session.id}/end`,post(),session.token).catch(error=>setError(`${voice.error} ${errorText(error)}`));setSession(null)
  },[voice.error,voice.status,session?.id,busy,voice.stop])
  useEffect(()=>{
    const last=messages[messages.length-1]
    if(last && /設備|周辺|学校|近く/.test(textOf(last)))setTopic('equipment')
  },[messages.length])
  useEffect(()=>{
    if(!session?.id)return
    const finishOnLeave=()=>{voice.stop();fetch(`/api/sessions/${session.id}/end`,{method:'POST',headers:{'X-Session-Token':session.token},keepalive:true}).catch(()=>{})}
    window.addEventListener('pagehide',finishOnLeave)
    return()=>window.removeEventListener('pagehide',finishOnLeave)
  },[session?.id,session?.token,voice.stop])
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth',block:'nearest'})},[messages.length,busy])
  async function startText() {setBusy(true);setError('');try{const data=await api<CustomerSessionCreated>('/sessions',post({mode:'text'}));setSession(data);setMessages(data.messages || []);setMaterials('');materialEvent.current=undefined;setTopic('overview')}catch(error){setError(errorText(error))}finally{setBusy(false)}}
  async function startVoice(){
    setBusy(true);setError('');let created:CustomerSessionWithToken|null=null;let microphone:MediaStream|null=null
    try{
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('マイクの利用には Chrome の localhost または HTTPS 接続が必要です。')
      microphone=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false})
      created=await api<CustomerSessionCreated>('/sessions',post({mode:'voice'}));setSession(created);setMessages([]);setMaterials('');materialEvent.current=undefined;setTopic('overview')
      await voice.connect(created,microphone)
    }catch(error){
      microphone?.getTracks().forEach(track=>track.stop());voice.stop()
      if(created)await api(`/sessions/${created.id}/end`,post(),created.token).catch(()=>{})
      setSession(null)
      setError(error instanceof DOMException && error.name==='NotAllowedError'?'マイクの利用が許可されませんでした。「文字で開始」からご相談いただけます。':errorText(error))
    }finally{setBusy(false)}
  }
  async function send(value:string) {if(!session || busy || !value.trim())return;setBusy(true);setError('');const question=value.trim();setText('');setMessages(current=>[...current,{role:'user',text:question,pending:true}]);try{const data=await api<CustomerAnswer>(`/sessions/${session.id}/messages`,post({text:question}),session.token);setMessages(current=>[...current,{role:'assistant',text:data.answer,references:data.references}]);const refreshed=await api<CustomerSession>(`/sessions/${session.id}`,{},session.token);setSession(current=>current?({...current,...refreshed}):null);setMessages(refreshed.messages || []);if(/設備|周辺|学校|近く/.test(question))setTopic('equipment');if(data.references?.length)setMaterials('sources')}catch(error){setError(errorText(error))}finally{setBusy(false)}}
  async function end() {
    if(!session || closing.current)return
    closing.current=true;setBusy(true);voice.silence()
    try{
      await api(`/sessions/${session.id}/end`,post(),session.token)
      voice.stop();setSession(null);setMessages([]);setMaterials('');setOffers([]);setText('');setError('')
    }catch(error){
      voice.stop();setError(`接客の終了を確認できませんでした。音声は停止しました。${errorText(error)}`)
    }finally{closing.current=false;setBusy(false)}
  }
  async function callStaff(){if(!session)return;setCalling(true);setError('');try{const lastQuestion=[...messages].reverse().find(message=>['user','customer'].includes(message.role || ''));const call=await api<CustomerStaffCall>(`/sessions/${session.id}/staff-calls`,post({reason:callReason,last_customer_question:lastQuestion?textOf(lastQuestion):''}),session.token);setSession(current=>current?({...current,staff_calls:[call,...(current.staff_calls || [])]}):null);setStaffOpen(false)}catch(error){setError(errorText(error))}finally{setCalling(false)}}
  const staffCalls:CustomerStaffCall[]=session?.staff_calls || []
  const latestCall=staffCalls[0] || null
  const latestMortgage=session?.display_events?.filter((e):e is MortgageDisplay=>e.kind==='mortgage').at(-1)
  return <div className="customer-shell"><header className="customer-header"><Brand/><div className="header-right"><span className="demo-label">建売住宅 AI接客 Demo</span><a href="/admin">管理者</a><a href="/staff">スタッフ</a></div></header><main className="customer-main"><div className="welcome-heading"><div><span className="eyebrow">A HOME, A CONVERSATION.</span><h1>新しい暮らしを、<br className="mobile-only"/>いっしょに見つけましょう。</h1><p>住宅購入のこと、購入の流れ、住宅ローン。気になることから自由にご相談ください。</p></div><span className="verified-label"><Icon name="check" size={15}/>確認・公開済みの情報だけをご案内</span></div><Alert message={connectionError || error || (health && !boundaryReady ? '接客の準備が整っていません。管理者にご確認ください。' : '')}/>{health && !health.ai_configured && <Alert tone="info" message="AI接客の設定が未完了です。公開資料の閲覧は可能ですが、文字・音声での AI 回答にはサーバーの API 設定が必要です。"/>}{session?.mode==='voice' && voice.ttsError && <div className="tts-error"><Alert message={voice.ttsError}/><button className="button secondary" onClick={()=>void voice.retrySpeech()}>音声を再試行</button><p>下の入力欄から文字でご相談いただけます。</p></div>}{session?.mode==='voice' && voice.ttsTestOnly && <p className="small-note">TEST ONLY — 検証用の電子音です。日本語音色・自然度の評価には使用できません。</p>}<div className={`customer-grid consultation-center ${materials?'has-materials':''}`}><section className="concierge-panel"><div className="concierge-top"><span className="eyebrow">AI HOUSING CONCIERGE</span><span className={`status-pill ${state}`}><i/>{stateLabels[state]}</span></div><Avatar state={state}/>{session?.mode==='voice'&&<div className="live-subtitles" aria-live="polite"><span className="subtitle-label">音声字幕 · {voice.status==='connecting'?'接続中':'リアルタイム'}</span>{voice.customerSubtitle&&<p className="customer-subtitle">お客様：{voice.customerSubtitle}</p>}<p>{voice.subtitle || (voice.status==='connecting'?'音声サービスに接続しています…':'お話しください。AI の音声字幕がここに表示されます。')}</p></div>}{!session ? <div className="start-area"><h2>気になることから、お気軽に。</h2><p>住宅購入・購入の流れ・住宅ローンをお尋ねください。<br/>接客開始後も文字でご相談いただけます。</p><button className="button primary wide" disabled={!boundaryReady || busy || !health?.realtime_configured} onClick={startVoice} title={!health?.realtime_configured?'サーバーの OpenAI API 設定が必要です':'マイクを使って音声接客を開始'}><Icon name="mic"/>{busy?'開始しています…':'接客を開始'}<span className="button-caption">{health?.realtime_configured?'音声で相談':'API 未設定'}</span></button><button className="button secondary wide" onClick={startText} disabled={!boundaryReady || busy}>{busy ? '開始しています…' : '文字で開始'}<Icon name="chat" size={18}/></button><span className="small-note">物件が決まっていなくてもご相談いただけます。</span></div> : <div className="session-caption"><span className="live-dot"/>{session.mode==='voice'?'音声で接客中':'文字で接客中'} <span>{session.version?`公開版 v${session.version}`:'資料未公開'}</span>{session.mode==='voice'&&<button className={`mute-button ${voice.muted?'muted':''}`} onClick={voice.toggleMute} aria-pressed={voice.muted}><Icon name="mic" size={12}/>{voice.muted?'マイクを再開':'マイクを停止'}</button>}<button onClick={end} disabled={busy}>接客終了</button></div>}<div className="conversation">{messages.length>0&&<p className="small-note">会話履歴は当時のご案内です。現在の条件はご案内資料と最新の試算をご確認ください。</p>}<div className="conversation-heading"><Icon name="chat" size={17}/><span>ご相談とご案内</span>{session&&<small>{session.version?`v${session.version} の確認済み資料`:'資料の確認・公開待ち'}</small>}</div>{!session ? <div className="conversation-empty">ここにお客様の質問と AI のご案内が表示されます。</div> : messages.length ? messages.map((message,index)=>{const customer=['customer','user'].includes(message.role || '');return <div key={message.event_id || index} className={`message ${customer?'customer':'assistant'}`}><span className="message-role">{customer?'お客様':message.channel==='policy'?'システム案内':'AIコンシェルジュ'}</span><div className="message-text">{textOf(message)}</div>{!customer&&<SourceList references={message.references || []}/>}</div>}) : <div className="conversation-empty">ご相談内容を文字で入力してください。</div>}{busy&&session&&<div className="thinking-message"><span/><span/><span/>資料を確認しています</div>}<div ref={bottom}/></div><div className="input-area"><div className="suggestions">{suggestions.map(value=><button key={value} disabled={!session || busy} onClick={()=>send(value)}>{value}</button>)}</div><form onSubmit={event=>{event.preventDefault();send(text)}}><label className="sr-only" htmlFor="question">ご相談内容</label><input id="question" value={text} onChange={event=>setText(event.target.value)} placeholder={session?session.mode==='voice'?'文字で質問する（文字への回答は音声なし）':'ご相談内容を入力してください':'接客を開始すると、文字でご相談できます'} disabled={!session || busy} autoComplete="off"/><button aria-label="送信" disabled={!session || busy || !text.trim()}><Icon name="send" size={19}/></button></form></div>{session&&<div className="staff-request"><div className="staff-request-top"><div><Icon name="people" size={19}/><span>担当スタッフへ相談する</span></div><button className="button secondary" onClick={()=>setStaffOpen(current=>!current)} disabled={calling || staffCalls.some(call=>call.status!=='completed')}>スタッフを呼ぶ</button></div>{latestCall&&<div className={`staff-status ${latestCall.status}`} role="status"><span className="live-dot"/>{latestCall.status==='completed'?'スタッフの対応が完了しました。':latestCall.status==='accepted'?'スタッフが確認しました。ご案内まで少々お待ちください。':'スタッフへの呼出を受け付けました。確認をお待ちください。'}</div>}{staffOpen&&<form onSubmit={event=>{event.preventDefault();callStaff()}}><label>ご相談内容<textarea value={callReason} onChange={event=>setCallReason(event.target.value)} required maxLength={500} rows={2}/></label><button className="button primary wide" disabled={calling || !callReason.trim()}>{calling?'呼出を送信しています…':'スタッフへの呼出を送信'}<Icon name="arrow" size={17}/></button></form>}</div>}<div className="customer-control-note"><Icon name="people" size={16}/><span>{session?.mode==='voice'?'文字入力への回答は文字で表示します。専門的な判断は担当スタッフにおつなぎします。':'専門的な判断や資料にない内容は、担当スタッフにおつなぎします。'}</span></div></section>{materials&&<aside className="property-column consultation-materials"><div className="section-heading"><h2>ご案内資料</h2><button className="button subtle" onClick={()=>setMaterials('')}>資料を閉じる</button></div>{materials==='offers'&&<section className="card">{offers.length?offers.map(p=><div key={p.property_id}><h3>{p.property_name}</h3><button className="button secondary" onClick={()=>chooseProperty(p.property_id)}>この物件について相談</button></div>):<p>公開済みの物件資料はありません。スタッフへご相談ください。</p>}</section>}{materials==='property'&&property&&<PropertyPanel property={property} version={session?.version || null} topic={topic} setTopic={setTopic}/>} {materials==='loan'&&session&&<Mortgage session={session} externalResult={latestMortgage?.result} externalResultEventId={latestMortgage?.event_id} onResult={()=>{}}/>}{materials==='sources'&&<section className="card"><h3>今回の回答の参照</h3>{session?.display_events?.filter((e):e is SourcesDisplay=>e.kind==='sources').at(-1)?.items.map((item,i)=><details key={i}><summary>{item.scope==='company'?'会社資料':item.scope==='property'?'物件資料':'共通住宅購入資料'}</summary><p style={{whiteSpace:'pre-wrap'}}>{item.text}</p><SourceList references={item.references}/></details>)}<SourceList references={[...messages].reverse().find(m=>m.role==='assistant')?.references || []}/>{session?.property_id&&<button className="button secondary" onClick={()=>setMaterials('property')}>物件資料を見る</button>}</section>}</aside>}</div><footer className="customer-footer"><span>SANZO / AI住宅接客 Demo</span><span>AI のご案内は確認済み資料に基づきます。詳細・条件は担当スタッフにご確認ください。</span></footer></main></div>
}
