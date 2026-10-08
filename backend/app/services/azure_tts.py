"""Azure REST adapter, ja-JP only, no retries or silent provider fallback.

Voice availability/styles are verified against this resource's region list.
SSML escapes all text and only changes pronunciation, never display facts.
"""
import re
from xml.sax.saxutils import escape, quoteattr
import httpx
from app.models.domain import AppError
from app.services.voice_output import SpeechAudio

PRONUNCIATIONS = {'三菱UFJ銀行': 'みつびしユーエフジェーぎんこう'}
TOKEN = re.compile(r'三菱UFJ銀行|No\.\s*(\d+)|([\d,]+(?:\.\d+)?)\s*[%％]')


def pronunciation_text(text):
    """Original token retained as sub content; aliases retain every numeric digit."""
    parts, start = [], 0
    for match in TOKEN.finditer(text):
        parts.append(escape(text[start:match.start()]))
        token = match.group(0)
        if token in PRONUNCIATIONS:
            alias = PRONUNCIATIONS[token]
        elif match.group(1):
            alias = match.group(1) + '号地'
        else:
            # Decimal fraction read digit by digit, not as an integer (195).
            amount = match.group(2).replace(',', '')
            whole, dot, fraction = amount.partition('.')
            alias = whole + ('点' + '・'.join(fraction) if dot else '') + 'パーセント'
        parts.append(f'<sub alias={quoteattr(alias)}>{escape(token)}</sub>')
        start = match.end()
    parts.append(escape(text[start:]))
    return ''.join(parts)


def speech_ssml(display_text, voice, style='', rate='', styledegree=''):
    content = pronunciation_text(display_text)
    if rate:
        content = f'<prosody rate={quoteattr(rate)}>{content}</prosody>'
    if style:
        degree = f' styledegree={quoteattr(styledegree)}' if styledegree else ''
        content = f'<mstts:express-as style={quoteattr(style)}{degree}>{content}</mstts:express-as>'
    return ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="ja-JP">'
            f'<voice name={quoteattr(voice)}>{content}</voice></speak>')


class AzureTtsAdapter:
    def __init__(self, settings):
        self.key = getattr(settings, 'azure_speech_key', '')
        self.region = getattr(settings, 'azure_speech_region', '')
        self.voice = getattr(settings, 'azure_speech_voice', '')
        self.style = getattr(settings, 'azure_speech_style', '')
        self.rate = getattr(settings, 'azure_speech_rate', '')
        self.styledegree = getattr(settings, 'azure_speech_styledegree', '')
        self.available = None

    @property
    def configured(self):
        return bool(self.key and self.region and self.voice)

    def check_config(self):
        if not self.configured:
            raise AppError('AZURE_NOT_CONFIGURED', '日本語音声生成に必要な Azure 設定が未完了です。文字でご相談いただけます。', 503)
        if not re.fullmatch(r'[a-z][a-z0-9]{1,39}', self.region) or not re.fullmatch(r'ja-JP-[A-Za-z0-9:._-]+', self.voice):
            raise AppError('AZURE_CONFIG_INVALID', '日本語音声の設定を管理者にご確認ください。', 503)
        if self.rate and (not re.fullmatch(r'[+-]\d{1,3}%', self.rate) or not -50 <= int(self.rate[:-1]) <= 100):
            raise AppError('AZURE_CONFIG_INVALID', '日本語音声の速度設定を管理者にご確認ください。', 503)
        if self.styledegree and (not re.fullmatch(r'\d+(?:\.\d+)?', self.styledegree) or not 0.01 <= float(self.styledegree) <= 2 or not self.style):
            raise AppError('AZURE_CONFIG_INVALID', '日本語音声のスタイル設定を管理者にご確認ください。', 503)

    async def voices(self):
        self.check_config()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/voices/list', headers={'Ocp-Apim-Subscription-Key': self.key})
        if response.is_error:
            raise AppError('AZURE_VOICE_LIST_FAILED', '日本語音声の利用可否を確認できませんでした。', 502)
        self.available = {v['ShortName']: v for v in response.json() if v.get('Locale') == 'ja-JP' and v.get('ShortName')}
        return self.available

    async def synthesize(self, display_text):
        self.check_config()
        available = self.available if self.available is not None else await self.voices()
        if self.voice not in available or (self.style and self.style not in available[self.voice].get('StyleList', [])):
            raise AppError('AZURE_VOICE_UNAVAILABLE', 'このリージョンでは指定した日本語音声・スタイルを利用できません。', 503)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1',
                headers={'Ocp-Apim-Subscription-Key': self.key, 'Content-Type': 'application/ssml+xml',
                         'X-Microsoft-OutputFormat': 'riff-24khz-16bit-mono-pcm', 'User-Agent': 'housing-demo-voice-phase1'},
                content=speech_ssml(display_text, self.voice, self.style, self.rate, self.styledegree).encode('utf-8'))
        if response.is_error or not response.content.startswith(b'RIFF') or len(response.content) > 10_000_000:
            raise AppError('AZURE_SYNTHESIS_FAILED', '日本語音声生成に失敗しました。字幕をご確認ください。', 502)
        return SpeechAudio(response.content)
