"""Standalone paid-gated Nanami style audition. No business/config/DB changes."""
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
STYLES = ['neutral', 'customerservice', 'chat']


def ssml(text, style):
    body = pronunciation_text(text)
    if style != 'neutral':
        body = f'<mstts:express-as style={quoteattr(style)} styledegree="1.0">{body}</mstts:express-as>'
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="ja-JP">'
            f'<voice name="{VOICE}">{body}</voice></speak>')


def page(out, report):
    groups = []
    for style in STYLES:
        cards = []
        for number, text in enumerate(PHRASES, 1):
            row = next((r for r in report['results'] if r['style'] == style and r['phrase'] == number), {})
            player = f'<audio controls preload="none" src="{row["audio"]}"></audio>' if row.get('audio') else '<p>未生成</p>'
            cards.append(f'<article><h3>サンプル {number}</h3><p>{html.escape(text)}</p>{player}</article>')
        groups.append(f'<section><h2>Nanami / {style}</h2>{"".join(cards)}</section>')
    (out / 'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nanami 接客スタイル比較</title><style>body{font-family:system-ui;max-width:960px;margin:32px auto;padding:0 20px;background:#f5f7f4;color:#24382b}article{background:white;padding:20px;margin:16px 0;border-radius:12px}audio{width:100%}p{line-height:1.7}</style><h1>Nanami 接客スタイル比較</h1><p>WAITING_FOR_USER_LISTENING — 日本人感・親和力・機械感・住宅営業員らしさをご確認ください。</p><p>同じ音色・文章。速度、pitch、volume は全て未指定（同じ既定値）。customerservice/chat は styledegree=1.0、neutral は style 指定なし。</p><p>金額等は発音確認用。実際のローン試算ではありません。表示は入力文であり、出力音声の転写ではありません。</p>' + ''.join(groups) + '<p><a href="results.json">実行記録</a> / <a href="voice_list.json">実際のvoice list</a></p></html>')


async def execute(args):
    if not args.execute_paid:
        print(json.dumps({'voice': VOICE, 'styles': STYLES, 'phrases': PHRASES,
            'maximum_list_requests': 1, 'maximum_synthesis_requests': 9, 'paid_execution': False}, ensure_ascii=False))
        return
    missing = [name for name, value in [('AZURE_SPEECH_KEY', settings.azure_speech_key), ('AZURE_SPEECH_REGION', settings.azure_speech_region)] if not value.strip()]
    if missing:
        print(json.dumps({'status': 'MISSING_CONFIGURATION', 'missing': missing}));return 1
    if settings.voice_output_provider != 'openai_realtime':
        print(json.dumps({'status': 'STOPPED_DEFAULT_IS_NOT_OPENAI_REALTIME'}));return 1
    adapter = AzureTtsAdapter(SimpleNamespace(azure_speech_key=settings.azure_speech_key,
        azure_speech_region=settings.azure_speech_region, azure_speech_voice=VOICE, azure_speech_style=''))
    adapter.check_config()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'evidence'):
        raise SystemExit('Output must be inside project evidence')
    out.mkdir(parents=True, exist_ok=False)
    protected = [ROOT / '.env'] + list((ROOT / 'backend/app').rglob('*.py'))
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    report = {'voice': VOICE, 'styles': STYLES, 'region': adapter.region,
        'styledegree': {'neutral': None, 'customerservice': 1.0, 'chat': 1.0},
        'prosody': {'rate': 'DEFAULT_UNSPECIFIED', 'pitch': 'DEFAULT_UNSPECIFIED', 'volume': 'DEFAULT_UNSPECIFIED'},
        'output_format': 'riff-24khz-16bit-mono-pcm', 'list_requests': 0, 'synthesis_requests': 0,
        'results': [], 'status': 'RUNNING', 'naturalness': 'WAITING_FOR_USER_LISTENING',
        'openai_calls': 0, 'actual_output_transcript': None, 'exact_billed_usage': None,
        'usage_note': 'Submitted display character counts only; not a bill or output transcript.',
        'official_style_reference': 'https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice'}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            report['list_requests'] += 1
            response = await client.get(f'https://{adapter.region}.tts.speech.microsoft.com/cognitiveservices/voices/list', headers={'Ocp-Apim-Subscription-Key': adapter.key})
            report['voice_list_http_status'] = response.status_code
            if response.is_error:
                raise RuntimeError('VOICE_LIST_HTTP_' + str(response.status_code))
            voices = response.json()
            (out / 'voice_list.json').write_text(json.dumps(voices, ensure_ascii=False, indent=2))
            voice = next((v for v in voices if v.get('ShortName') == VOICE and v.get('Locale') == 'ja-JP'), None)
            if not voice:
                raise RuntimeError('NANAMI_UNAVAILABLE')
            report['nanami_voice_list_entry'] = voice
            unsupported = [s for s in STYLES[1:] if s not in voice.get('StyleList', [])]
            if unsupported:
                report['unsupported_styles'] = unsupported
                raise RuntimeError('REQUESTED_STYLE_UNAVAILABLE')
            for style in STYLES:
                for number, text in enumerate(PHRASES, 1):
                    stem = f'nanami-{style}-{number}'
                    content = ssml(text, style)
                    (out / f'{stem}.ssml').write_text(content)
                    row = {'voice': VOICE, 'style': style, 'phrase': number, 'display_text': text,
                        'submitted_characters': len(text), 'ssml': f'{stem}.ssml', 'status': 'REQUESTED'}
                    report['results'].append(row)
                    report['synthesis_requests'] += 1
                    response = await client.post(f'https://{adapter.region}.tts.speech.microsoft.com/cognitiveservices/v1',
                        headers={'Ocp-Apim-Subscription-Key': adapter.key, 'Content-Type': 'application/ssml+xml',
                            'X-Microsoft-OutputFormat': report['output_format'], 'User-Agent': 'housing-demo-nanami-style-audition'},
                        content=content.encode('utf-8'))
                    row['http_status'] = response.status_code
                    if response.is_error or not response.content.startswith(b'RIFF'):
                        row['status'] = 'FAILED'
                        raise RuntimeError('SYNTHESIS_FAILED_HTTP_' + str(response.status_code))
                    (out / f'{stem}.wav').write_bytes(response.content)
                    row.update(status='SUCCESS', audio=f'{stem}.wav', bytes=len(response.content))
        report['status'] = 'GENERATED_WAITING_FOR_USER_LISTENING'
    except Exception as exc:
        report['status'] = 'FAILED_STOPPED_NO_RETRY'
        report['error_code'] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        if report['results'] and report['results'][-1]['status'] == 'REQUESTED':report['results'][-1]['status'] = 'FAILED'
    finally:
        report['protected_files_unchanged'] = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value for name, value in before.items())
        (out / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        page(out, report)
    print(json.dumps({'status': report['status'], 'output': str(out), 'list_requests': report['list_requests'],
        'synthesis_requests': report['synthesis_requests'], 'audio_files': sum(r['status'] == 'SUCCESS' for r in report['results']),
        'error_code': report.get('error_code')}, ensure_ascii=False))
    return 1 if report['status'].startswith('FAILED') else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-paid', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence' / ('nanami_style_audition_' + datetime.now().strftime('%Y%m%d_%H%M%S')))
    sys.exit(asyncio.run(execute(parser.parse_args())) or 0)
