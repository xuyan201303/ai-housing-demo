"""Explicitly approved paid audition only; no DB, mic, SDK or sample uploads."""
import argparse
import asyncio
import base64
import hashlib
import html
import json
import sys
import wave
from datetime import datetime
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings, validated_realtime_voice
from app.services.ai import VOICE_STYLE

SAMPLES = [
    'こんにちは。AI住宅コンシェルジュです。住宅購入や住宅ローンについて、お気軽にご相談ください。',
    '住宅購入では、ご希望や予算を整理し、資料と現地で条件を確認していきます。まず、どのような暮らしをご希望ですか。',
    'これは発音確認用の架空の例です。借入額は三千万円、返済期間は三十五年、年利は一点一九五パーセントです。実際の物件や融資条件のご案内ではありません。',
]

def write_page(dest, report, voices):
    escape = html.escape
    groups = []
    for voice in voices:
        cards = []
        for index, text in enumerate(SAMPLES, 1):
            row = next((r for r in report['results'] if r['voice'] == voice and r['sample'] == index), {})
            player = ('<audio controls preload="none" src="' + escape(row['audio_file']) + '"></audio>') if row.get('audio_bytes') else '<p>未生成 / 音声なし</p>'
            cards.append('<article><h3>サンプル ' + str(index) + '</h3>' + player +
                         '<p><b>テスト文</b><br>' + escape(text) + '</p><p><b>実際の出力字幕</b><br>' + escape(row.get('transcript', '未取得')) +
                         '</p><p>API: ' + escape(row.get('status', 'NOT_REQUESTED')) + '</p></article>')
        groups.append('<section><h2>' + escape(voice) + '</h2>' + ''.join(cards) + '</section>')
    page = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>日本語音色试听</title><style>body{font-family:system-ui;max-width:980px;margin:32px auto;padding:0 20px;background:#f4f6f8;color:#182735}article{background:white;padding:20px;margin:16px 0;border-radius:12px}audio{width:100%}p{line-height:1.7;white-space:pre-wrap}</style><h1>日本語音色试听</h1><p>原始音频・原始字幕。自動再生なし。発音テストの金額は実際の融資条件ではありません。自然度: WAITING_FOR_USER_LISTENING</p>' + ''.join(groups) + '<p><a href="result.json">usage / 実行記録</a></p></html>'
    (dest / 'index.html').write_text(page)


async def run(voices):
    if not settings.api_key:
        raise RuntimeError('API configuration is missing')
    dest = ROOT / 'evidence/voice_quality' / ('audition_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    dest.mkdir(parents=True)
    report = {'model': settings.realtime_model, 'input_kind': 'TEXT_PRONUNCIATION_SAMPLE_NOT_MIC_ACCEPTANCE',
              'style_sha256': hashlib.sha256(VOICE_STYLE.encode()).hexdigest(),
              'naturalness': 'WAITING_FOR_USER_LISTENING', 'results': [], 'sessions': [], 'response_requests': 0}
    try:
        for voice in voices:
            session_record = {'voice': voice, 'status': 'CONNECTING'}
            report['sessions'].append(session_record)
            # Voice is set before any audio, in a new connection for each candidate.
            async with websockets.connect('wss://api.openai.com/v1/realtime?model=' + settings.realtime_model,
                    additional_headers={'Authorization': 'Bearer ' + settings.api_key}, max_size=4_000_000) as ws:
                await ws.send(json.dumps({'type': 'session.update', 'session': {
                    'type': 'realtime', 'instructions': VOICE_STYLE,
                    'output_modalities': ['audio'], 'tools': [],
                    'audio': {'output': {'voice': voice, 'format': {'type': 'audio/pcm', 'rate': 24000}},
                              'input': {'turn_detection': None}}}}))
                while True:
                    event = json.loads(await asyncio.wait_for(ws.recv(), 30))
                    with (dest / (voice + '_events.jsonl')).open('a') as log:
                        log.write(json.dumps(event, ensure_ascii=False) + '\n')
                    if event['type'] == 'session.created':
                        session_record['session_id'] = event.get('session', {}).get('id')
                    if event['type'] == 'error':
                        raise RuntimeError('Realtime session configuration failed; no retry')
                    if event['type'] == 'session.updated':
                        session_record['status'] = 'CONFIGURED'
                        session_record['actual_model'] = event.get('session', {}).get('model')
                        if session_record['actual_model'] != settings.realtime_model:
                            raise RuntimeError('Returned model differs from configured model; stopped')
                        break
                for index, sample in enumerate(SAMPLES, 1):
                    entry = {'voice': voice, 'sample': index, 'requested_text': sample, 'status': 'RUNNING'}
                    report['results'].append(entry)
                    pcm = bytearray(); transcript = ''
                    report['response_requests'] += 1
                    await ws.send(json.dumps({'type': 'response.create', 'response': {
                        'conversation': 'none', 'input': [], 'tools': [], 'tool_choice': 'none',
                        'max_output_tokens': 450,
                        'instructions': VOICE_STYLE + '\nこれは音色比較の独立テストです。住宅接客の事実回答ではありません。次の文章だけを自然に読み上げてください:\n' + sample}}))
                    try:
                        while True:
                            event = json.loads(await asyncio.wait_for(ws.recv(), 60))
                            kind = event['type']
                            if kind not in {'response.output_audio.delta', 'response.audio.delta'}:
                                with (dest / (voice + '_events.jsonl')).open('a') as log:
                                    log.write(json.dumps(event, ensure_ascii=False) + '\n')
                            if kind in {'response.output_audio.delta', 'response.audio.delta'}:
                                pcm.extend(base64.b64decode(event['delta']))
                            elif kind in {'response.output_audio_transcript.done', 'response.audio_transcript.done'}:
                                transcript = event.get('transcript', '')
                            elif kind == 'error':
                                raise RuntimeError('Realtime response error; no retry')
                            elif kind == 'response.done':
                                entry['status'] = event['response'].get('status')
                                entry['usage'] = event['response'].get('usage')
                                if entry['status'] != 'completed':
                                    raise RuntimeError('Incomplete response; no retry')
                                break
                    finally:
                        filename = f'{voice}_{index}.wav'
                        with wave.open(str(dest / filename), 'wb') as output:
                            output.setnchannels(1); output.setsampwidth(2); output.setframerate(24000); output.writeframes(pcm)
                        entry.update(audio_file=filename, transcript=transcript, audio_bytes=len(pcm))
                        (dest / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
            session_record['status'] = 'COMPLETED'
    except Exception as exc:
        report['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        write_page(dest, report, voices)
        print('OUTPUT_DIRECTORY=' + str(dest), flush=True)
        (dest / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(str(dest))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-paid', action='store_true', help='Use only after explicit approval')
    parser.add_argument('--voices', nargs='+', default=['marin', 'cedar', 'coral'])
    args = parser.parse_args()
    if not args.execute_paid:
        parser.error('No API call performed. Explicit paid audition approval is required.')
    if not 1 <= len(args.voices) <= 3 or len(set(args.voices)) != len(args.voices):
        parser.error('Choose up to three distinct voices')
    asyncio.run(run([validated_realtime_voice(v) for v in args.voices]))
