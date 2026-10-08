// Live OpenAI WebRTC test using a clearly labeled synthetic Japanese input.
// This is not a physical microphone / user acceptance test. No AI mock.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'..')
const out=path.join(root,'evidence',process.env.VOICE_RUN_NAME || 'live_voice_roundtrip');await fs.mkdir(out,{recursive:true})
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',`--use-file-for-fake-audio-capture=${path.join(root,'evidence/live_voice/input_test.wav')}`]})
const context=await browser.newContext({viewport:{width:1440,height:1100},permissions:['microphone'],locale:'ja-JP'})
await context.addInitScript(()=>{
  window.__voiceEvidence={events:[],errors:[],audioChunks:[],avatarStates:[]}
  new MutationObserver(()=>{
    const state=document.querySelector('.avatar-stage')?.className
    if(state&&window.__voiceEvidence.avatarStates.at(-1)?.state!==state)window.__voiceEvidence.avatarStates.push({state,at_ms:Date.now()})
  }).observe(document,{subtree:true,attributes:true,childList:true})
  const original=RTCPeerConnection.prototype.createDataChannel
  RTCPeerConnection.prototype.createDataChannel=function(...args){
    window.__voicePeer=this
    this.addEventListener('track',e=>{
      const media=e.streams[0] || new MediaStream([e.track])
      const recorder=new MediaRecorder(media)
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
const page=await context.newPage();const pageErrors=[];page.on('pageerror',e=>pageErrors.push(e.message))
let session
let result={date:'2026-10-07',mode:'REAL_OPENAI_CHROME_WEBRTC_WITH_SYNTHETIC_TEST_INPUT',physical_microphone:'NOT_VERIFIED',input:'macOS Kyoko synthetic Japanese: 駅から何分ですか。',model:'configured .env OPENAI_REALTIME_MODEL',status:'RUNNING'}
try{
  const health=await(await context.request.get('http://127.0.0.1:5174/api/health')).json()
  if(health.demo_mode!=='test'||!health.realtime_configured)throw new Error('Require isolated configured test server')
  page.on('response',async response=>{
    if(response.request().method()==='POST' && response.url().endsWith('/api/sessions') && response.ok()){
      session=await response.json();result.session_id=session.id;result.version=session.version
    }
  })
  await page.goto('http://127.0.0.1:5174/')
  await page.getByRole('button',{name:'接客を開始',exact:false}).click()
  await page.waitForFunction(()=>window.__voiceEvidence.events.some(e=>e.type==='response.output_audio_transcript.done'||e.type==='response.audio_transcript.done')||document.querySelector('[role=alert]'),{},{timeout:60000})
  if(await page.getByRole('alert').count())throw new Error(await page.getByRole('alert').innerText())
  const greeting=await page.evaluate(()=>window.__voiceEvidence.events.find(e=>e.type==='response.output_audio_transcript.done'||e.type==='response.audio_transcript.done')?.transcript)
  result.actual_greeting=greeting
  expect(greeting).toMatch(/^こんにちは[。．. ]*AI住宅コンシェルジュです/)
  expect(greeting).toContain('No.15')
  await page.waitForFunction(()=>{
    const e=window.__voiceEvidence.events
    const user=e.findIndex(x=>x.type==='conversation.item.input_audio_transcription.completed'&&x.transcript.includes('駅'))
    const answer=e.findIndex((x,i)=>i>user&&user>=0&&(x.type==='response.output_audio_transcript.done'||x.type==='response.audio_transcript.done')&&/12|１２/.test(x.transcript))
    return answer>=0 && e.slice(answer+1).some(x=>x.type==='response.done'&&x.status==='completed'&&x.function_calls===0)
      && e.slice(answer+1).some(x=>x.type==='output_audio_buffer.stopped')
      && document.querySelector('.avatar-stage')?.classList.contains('idle')
  },{},{timeout:90000})
  const evidence=await page.evaluate(async()=>{
    const entries=[]
    for(const report of (await window.__voicePeer.getStats()).values())if(report.type==='inbound-rtp'&&report.kind==='audio')entries.push({bytesReceived:report.bytesReceived,packetsReceived:report.packetsReceived})
    return {events:window.__voiceEvidence.events,received_audio:entries,avatar_states:window.__voiceEvidence.avatarStates,subtitles:document.querySelector('.live-subtitles')?.textContent}
  })
  expect(evidence.received_audio.some(s=>s.bytesReceived>1000)).toBe(true)
  expect(evidence.events.some(e=>e.type==='error')).toBe(false)
  const userIndex=evidence.events.findIndex(e=>e.type==='conversation.item.input_audio_transcription.completed'&&e.transcript.includes('駅'))
  const answers=evidence.events.slice(userIndex+1).filter(e=>e.type==='response.output_audio_transcript.done'||e.type==='response.audio_transcript.done')
  result.user_question=evidence.events[userIndex].transcript
  result.actual_answer=answers.map(e=>e.transcript).join('\n')
  expect(result.actual_answer).toMatch(/12|１２/)
  expect(result.actual_answer).toMatch(/4戸|４戸|4つ|４つ|全体|範囲|複数|分譲/)
  result.events=evidence.events;result.received_audio=evidence.received_audio;result.avatar_states=evidence.avatar_states;result.subtitles=evidence.subtitles;result.page_errors=pageErrors
  result.roundtrip_check='PASS_REAL_STATION_AUDIO_SUBTITLES_AND_PLAYBACK'
  await page.evaluate(()=>new Promise(resolve=>{window.__voiceRecorder.addEventListener('stop',resolve,{once:true});window.__voiceRecorder.stop()}))
  const audio=await page.evaluate(async()=>{const bytes=new Uint8Array(await new Blob(window.__voiceEvidence.audioChunks).arrayBuffer());let raw='';for(const v of bytes)raw+=String.fromCharCode(v);return btoa(raw)})
  await fs.writeFile(path.join(out,'actual_openai_response.webm'),Buffer.from(audio,'base64'))
  const stored=await(await context.request.get(`http://127.0.0.1:5174/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}})).json()
  result.messages=stored.messages;result.tool_events=stored.tool_events
  expect(pageErrors).toEqual([])
  expect(evidence.subtitles).toContain('駅から何分')
  expect(evidence.subtitles).toMatch(/12|１２/)
  for(const state of ['listening','thinking','speaking'])expect(evidence.avatar_states.some(e=>e.state.includes(state))).toBe(true)
  await page.screenshot({path:path.join(out,'live-voice.png'),fullPage:true})
  const endResponse=page.waitForResponse(response=>response.request().method()==='POST'&&response.url().endsWith(`/api/sessions/${session.id}/end`))
  await page.getByRole('button',{name:'接客終了',exact:true}).click()
  expect((await endResponse).status()).toBe(200)
  await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
  result.local_media_end=await page.evaluate(()=>({peer_state:window.__voicePeer.connectionState,sender_tracks:window.__voicePeer.getSenders().map(s=>s.track?.readyState)}))
  expect(result.local_media_end.peer_state).toBe('closed')
  expect(result.local_media_end.sender_tracks.every(state=>state==='ended'||state===undefined)).toBe(true)
  const ended=await(await context.request.get(`http://127.0.0.1:5174/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}})).json()
  result.ended_status=ended.status;result.realtime_end=ended.realtime
  expect(ended.status).toBe('ended')
  expect(ended.realtime.status).toBe('closed')
  expect(ended.realtime.upstream_hangup_status).toBe(200)
  result.status='PASS_REAL_AUDIO_STATION_ROUNDTRIP_WITH_SYNTHETIC_INPUT'
}catch(e){result.status='FAIL';result.error=e.message;result.events=await page.evaluate(()=>window.__voiceEvidence.events).catch(()=>[]);await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw e}
finally{
  if(session)await context.request.post(`http://127.0.0.1:5174/api/sessions/${session.id}/end`,{headers:{'X-Session-Token':session.token}}).catch(()=>{})
  await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2));await browser.close()
  console.log(JSON.stringify({status:result.status,error:result.error,physical_microphone:result.physical_microphone,transcripts:result.events?.filter(e=>e.transcript).map(e=>e.transcript),received_audio:result.received_audio},null,2))
}
