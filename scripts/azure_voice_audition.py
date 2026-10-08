"""Explicitly gated audition only. No DB, mic, Realtime or default-voice changes."""
import argparse
import asyncio
import html
import json
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.models.domain import AppError
from app.services.azure_tts import AzureTtsAdapter, speech_ssml

PHRASES = [
    'こんにちは。AI住宅コンシェルジュです。住宅購入や住宅ローンについて、お気軽にご相談ください。',
    '住宅購入では、ご希望やご予算を整理しながら、条件に合う住まいをご案内いたします。まず、どのような暮らしをご希望ですか。',
    'これは発音確認用です。借入額は三千万円、返済期間は三十五年、参考金利は年一・一九五パーセントです。',
]
CANDIDATES = ['ja-JP-NanamiNeural', 'ja-JP-ShioriNeural', 'ja-JP-Nanami:DragonHDLatestNeural', 'ja-JP-Sakura:MAI-Voice-2-Flash']


async def execute(args):
    names = args.voices
    if len(names) > 3 or len(set(names)) != len(names) or any(v not in CANDIDATES for v in names):
        raise SystemExit('Select 1-3 distinct supported audition candidates')
    plan = {'voices': names, 'phrases': PHRASES, 'maximum_synthesis_requests': len(names) * 3,
            'voice_list_requests': 1, 'paid_execution': args.execute_paid,
            'naturalness': 'WAITING_FOR_USER_LISTENING'}
    if not args.execute_paid:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return  # Before adapter, directories, voice-list or network execution.
    adapter = AzureTtsAdapter(SimpleNamespace(azure_speech_key=settings.azure_speech_key,
        azure_speech_region=settings.azure_speech_region, azure_speech_voice=names[0], azure_speech_style=''))
    adapter.check_config()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT / 'evidence'):
        raise SystemExit('Audition output must be in project evidence')
    out.mkdir(parents=True, exist_ok=False)  # Preserve original previous auditions.
    record = {**plan, 'region': adapter.region, 'output_format': 'riff-24khz-16bit-mono-pcm',
              'results': [], 'status': 'RUNNING', 'synthesis_requests': 0, 'voice_list_requests_attempted': 0,
              'usage_note': 'Submitted character counts; REST does not provide actual billed usage or price.'}
    try:
        record['voice_list_requests_attempted'] = 1
        available = await adapter.voices()
        record['available_candidates'] = {v: {'available': v in available, 'styles': available.get(v, {}).get('StyleList', [])} for v in CANDIDATES}
        if any(v not in available for v in names):
            raise AppError('AZURE_VOICE_UNAVAILABLE', 'One or more selected voices are unavailable in this region')
        # Neutral style for all voices: fair baseline. customerservice is an optional,
        # separately disclosed follow-up comparison, never silently applied to Nanami.
        for index, voice in enumerate(names):
            adapter.voice = voice
            for phrase_index, text in enumerate(PHRASES):
                record['synthesis_requests'] += 1
                audio = await adapter.synthesize(text)
                stem = f'voice-{index + 1}-phrase-{phrase_index + 1}'
                (out / f'{stem}.wav').write_bytes(audio.data)
                (out / f'{stem}.ssml').write_text(speech_ssml(text, voice))
                record['results'].append({'voice': voice, 'style': 'neutral', 'display_text': text,
                    'submitted_characters': len(text), 'audio': f'{stem}.wav', 'bytes': len(audio.data), 'api_result': 'SUCCESS',
                    'actual_output_transcript': None, 'transcript_note': 'Azure TTS returns audio, not a recognized output transcript; listening remains required.'})
        record['status'] = 'GENERATED_WAITING_FOR_USER_LISTENING'
    except Exception as exc:
        record['status'] = 'FAILED_STOPPED_NO_RETRY'
        record['error_code'] = exc.code if isinstance(exc, AppError) else type(exc).__name__
    finally:
        (out / 'results.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
        sections = []
        for voice in names:
            cards = ''.join(f'<p>{html.escape(r["display_text"])}</p><audio controls preload="none" src="{r["audio"]}"></audio>' for r in record['results'] if r['voice'] == voice)
            sections.append(f'<section><h2>{html.escape(voice)} / neutral</h2>{cards or "生成なし"}</section>')
        (out / 'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>日本語音声试听</title><h1>WAITING_FOR_USER_LISTENING</h1><p>金額等は発音確認用。実際のローン試算ではありません。</p>' + ''.join(sections) + '</html>')
    print(json.dumps({'status': record['status'], 'output': str(out), 'synthesis_requests': record['synthesis_requests']}, ensure_ascii=False))
    if record['status'].startswith('FAILED'):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-paid', action='store_true')
    parser.add_argument('--voices', nargs='+', default=CANDIDATES[:2])
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence/azure_voice_audition')
    asyncio.run(execute(parser.parse_args()))
