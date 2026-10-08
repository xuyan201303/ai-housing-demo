// Output transport only. Business text always comes from the saved server event.
import type { CustomerSessionWithToken } from './customerTypes'
export type VoiceProvider = 'openai_realtime' | 'azure_tts'
type VoiceAnswer = {assistant_event_id:number,display_text:string}
const failure='日本語音声生成に失敗しました。字幕はそのままご確認いただけます。音声を再試行するか、文字でご相談ください。'

export class JapaneseSpeechPlayback {
  private controller:AbortController|null=null
  private audio:HTMLAudioElement|null=null
  private url:string|null=null
  private attempt=0
  private last:VoiceAnswer|null=null
  private session:CustomerSessionWithToken|null=null
  constructor(private callbacks:{text:(text:string)=>void,playing:(value:boolean)=>void,pending:(value:boolean)=>void,error:(text:string)=>void,test:(value:boolean)=>void}){}
  stop(clearLast=false){
    this.attempt++;this.controller?.abort();this.controller=null
    if(this.audio){this.audio.onplaying=null;this.audio.onended=null;this.audio.onerror=null;this.audio.pause();this.audio.removeAttribute('src');this.audio.load();this.audio=null}
    if(this.url){URL.revokeObjectURL(this.url);this.url=null}
    this.callbacks.playing(false);this.callbacks.pending(false)
    if(clearLast){this.last=null;this.session=null;this.callbacks.error('')}
  }
  private async json(path:string,signal:AbortSignal){
    const response=await fetch(`/api/sessions/${this.session!.id}${path}`,{headers:{'X-Session-Token':this.session!.token},signal})
    if(!response.ok)throw new Error(failure)
    return response.json() as Promise<VoiceAnswer|null>
  }
  async response(session:CustomerSessionWithToken,responseId:string){
    this.stop(true);this.session=session
    const attempt=this.attempt;const controller=new AbortController();this.controller=controller
    this.callbacks.pending(true)
    try{
      let answer:VoiceAnswer|null=null
      // Data channel and server sideband are independent: wait for the persisted event.
      for(let i=0;i<40&&!answer;i++){
        answer=await this.json(`/voice-answer?response_id=${encodeURIComponent(responseId)}`,controller.signal)
        if(!answer)await new Promise<void>((resolve,reject)=>{
          const abort=()=>{clearTimeout(timer);reject(new DOMException('Aborted','AbortError'))}
          const timer=setTimeout(()=>{controller.signal.removeEventListener('abort',abort);resolve()},100)
          controller.signal.addEventListener('abort',abort,{once:true})
          if(controller.signal.aborted)abort()
        })
      }
      if(!answer)throw new Error(failure)
      if(attempt!==this.attempt)return
      this.last=answer;this.callbacks.text(answer.display_text)
      await this.play(answer,attempt,controller)
    }catch{if(attempt===this.attempt){this.stop();this.callbacks.error(failure)}}
  }
  private async play(answer:VoiceAnswer,attempt:number,controller:AbortController){
    this.callbacks.error('');this.callbacks.pending(true)
    const response=await fetch(`/api/sessions/${this.session!.id}/speech`,{method:'POST',
      headers:{'Content-Type':'application/json','X-Session-Token':this.session!.token},
      body:JSON.stringify({assistant_event_id:answer.assistant_event_id}),signal:controller.signal})
    if(!response.ok)throw new Error(failure)
    const blob=await response.blob()
    if(attempt!==this.attempt)return
    this.callbacks.test(response.headers.get('X-Audio-Test-Only')==='true')
    this.url=URL.createObjectURL(blob);const audio=new Audio(this.url);this.audio=audio
    audio.onplaying=()=>{if(attempt===this.attempt){this.callbacks.pending(false);this.callbacks.playing(true)}}
    audio.onended=()=>{if(attempt===this.attempt)this.stop()}
    audio.onerror=()=>{if(attempt===this.attempt){this.stop();this.callbacks.error(failure)}}
    await audio.play()
  }
  async retry(){
    if(!this.last||!this.session)return
    const answer=this.last;this.stop();const attempt=this.attempt
    const controller=new AbortController();this.controller=controller
    try{await this.play(answer,attempt,controller)}catch{if(attempt===this.attempt){this.stop();this.callbacks.error(failure)}}
  }
}
