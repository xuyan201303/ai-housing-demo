import { useCallback, useEffect, useRef, useState } from 'react'
import { api, errorText, post } from './api'
import type { Json } from './api'
import type { CustomerSessionWithToken } from './customerTypes'
import { JapaneseSpeechPlayback } from './voiceOutput'
import type { VoiceProvider } from './voiceOutput'
export type ConciergeState = 'idle' | 'listening' | 'thinking' | 'speaking'
export default function useVoice() {
  const peer = useRef<RTCPeerConnection|null>(null)
  const stream = useRef<MediaStream|null>(null)
  const playback = useRef<HTMLAudioElement|null>(null)
  const generation = useRef(0)
  const audioPlaying = useRef(false)
  const inputSpeaking = useRef(false)
  const awaitingResponse = useRef(false)
  const responseInProgress = useRef(false)
  const ttsPending = useRef(false)
  const speech = useRef<JapaneseSpeechPlayback|null>(null)
  const [state,setState]=useState<ConciergeState>('idle')
  const [status,setStatus]=useState('idle')
  const [error,setError]=useState('')
  const [subtitle,setSubtitle]=useState('')
  const [customerSubtitle,setCustomerSubtitle]=useState('')
  const [muted,setMuted]=useState(false)
  const [sessionId,setSessionId]=useState('')
  const [ttsError,setTtsError]=useState('')
  const [ttsTestOnly,setTtsTestOnly]=useState(false)
  const resetFlow = useCallback(()=>{
    audioPlaying.current=false;inputSpeaking.current=false
    awaitingResponse.current=false;responseInProgress.current=false;ttsPending.current=false
  },[])
  const syncState = useCallback(()=>{
    setState(inputSpeaking.current?'listening':audioPlaying.current?'speaking':responseInProgress.current || awaitingResponse.current || ttsPending.current?'thinking':'idle')
  },[])
  const silence = useCallback(()=> {
    // Ignore late media events while the backend performs an orderly hangup.
    // Keep the peer open until its authenticated end request completes.
    generation.current += 1
    speech.current?.stop(true)
    if(stream.current){stream.current.getTracks().forEach(track=>track.stop());stream.current=null}
    playback.current?.pause()
    resetFlow()
    setState('idle');setMuted(true)
  },[resetFlow])
  const stop = useCallback(()=> {
    generation.current += 1
    speech.current?.stop(true);speech.current=null
    if(peer.current){peer.current.onconnectionstatechange=null;peer.current.ontrack=null;peer.current.close();peer.current=null}
    if(stream.current){stream.current.getTracks().forEach(track=>track.stop());stream.current=null}
    if(playback.current){playback.current.pause();playback.current.srcObject=null;playback.current=null}
    resetFlow()
    setState('idle');setStatus('idle');setMuted(false)
  },[resetFlow])
  useEffect(()=>()=>{stop()},[stop])
  async function connect(session:CustomerSessionWithToken, microphone:MediaStream) {
    stop();const current=++generation.current
    stream.current=microphone;setSessionId(session.id);setError('');setSubtitle('');setCustomerSubtitle('');setStatus('connecting')
    setTtsError('');setTtsTestOnly(false)
    let provider:VoiceProvider='openai_realtime'
    try{provider=(await api<{provider:VoiceProvider}>(`/sessions/${session.id}/voice-output`,{},session.token)).provider}
    catch(error){stop();throw error}
    if(generation.current!==current)return
    const textMode=provider==='azure_tts'
    if(textMode)speech.current=new JapaneseSpeechPlayback({text:setSubtitle,error:setTtsError,test:setTtsTestOnly,
      playing:value=>{audioPlaying.current=value;syncState()},pending:value=>{ttsPending.current=value;syncState()}})
    const rtc=new RTCPeerConnection();peer.current=rtc
    const audio=new Audio();audio.autoplay=true;playback.current=audio
    const fail=(message:string)=>{if(generation.current!==current)return;stop();setError(message);setStatus('error')}
    rtc.ontrack=event=>{if(generation.current!==current || textMode)return;audio.srcObject=event.streams[0] || new MediaStream([event.track]);audio.play().catch(()=>fail('音声の再生が許可されませんでした。接客を終了し、ブラウザーの音声設定をご確認ください。'))}
    rtc.onconnectionstatechange=()=>{if(generation.current!==current)return;if(['failed','disconnected','closed'].includes(rtc.connectionState))fail('音声接続が切れました。接客を終了して、改めて開始してください。')}
    microphone.getTracks().forEach(track=>rtc.addTrack(track,microphone))
    const channel=rtc.createDataChannel('oai-events')
    let inputEpoch=0
    const responseEpochs=new Map<string,number>()
    const spokenResponses=new Set<string>()
    channel.onopen=()=>{if(generation.current!==current)return;setStatus('connected');api(`/sessions/${session.id}/realtime/greet`,post(),session.token).catch(error=>fail(errorText(error)))}
    channel.onclose=()=>{if(generation.current===current)fail('音声の制御接続が切れました。接客を終了して再接続してください。')}
    channel.onerror=()=>fail('音声データの通信に失敗しました。接客を終了して再接続してください。')
    channel.onmessage=event=>{
      if(generation.current!==current)return
      let data:Json
      try{data=JSON.parse(event.data)}catch{return}
      switch(data.type){
        case 'input_audio_buffer.speech_started':inputEpoch++;speech.current?.stop(true);inputSpeaking.current=true;awaitingResponse.current=true;setCustomerSubtitle('');syncState();break
        case 'input_audio_buffer.speech_stopped':inputSpeaking.current=false;awaitingResponse.current=true;syncState();break
        case 'conversation.item.input_audio_transcription.completed':setCustomerSubtitle(data.transcript || '');break
        case 'response.created':if(data.response?.id)responseEpochs.set(data.response.id,inputEpoch);responseInProgress.current=true;awaitingResponse.current=false;setSubtitle('');syncState();break
        case 'response.output_audio_transcript.delta':case 'response.audio_transcript.delta':if(!textMode)setSubtitle(current=>current+(data.delta || ''));break
        case 'response.output_audio_transcript.done':case 'response.audio_transcript.done':if(!textMode)setSubtitle(data.transcript || '');break
        case 'response.output_text.delta':if(textMode && responseEpochs.get(data.response_id)===inputEpoch)setSubtitle(current=>current+(data.delta || ''));break
        case 'response.output_text.done':if(textMode && responseEpochs.get(data.response_id)===inputEpoch)setSubtitle(data.text || '');break
        case 'output_audio_buffer.started':if(!textMode){audioPlaying.current=true;syncState()}break
        case 'output_audio_buffer.stopped':case 'output_audio_buffer.cleared':if(!textMode){audioPlaying.current=false;syncState()}break
        case 'response.done':
          responseInProgress.current=false
          if(data.response?.status==='failed'){fail('音声回答に失敗しました。API の設定と利用状況をご確認ください。');break}
          // A tool-only response can finish while its backend continuation is pending.
          if((data.response?.output || []).some((item:Json)=>item.type==='function_call'))awaitingResponse.current=true
          if(textMode && data.response?.status==='completed' && responseEpochs.get(data.response.id)===inputEpoch && !spokenResponses.has(data.response.id) && !inputSpeaking.current && (data.response?.output || []).some((item:Json)=>item.type==='message'&&item.role==='assistant'&&item.content?.some((part:Json)=>part.type==='output_text'&&part.text))){spokenResponses.add(data.response.id);void speech.current?.response(session,data.response.id)}
          syncState();break
        case 'error':fail('音声 API がエラーを返しました。接客を終了して再接続してください。');break
        // Function calls are controlled exclusively by the backend sideband.
        default:break
      }
    }
    try{
      const offer=await rtc.createOffer();await rtc.setLocalDescription(offer)
      const answer=await api<string>(`/sessions/${session.id}/realtime`,{method:'POST',headers:{'Content-Type':'application/sdp'},body:offer.sdp},session.token)
      if(generation.current!==current)return
      await rtc.setRemoteDescription({type:'answer',sdp:answer})
    }catch(error){fail(errorText(error));throw error}
  }
  function toggleMute(){if(!stream.current)return;const next=!muted;stream.current.getAudioTracks().forEach(track=>track.enabled=!next);setMuted(next);if(next){inputSpeaking.current=false;syncState()}}
  return {connect,silence,stop,toggleMute,state,status,error,subtitle,customerSubtitle,muted,sessionId,ttsError,ttsTestOnly,retrySpeech:()=>speech.current?.retry()}
}
