"""Paid-gated A/B/C Nanami/chat SSML audition; no application changes."""
import argparse
import asyncio
import hashlib
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from xml.sax.saxutils import quoteattr
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))
from app.config import settings
from app.services.azure_tts import AzureTtsAdapter, pronunciation_text
from azure_voice_audition import PHRASES

VOICE = 'ja-JP-NanamiNeural'
GROUPS = [('A', '+10%', '1.0'), ('B', '+15%', '1.15'), ('C', '+20%', '1.15')]
SUPPORT = ROOT / 'evidence/nanami_style_audition_20261007_235302'


def ssml(text, rate, degree):
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="ja-JP">'
        f'<voice name="{VOICE}"><mstts:express-as style="chat" styledegree={quoteattr(degree)}>'
        f'<prosody rate={quoteattr(rate)}>{pronunciation_text(text)}</prosody></mstts:express-as></voice></speak>')


def page(out, report):
    groups = []
    for label, rate, degree in GROUPS:
        cards = []
        for number, text in enumerate(PHRASES, 1):
            row = next((r for r in report['results'] if r['group'] == label and r['phrase'] == number), {})
            player = f'<audio controls preload="none" src="{row["audio"]}"></audio>' if row.get('audio') else '<p>未生成</p>'
            cards.append(f'<article><h3>サンプル {number}</h3><p>{html.escape(text)}</p>{player}</article>')
        groups.append(f'<section><h2>{label} / Nanami chat</h2><p>rate={rate} / styledegree={degree}</p>{"".join(cards)}</section>')
    (out / 'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nanami chat A/B/C</title><style>body{font-family:system-ui;max-width:960px;margin:32px auto;padding:0 20px;background:#f5f7f4;color:#24382b}article{background:white;padding:20px;margin:16px 0;border-radius:12px}audio{width:100%}p{line-height:1.7}</style><h1>Nanami / chat — A/B/C比較</h1><p>WAITING_FOR_USER_LISTENING</p><p>全グループ同じ3文章・音色・chat。pitch/volume は指定せず既定値を保持。SSML の rate と styledegree のみ変更。原始WAV、再生速度の加工なし。</p><p>金額等は発音確認用。表示は入力文であり、出力音声の転写ではありません。</p>' + ''.join(groups) + '<p><a href="results.json">実行記録</a></p></html>')


async def execute(args):
    if not args.execute_paid:
        print(json.dumps({'voice': VOICE, 'style': 'chat', 'groups': GROUPS,
            'phrases': PHRASES, 'maximum_synthesis_requests': 9, 'new_voice_list_requests': 0}, ensure_ascii=False));return 0
    adapter = AzureTtsAdapter(SimpleNamespace(azure_speech_key=settings.azure_speech_key,
        azure_speech_region=settings.azure_speech_region, azure_speech_voice=VOICE, azure_speech_style='chat'))
    adapter.check_config()
    if settings.voice_output_provider != 'openai_realtime':
        raise SystemExit('STOPPED: normal default is not openai_realtime')
    support = json.loads((SUPPORT / 'results.json').read_text())
    if support['region'] != adapter.region or 'chat' not in support['nanami_voice_list_entry'].get('StyleList', []):
        raise SystemExit('STOPPED: prior actual regional list does not establish chat support for this configuration')
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'evidence'):raise SystemExit('Output must be inside project evidence')
    out.mkdir(parents=True, exist_ok=False)
    protected = [ROOT / '.env'] + list((ROOT / 'backend/app').rglob('*.py')) + [p for p in (ROOT / 'frontend/src').rglob('*') if p.is_file()]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    report = {'voice': VOICE, 'style': 'chat', 'region': adapter.region, 'groups': GROUPS,
        'pitch': 'DEFAULT_UNSPECIFIED', 'volume': 'DEFAULT_UNSPECIFIED', 'synthesis_requests': 0,
        'new_voice_list_requests': 0, 'voice_support_evidence': str(SUPPORT.relative_to(ROOT) / 'results.json'),
        'voice_support_note': 'Reused prior actual voice list from the same region, not a new query.',
        'nanami_voice_list_entry': support['nanami_voice_list_entry'],
        'results': [], 'status': 'RUNNING', 'naturalness': 'WAITING_FOR_USER_LISTENING',
        'openai_calls': 0, 'actual_output_transcript': None, 'exact_billed_usage': None}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            for label, rate, degree in GROUPS:
                for number, text in enumerate(PHRASES, 1):
                    stem = f'nanami-chat-{label}-{number}';content = ssml(text, rate, degree)
                    (out / f'{stem}.ssml').write_text(content)
                    row = {'group': label, 'voice': VOICE, 'style': 'chat', 'rate': rate, 'styledegree': degree,
                        'phrase': number, 'display_text': text, 'submitted_characters': len(text),
                        'ssml': f'{stem}.ssml', 'status': 'REQUESTED'}
                    report['results'].append(row);report['synthesis_requests'] += 1
                    response = await client.post(f'https://{adapter.region}.tts.speech.microsoft.com/cognitiveservices/v1',
                        headers={'Ocp-Apim-Subscription-Key': adapter.key, 'Content-Type': 'application/ssml+xml',
                            'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm', 'User-Agent': 'housing-demo-nanami-chat-tuning'},
                        content=content.encode('utf-8'))
                    row['http_status'] = response.status_code
                    if response.is_error or not response.content.startswith(b'RIFF'):
                        row['status'] = 'FAILED';raise RuntimeError('SYNTHESIS_FAILED_HTTP_' + str(response.status_code))
                    (out / f'{stem}.wav').write_bytes(response.content)
                    row.update(status='SUCCESS', audio=f'{stem}.wav', bytes=len(response.content))
        report['status'] = 'GENERATED_WAITING_FOR_USER_LISTENING'
    except Exception as exc:
        report['status'] = 'FAILED_STOPPED_NO_RETRY'
        report['error_code'] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        if report['results'] and report['results'][-1]['status'] == 'REQUESTED':report['results'][-1]['status'] = 'FAILED'
    finally:
        report['protected_files_unchanged'] = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value for name, value in before.items())
        (out / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2));page(out, report)
    print(json.dumps({'status': report['status'], 'output': str(out), 'synthesis_requests': report['synthesis_requests'],
        'audio_files': sum(r['status'] == 'SUCCESS' for r in report['results']), 'error_code': report.get('error_code')}, ensure_ascii=False))
    return 1 if report['status'].startswith('FAILED') else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--execute-paid', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence' / ('nanami_chat_tuning_' + datetime.now().strftime('%Y%m%d_%H%M%S')))
    sys.exit(asyncio.run(execute(parser.parse_args())))
