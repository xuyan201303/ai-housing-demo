import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env', override=False)


def project_path(value: str) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError('Demo storage must be within the project directory')
    return path


REALTIME_VOICES = frozenset({'alloy', 'ash', 'ballad', 'coral', 'echo', 'sage', 'shimmer', 'verse', 'marin', 'cedar'})


def validated_realtime_voice(value: str) -> str:
    if value not in REALTIME_VOICES:
        raise RuntimeError('OPENAI_REALTIME_VOICE must be a supported built-in Realtime voice')
    return value


class Settings:
    def __init__(self):
        url = os.getenv('DATABASE_URL', 'sqlite:///./data/housing.db')
        if not url.startswith('sqlite:///'):
            raise RuntimeError('Only SQLite is supported')
        self.database = project_path(url.removeprefix('sqlite:///'))
        self.upload_dir = project_path(os.getenv('UPLOAD_DIR', './uploads'))
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.text_model = os.getenv('OPENAI_TEXT_MODEL', 'gpt-4.1-mini')
        self.realtime_model = os.getenv('OPENAI_REALTIME_MODEL', 'gpt-realtime-2.1')
        self.realtime_voice = validated_realtime_voice(os.getenv('OPENAI_REALTIME_VOICE', 'marin'))
        self.voice_output_provider = os.getenv('VOICE_OUTPUT_PROVIDER', 'openai_realtime')
        if self.voice_output_provider not in {'openai_realtime', 'azure_tts'}:
            raise RuntimeError('VOICE_OUTPUT_PROVIDER must be openai_realtime or azure_tts')
        self.azure_speech_key = os.getenv('AZURE_SPEECH_KEY', '')
        self.azure_speech_region = os.getenv('AZURE_SPEECH_REGION', '')
        self.azure_speech_voice = os.getenv('AZURE_SPEECH_VOICE', '')
        self.azure_speech_style = os.getenv('AZURE_SPEECH_STYLE', '')
        self.azure_speech_rate = os.getenv('AZURE_SPEECH_RATE', '')
        self.azure_speech_styledegree = os.getenv('AZURE_SPEECH_STYLEDEGREE', '')
        self.admin_password = os.getenv('ADMIN_PASSWORD', '')
        self.staff_password = os.getenv('STAFF_PASSWORD', '')
        self.demo_mode = os.getenv('DEMO_MODE', 'demo')
        if self.demo_mode not in {'demo', 'test'}:
            raise RuntimeError('DEMO_MODE must be demo or test; neither enables fake responses')
        self.max_upload_bytes = min(int(os.getenv('MAX_UPLOAD_MB', '10')), 20) * 1024 * 1024
        self.frontend_origin = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')


settings = Settings()
