// Bounded, continuous REAL OpenAI Realtime business acceptance.
// Only the microphone input is synthetic macOS Kyoko speech, injected in a
// test-only MediaStream. No application response, API or tool is mocked.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
import {execFileSync} from 'node:child_process'
import crypto from 'node:crypto'

const root=path.resolve(import.meta.dirname,'..')
const run=process.env.VOICE_RUN_NAME || 'live_consultation_voice'
const out=path.join(root,'evidence',run)
await fs.mkdir(path.join(out,'input'),{recursive:true})
if(await fs.stat(path.join(out,'result.json')).catch(()=>null))throw new Error('Evidence exists; choose a separate VOICE_RUN_NAME for a justified revalidation')
const envText=await fs.readFile(path.join(root,'.env'),'utf8')
const staffPassword=envText.match(/^STAFF_PASSWORD=(.*)$/m)?.[1]?.trim().replace(/^['"]|['"]$/g,'')
if(!staffPassword)throw new Error('Staff credential not configured')
const evidenceSources=['frontend/src/Mortgage.tsx','frontend/src/Customer.tsx','frontend/src/useVoice.ts','backend/app/services/ai.py','backend/app/services/realtime.py','backend/app/services/tools.py','backend/app/services/context.py','backend/app/services/sessions.py','backend/app/services/guardrails.py']
async function sourceHashes(){return Object.fromEntries(await Promise.all(evidenceSources.map(async filename=>[filename,crypto.createHash('sha256').update(await fs.readFile(path.join(root,filename))).digest('hex')]))) }
const initialHashes=await sourceHashes()
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required']})
const context=await browser.newContext({viewport:{width:1440,height:1100},permissions:['microphone'],locale:'ja-JP'})
await context.addInitScript(()=>{
  window.__voiceEvidence={events:[],audioChunks:[],avatarStates:[]}
  new MutationObserver(()=>{
    const state=document.querySelector('.avatar-stage')?.className
    if(state&&window.__voiceEvidence.avatarStates.at(-1)?.state!==state)window.__voiceEvidence.avatarStates.push({state,at_ms:Date.now()})
  }).observe(document,{subtree:true,attributes:true,childList:true})
  navigator.mediaDevices.getUserMedia=async()=>{
    const audioContext=new AudioContext({sampleRate:48000})
    const destination=audioContext.createMediaStreamDestination()
    // Keep zero-valued audio frames flowing between finite speech clips so
    // server VAD receives actual silence and can commit the audio turn.
    const clock=audioContext.createOscillator();const zero=audioContext.createGain()
    zero.gain.value=0;clock.connect(zero);zero.connect(destination);clock.start()
    window.__syntheticMic={audioContext,destination,clock,zero,sources:[]}
    return destination.stream
  }
  const NativeAudio=window.Audio
  window.Audio=function(...args){const audio=new NativeAudio(...args);window.__playbackAudio=audio;return audio}
  window.Audio.prototype=NativeAudio.prototype
  const original=RTCPeerConnection.prototype.createDataChannel
  RTCPeerConnection.prototype.createDataChannel=function(...args){
    window.__voicePeer=this
    this.addEventListener('track',e=>{
      const recorder=new MediaRecorder(e.streams[0] || new MediaStream([e.track]))
      recorder.ondataavailable=e=>{if(e.data.size)window.__voiceEvidence.audioChunks.push(e.data)}
      recorder.start();window.__voiceRecorder=recorder
    })
    const channel=original.apply(this,args)
    channel.addEventListener('message',e=>{
      const data=JSON.parse(e.data)
      const entry={type:data.type,at_ms:Date.now()}
      if(data.transcript)entry.transcript=data.transcript
      if(data.type==='response.done'){
        entry.status=data.response?.status
        entry.function_calls=(data.response?.output || []).filter(item=>item.type==='function_call').length
      }
      if(data.type==='error')entry.error={code:data.error?.code,type:data.error?.type,param:data.error?.param}
      if(data.type==='response.function_call_arguments.done')entry.tool=data.name
      window.__voiceEvidence.events.push(entry)
    })
    return channel
  }
})
const page=await context.newPage()
const pageErrors=[];page.on('pageerror',e=>pageErrors.push(e.message))
let session
const result={date:'2026-10-07',mode:'REAL_CHROME_WEBRTC_REAL_OPENAI_REAL_TOOLS_SYNTHETIC_KYOKO_INPUT',normal_demo_acceptance:'NOT_RUN',physical_microphone:'NOT_VERIFIED',physical_speaker_audibility:'NOT_VERIFIED',model:'configured .env OPENAI_REALTIME_MODEL',single_session:true,source_hashes_at_start:initialHashes,inputs:[],turns:[],checks:{},status:'RUNNING'}
const transcriptTypes=['response.output_audio_transcript.done','response.audio_transcript.done']
async function persisted(){const response=await context.request.get(`http://127.0.0.1:5174/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}});expect(response.ok()).toBe(true);return response.json()}
async function save(){await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2))}
async function settled(after,requireUser=true){
  await page.waitForFunction(({after,requireUser})=>{
    if(document.querySelector('[role="alert"]'))return true
    const e=window.__voiceEvidence.events.slice(after)
    const user=e.findIndex(x=>x.type==='conversation.item.input_audio_transcription.completed')
    if(requireUser&&user<0)return false
    const start=requireUser?user:0
    const transcript=e.findLastIndex((x,i)=>i>=start&&['response.output_audio_transcript.done','response.audio_transcript.done'].includes(x.type))
    const done=e.findLastIndex(x=>x.type==='response.done')
    const stopped=e.findLastIndex(x=>x.type==='output_audio_buffer.stopped')
    return transcript>=0&&done>transcript&&e[done].status==='completed'&&e[done].function_calls===0&&stopped>transcript
      &&document.querySelector('.avatar-stage')?.classList.contains('idle')
  },{after,requireUser},{timeout:150000})
  await page.waitForTimeout(500)
  if(await page.getByRole('alert').count())throw new Error(await page.getByRole('alert').innerText())
}
async function say(text,label){
  const filename=path.join(out,'input',`${String(result.inputs.length).padStart(2,'0')}_${label}.wav`)
  execFileSync('/usr/bin/say',['-v','Kyoko','-r','175','-o',filename,'--file-format=WAVE','--data-format=LEI16@48000',text])
  const bytes=await fs.readFile(filename)
  result.inputs.push({label,text,kind:'SYNTHETIC_MACOS_KYOKO_WAV',sha256:crypto.createHash('sha256').update(bytes).digest('hex')})
  console.log(JSON.stringify({stage:label,status:'SYNTHETIC_INPUT_START',text}))
  const after=await page.evaluate(()=>window.__voiceEvidence.events.length)
  await page.evaluate(async b64=>{
    const m=window.__syntheticMic
    const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0))
    await m.audioContext.resume()
    const buffer=await m.audioContext.decodeAudioData(bytes.buffer)
    const source=m.audioContext.createBufferSource();source.buffer=buffer;source.connect(m.destination);m.sources.push(source)
    await new Promise(resolve=>{source.onended=resolve;source.start()})
  },bytes.toString('base64'))
  await settled(after)
  const local=await page.evaluate(after=>({events:window.__voiceEvidence.events.slice(after),subtitles:document.querySelector('.live-subtitles')?.textContent,avatar:document.querySelector('.avatar-stage')?.className}),after)
  const state=await persisted()
  const turn={label,intended_input:text,actual_input:local.events.find(e=>e.type==='conversation.item.input_audio_transcription.completed')?.transcript,actual_answer:local.events.filter(e=>transcriptTypes.includes(e.type)).map(e=>e.transcript).join('\n'),...local,tool_events:state.tool_events,messages:state.messages}
  result.turns.push(turn);await save()
  console.log(JSON.stringify({stage:label,actual_input:turn.actual_input,actual_answer:turn.actual_answer,avatar:turn.avatar,successful_calculations:state.tool_events.filter(e=>e.name==='calculate_mortgage'&&!e.result?.error).length}))
  return {turn,state}
}
try{
  const health=await(await context.request.get('http://127.0.0.1:5174/api/health')).json()
  expect(health.demo_mode).toBe('test');expect(health.realtime_configured).toBe(true)
  page.on('response',async response=>{
    if(response.request().method()==='POST'&&response.url().endsWith('/api/sessions')&&response.ok()){
      session=await response.json();result.session_id=session.id;result.version=session.version
      result.initial_property_id=session.property_id
    }
  })
  await page.goto('http://127.0.0.1:5174/')
  expect(await page.locator('body').innerText()).not.toMatch(/No\.15|7,690|八千代/)
  await page.getByRole('button',{name:'接客を開始',exact:false}).click()
  await settled(0,false)
  result.greeting=await page.evaluate(()=>window.__voiceEvidence.events.filter(e=>['response.output_audio_transcript.done','response.audio_transcript.done'].includes(e.type)).map(e=>e.transcript).join('\n'))
  expect(result.greeting).toMatch(/住宅購入|住宅ローン/)
  expect(result.greeting).not.toMatch(/No\.15|八千代|7,690|7690/)
  expect(session.property_id).toBeNull();expect(session.snapshot.property).toEqual({})
  result.checks.general_greeting_without_default_property='PASS'
  let turn,state
  result.general_ui_prior_evidence='evidence/live_consultation_voice/result.json (general card / clarification checks before targeted loan fix)'
  ;({turn,state}=await say('借入額は3000万円です。物件はまだ決めていません。','explicit_loan_amount'))
  expect(state.property_id).toBeNull()
  expect(state.tool_events.filter(e=>e.name==='calculate_mortgage').length).toBe(0)
  ;({turn,state}=await say('35年で考えています。','loan_years'))
  expect(state.tool_events.filter(e=>e.name==='calculate_mortgage').length).toBe(0)
  result.checks.no_calculation_before_explicit_product='PASS'
  const presentation=result.turns.map(t=>t.actual_answer).join('\n')
  result.preselection_rate_presentation=presentation
  result.checks.preselection_conditions=/9割以下|９割以下|九割以下/.test(presentation)&&/9割超|９割超|九割超|9割を超|９割を超/.test(presentation)?'PASS_BOTH_FLAT35_BANDS':'REVIEW_REQUIRED'
  ;({turn,state}=await say('三菱UFJ銀行の変動金利でお願いします。月返済額を試算してください。','explicit_product'))
  const calculations=state.tool_events.filter(e=>e.name==='calculate_mortgage'&&!e.result?.error)
  expect(calculations.length).toBe(1)
  const calculation=calculations[0].result
  result.calculation=calculation;result.calculator_arguments=calculations[0].arguments
  expect(calculation.loan_amount).toBe(30000000);expect(calculation.years).toBe(35)
  expect(calculation.property_price).toBeNull();expect(calculation.down_payment).toBeNull()
  expect(calculation.monthly_payment).toBe(87439);expect(calculation.annual_interest_rate).toBe(1.195)
  expect(calculation.version).toBe(session.version);expect(state.property_id).toBeNull()
  await expect(page.locator('.mortgage-result').last()).toContainText('87,439 円')
  const card=await page.locator('.mortgage-result').last().innerText()
  expect(card).toContain('30,000,000 円');expect(card).toContain('35 年');expect(card).not.toContain('76,900,000')
  result.calculation_card=card
  const normalized=turn.actual_answer.normalize('NFKC').replace(/[,，\s]/g,'')
  result.checks.real_backend_voice_subtitle_card_amount=/87439円|8万7439円|八万七千四百三十九円/.test(normalized)?'PASS_87439_JPY':'REVIEW_REQUIRED'
  result.checks.explicit_loan_no_default_price='PASS'
  await page.screenshot({path:path.join(out,'unselected-loan.png'),fullPage:true})
  ;({turn,state}=await say('15号地の価格と設備を教えてください。','explicit_property'))
  expect(state.property_id).toBe('No.15')
  expect(turn.actual_answer).toMatch(/7690|7,690|七千六百九十|7千690/)
  await expect(page.locator('.consultation-materials')).toBeVisible()
  await expect(page.locator('.consultation-materials')).toContainText('No.15')
  result.checks.explicit_voice_property_and_linked_card='PASS'
  await page.getByRole('button',{name:'資料を閉じる',exact:true}).click()
  await expect(page.locator('.consultation-materials')).toHaveCount(0)
  const {turn:handoffTurn,state:handoff}=await say('この年収なら、ローン審査に絶対通りますか？','underwriting_handoff')
  result.checks.voice_underwriting_non_guarantee=/判断|確約|断定|金融機関|できません|保証/.test(handoffTurn.actual_answer)?'PASS_ACTUAL_ANSWER_REQUIRES_REVIEW':'REVIEW_REQUIRED'
  const call=handoff.staff_calls.find(c=>c.status==='pending')
  expect(call).toBeTruthy();expect(call.session_id).toBe(session.id);expect(call.version).toBe(session.version)
  result.staff_call_created=call
  await expect(page.locator('.staff-status')).toContainText('呼出を受け付けました')
  const staffPage=await context.newPage();await staffPage.goto('http://127.0.0.1:5174/staff')
  await staffPage.getByLabel('パスワード',{exact:true}).fill(staffPassword)
  await staffPage.getByRole('button',{name:'ログイン',exact:true}).click()
  const staffCard=staffPage.locator('.staff-call').filter({hasText:session.id})
  await expect(staffCard).toBeVisible()
  await staffCard.getByRole('button',{name:'受付',exact:true}).click()
  await expect(staffCard).toContainText('受付済み')
  await expect(page.locator('.staff-status')).toContainText('スタッフが確認しました')
  result.staff_accepted=(await persisted()).staff_calls.find(c=>c.id===call.id)
  await staffCard.getByRole('button',{name:'対応完了',exact:true}).click()
  await expect(page.locator('.staff-status')).toContainText('スタッフの対応が完了しました')
  result.staff_completed=(await persisted()).staff_calls.find(c=>c.id===call.id)
  expect(result.staff_completed.status).toBe('completed')
  result.checks.staff_ui_and_customer_polling='PASS_PENDING_ACCEPTED_COMPLETED_SAME_SESSION'
  await staffPage.getByRole('button',{name:/すべて/}).click()
  await expect(staffPage.locator('.staff-call').filter({hasText:session.id})).toContainText('対応完了')
  await staffPage.screenshot({path:path.join(out,'staff-completed.png'),fullPage:true})
  await page.screenshot({path:path.join(out,'customer-staff-completed.png'),fullPage:true})
  const preEnd=await persisted();result.messages=preEnd.messages;result.tool_events=preEnd.tool_events
  result.events=await page.evaluate(()=>window.__voiceEvidence.events)
  result.avatar_states=await page.evaluate(()=>window.__voiceEvidence.avatarStates)
  expect(result.events.filter(e=>e.type==='conversation.item.input_audio_transcription.completed').length).toBe(result.inputs.length)
  expect(result.messages.filter(m=>m.role==='user'&&m.channel==='voice').length).toBe(result.inputs.length)
  expect(result.messages.filter(m=>m.role==='assistant').every(m=>m.version===session.version&&m.provider==='openai_realtime')).toBe(true)
  expect(result.events.some(e=>e.type==='error')).toBe(false);expect(pageErrors).toEqual([])
  result.page_errors=pageErrors
  result.received_audio=await page.evaluate(async()=>{const rows=[];for(const r of (await window.__voicePeer.getStats()).values())if(r.type==='inbound-rtp'&&r.kind==='audio')rows.push({bytesReceived:r.bytesReceived,packetsReceived:r.packetsReceived});return rows})
  await page.evaluate(()=>new Promise(resolve=>{window.__voiceRecorder.addEventListener('stop',resolve,{once:true});window.__voiceRecorder.stop()}))
  const audio=await page.evaluate(async()=>{const bytes=new Uint8Array(await new Blob(window.__voiceEvidence.audioChunks).arrayBuffer());let raw='';for(const v of bytes)raw+=String.fromCharCode(v);return btoa(raw)})
  await fs.writeFile(path.join(out,'actual_openai_response.webm'),Buffer.from(audio,'base64'))
  const endResponse=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith(`/api/sessions/${session.id}/end`))
  await page.getByRole('button',{name:'接客終了',exact:true}).click();expect((await endResponse).status()).toBe(200)
  await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
  result.local_media_end=await page.evaluate(()=>({peer_state:window.__voicePeer.connectionState,sender_tracks:window.__voicePeer.getSenders().map(s=>s.track?.readyState),synthetic_input_tracks:window.__syntheticMic.destination.stream.getTracks().map(t=>t.readyState),playback_paused:window.__playbackAudio.paused,playback_source_cleared:window.__playbackAudio.srcObject===null,avatar:document.querySelector('.avatar-stage')?.className,active_session_caption:!!document.querySelector('.session-caption')}))
  expect(result.local_media_end.peer_state).toBe('closed');expect(result.local_media_end.sender_tracks.every(s=>s==='ended'||s===undefined)).toBe(true);expect(result.local_media_end.synthetic_input_tracks.every(s=>s==='ended')).toBe(true)
  expect(result.local_media_end.playback_paused).toBe(true);expect(result.local_media_end.playback_source_cleared).toBe(true);expect(result.local_media_end.active_session_caption).toBe(false)
  const ended=await persisted();result.ended_status=ended.status;result.realtime_end=ended.realtime
  expect(ended.status).toBe('ended');expect(ended.realtime.status).toBe('closed');expect(ended.realtime.upstream_hangup_status).toBe(200)
  result.checks.end_cleanup='PASS_STOPPED_INPUT_PAUSED_AUDIO_CLOSED_PEER_UPSTREAM_200_ENDED_SESSION'
  result.source_hashes_at_end=await sourceHashes()
  expect(result.source_hashes_at_end).toEqual(result.source_hashes_at_start)
  result.status='PASS_AUTOMATED_CONTINUOUS_VOICE_BUSINESS_PENDING_MANUAL_TRANSCRIPT_REVIEW'
  await page.screenshot({path:path.join(out,'ended.png'),fullPage:true})
}catch(e){
  result.status='FAIL';result.error=e.message;result.page_errors=pageErrors
  result.events=await page.evaluate(()=>window.__voiceEvidence.events).catch(()=>[])
  if(session){const state=await persisted().catch(()=>null);if(state){result.messages=state.messages;result.tool_events=state.tool_events;result.realtime_at_failure=state.realtime;result.staff_calls_at_failure=state.staff_calls}}
  await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{})
}finally{
  if(session){const state=await persisted().catch(()=>null);if(state?.status==='active'){
    await context.request.post(`http://127.0.0.1:5174/api/sessions/${session.id}/end`,{headers:{'X-Session-Token':session.token}}).catch(()=>{})
    const closed=await persisted().catch(()=>null);result.cleanup_after_failure=closed?{status:closed.status,realtime:closed.realtime}:null
  }}
  await save();await browser.close()
  console.log(JSON.stringify({status:result.status,error:result.error,checks:result.checks,physical_microphone:result.physical_microphone,physical_speaker_audibility:result.physical_speaker_audibility,evidence:`evidence/${run}/result.json`},null,2))
}
if(result.status==='FAIL')process.exitCode=1
