// Actual isolated Chrome Audio playback; TEST WebRTC/VAD and silent synthetic track.
// Not a real mic, real provider or physical speaker acceptance.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
const out=path.resolve(import.meta.dirname,'../evidence/japanese_voice_architecture_phase1')
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--autoplay-policy=no-user-gesture-required']})
const context=await browser.newContext({viewport:{width:1440,height:1100}})
await context.addInitScript(()=>{
 window.TEST={peers:[],tracks:[],audioContexts:[],activeUrls:[],speechBodies:[],audioEvents:[],maxPlaying:0,playing:0}
 navigator.mediaDevices.getUserMedia=async()=>{
  const ac=new AudioContext();const source=ac.createMediaStreamDestination();window.TEST.audioContexts.push(ac)
  window.TEST.tracks.push(...source.stream.getTracks());return source.stream
 }
 window.RTCPeerConnection=class{
  constructor(){this.connectionState='new';window.TEST.peers.push(this)}
  addTrack(){}
  createDataChannel(){this.channel={close(){this.closed=true}};return this.channel}
  async createOffer(){return {type:'offer',sdp:'v=0\r\nTEST_NO_MIC_OR_OPENAI'}}
  async setLocalDescription(){}
  async setRemoteDescription(){this.connectionState='connected';setTimeout(()=>this.channel.onopen?.(),0)}
  close(){this.connectionState='closed';this.channel?.close()}
 }
 const originalAudio=window.Audio
 window.Audio=function(...args){
  const audio=new originalAudio(...args);let counted=false
  audio.addEventListener('playing',()=>{if(!counted){counted=true;window.TEST.playing++;window.TEST.maxPlaying=Math.max(window.TEST.maxPlaying,window.TEST.playing)}window.TEST.audioEvents.push('playing')})
  for(const name of ['pause','ended','emptied'])audio.addEventListener(name,()=>{if(counted){counted=false;window.TEST.playing--}window.TEST.audioEvents.push(name)})
  return audio
 }
 const create=URL.createObjectURL.bind(URL),revoke=URL.revokeObjectURL.bind(URL)
 URL.createObjectURL=blob=>{const url=create(blob);window.TEST.activeUrls.push(url);return url}
 URL.revokeObjectURL=url=>{window.TEST.activeUrls=window.TEST.activeUrls.filter(u=>u!==url);revoke(url)}
 const originalFetch=window.fetch.bind(window)
 window.fetch=(input,opts)=>{if(String(input).endsWith('/speech')&&opts?.body)window.TEST.speechBodies.push(JSON.parse(opts.body));return originalFetch(input,opts)}
})
const page=await context.newPage()
const result={status:'RUNNING',provider:'TEST_ONLY_FAKE_WEBRTC_AND_ELECTRONIC_TONE',paid_api_calls:0,physical_microphone:'NOT_TESTED',physical_speaker:'NOT_TESTED',checks:{},page_errors:[]}
page.on('pageerror',e=>result.page_errors.push(e.message))
let session
async function emit(event){await page.evaluate(event=>window.TEST.peers.at(-1).channel.onmessage({data:JSON.stringify(event)}),event)}
async function turn(text){
 await emit({type:'input_audio_buffer.speech_started'})
 await expect(page.locator('.avatar-stage')).toHaveClass(/listening/)
 const response=await context.request.post(`http://localhost:5188/api/TEST/voice-turn/${session.id}`,{headers:{'X-Session-Token':session.token},data:{text}})
 expect(response.ok()).toBe(true);const value=await response.json()
 for(const event of value.events.slice(1))await emit(event)
 return value.answer
}
async function speaking(text){const answer=await turn(text);await expect(page.locator('.avatar-stage')).toHaveClass(/speaking/);await expect(page.locator('.live-subtitles')).toContainText(answer);return answer}
async function idle(){await expect(page.locator('.avatar-stage')).toHaveClass(/idle/,{timeout:8000})}
try{
 await page.goto('http://localhost:5188')
 const started=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/sessions'&&r.request().method()==='POST')
 started.catch(()=>{})
 await page.getByRole('button',{name:/接客を開始/}).click();session=await (await started).json()
 await expect(page.locator('.live-subtitles')).toContainText('リアルタイム')
 result.checks.new_mode_start_no_property='PASS'
 await speaking('住宅購入は何から始めますか？');await idle()
 result.checks.text_delta_done_saved_event_playback_idle='PASS'
 const first=await context.request.get(`http://localhost:5188/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}})
 expect((await first.json()).messages.filter(m=>m.role==='assistant')).toHaveLength(1)
 result.checks.audio_transcript_ignored_no_duplicate='PASS'
 await speaking('紹介できる物件はありますか？');await idle()
 await expect(page.getByRole('button',{name:'この物件について相談',exact:true})).toBeVisible()
 await page.getByRole('button',{name:'この物件について相談',exact:true}).click()
 await speaking('No.15の設備について教えてください');await idle()
 await expect(page.locator('.property-panel')).toContainText('TEST設備')
 await page.getByRole('button',{name:'資料を閉じる',exact:true}).click();await expect(page.locator('.consultation-materials')).toHaveCount(0)
 result.checks.property_selection_materials_close='PASS'
 const loan=await speaking('借入額は3000万円、35年、TEST変動金利でお願いします。')
 await expect(page.locator('.mortgage-result')).toContainText('87,439 円');expect(loan).toContain('87,439');await idle()
 result.checks.loan_backend_amount_card_subtitle='PASS'
 await speaking('打断用の回答をお願いします')
 const interruptedAt=Date.now();await emit({type:'input_audio_buffer.speech_started'})
 await expect(page.locator('.avatar-stage')).toHaveClass(/listening/)
 expect(await page.evaluate(()=>window.TEST.playing)).toBe(0)
 result.checks.barge_in_playback_stopped={status:'PASS',observed_ms:Date.now()-interruptedAt}
 await speaking('次の住宅購入の相談です');await idle()
 const pending=await turn('遅い音声生成の確認です')
 await expect(page.locator('.avatar-stage')).toHaveClass(/thinking/)
 await page.waitForTimeout(100);await emit({type:'input_audio_buffer.speech_started'})
 await speaking('新しい質問です');await idle()
 result.checks.barge_in_pending_request_aborted='PASS'
 const failedText=await turn('失敗を確認します')
 await expect(page.locator('.tts-error')).toContainText('日本語音声生成に失敗')
 await expect(page.locator('.live-subtitles')).toContainText(failedText)
 await expect(page.getByRole('button',{name:'音声を再試行',exact:true})).toBeVisible()
 await expect(page.locator('.avatar-stage')).toHaveClass(/idle/)
 result.checks.failure_visible_subtitle_kept_no_fallback='PASS'
 await speaking('この年収ならローン審査に絶対通りますか？');await idle()
 await expect(page.locator('.staff-status')).toContainText('確認をお待ちください')
 const staff=await context.newPage();await staff.goto('http://localhost:5188/staff')
 await staff.getByLabel('パスワード').fill('TEST-phase1-staff');await staff.getByRole('button',{name:'ログイン',exact:true}).click()
 const card=staff.locator('article.staff-call').filter({hasText:session.id})
 await card.getByRole('button',{name:'受付',exact:true}).click();await expect(page.locator('.staff-status')).toContainText('スタッフが確認しました')
 await card.getByRole('button',{name:'対応完了',exact:true}).click();await expect(page.locator('.staff-status')).toContainText('対応が完了しました')
 result.checks.staff_policy_and_state_sync='PASS'
 await speaking('接客終了用の回答です')
 await page.screenshot({path:path.join(out,'test-tts-speaking.png'),fullPage:true})
 await page.getByRole('button',{name:'接客終了',exact:true}).click()
 await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
 const cleanup=await page.evaluate(()=>({tracks:window.TEST.tracks.map(t=>t.readyState),peers:window.TEST.peers.map(p=>p.connectionState),urls:window.TEST.activeUrls.length,playing:window.TEST.playing,maxPlaying:window.TEST.maxPlaying,speechBodies:window.TEST.speechBodies,audioEvents:window.TEST.audioEvents}))
 expect(cleanup.tracks.every(t=>t==='ended')).toBe(true);expect(cleanup.peers.every(s=>s==='closed')).toBe(true)
 expect(cleanup.urls).toBe(0);expect(cleanup.playing).toBe(0);expect(cleanup.maxPlaying).toBe(1)
 expect(cleanup.speechBodies.every(b=>Object.keys(b).length===1&&Number.isInteger(b.assistant_event_id))).toBe(true)
 result.cleanup=cleanup;result.checks.end_tracks_peer_audio_urls='PASS';result.checks.event_id_only_no_overlap='PASS'
 const evidence=await (await context.request.get('http://localhost:5188/api/TEST/voice-evidence')).json()
 expect(evidence.realtime_session_configs.every(c=>JSON.stringify(c.output_modalities)==='["text"]'&&!c.audio.output)).toBe(true)
 expect(evidence.fake_cancelled).toBeGreaterThan(0);expect(evidence.connections).toBe(0);expect(evidence.tts_jobs).toBe(0);expect(evidence.tts_cache).toBe(0)
 expect(evidence.fake_tts_inputs).toContain(loan)
 result.checks.server_text_only_cancel_end_and_tts_same_text='PASS'
 // End while the sideband event is not saved yet: the resolution timer/fetch
 // must not keep polling or resurrect audio after the session closes.
 const startedAgain=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/sessions'&&r.request().method()==='POST');startedAgain.catch(()=>{})
 await page.getByRole('button',{name:/接客を開始/}).click();session=await (await startedAgain).json()
 await expect(page.locator('.live-subtitles')).toContainText('リアルタイム')
 let lookups=0
 page.on('request',r=>{if(r.url().includes('/voice-answer?'))lookups++})
 await emit({type:'response.created',response:{id:'resp_TEST_NOT_PERSISTED'}})
 await emit({type:'response.output_text.done',response_id:'resp_TEST_NOT_PERSISTED',text:'TEST未保存の回答'})
 await emit({type:'response.done',response:{id:'resp_TEST_NOT_PERSISTED',status:'completed',output:[{type:'message',role:'assistant',content:[{type:'output_text',text:'TEST未保存の回答'}]}]}})
 await expect.poll(()=>lookups).toBeGreaterThan(1)
 await page.getByRole('button',{name:'接客終了',exact:true}).click()
 await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
 const countAtEnd=lookups;await page.waitForTimeout(400);expect(lookups).toBe(countAtEnd)
 await expect(page.locator('.avatar-stage')).toHaveClass(/idle/)
 result.checks.end_cancels_persisted_event_wait_timer='PASS'
 await page.screenshot({path:path.join(out,'test-tts-ended.png'),fullPage:true})
 expect(result.page_errors).toEqual([]);result.status='PASS'
}catch(error){result.status='FAIL';result.error=String(error);await page.screenshot({path:path.join(out,'test-chrome-failure.png'),fullPage:true}).catch(()=>{});throw error}
finally{await fs.writeFile(path.join(out,'chrome_result.json'),JSON.stringify(result,null,2));await context.close();await browser.close()}
