"""Real-provider user acceptance entry. No provider calls until user starts.
Existing isolated TEST publications are copied once; normal DB is never opened.
"""
import os
import sqlite3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/phase1_user_10min_preparation'
TARGET = OUT / 'user-test.db'
SOURCE = ROOT / 'evidence/japanese_voice_architecture_phase1/ui-test.db'
OUT.mkdir(parents=True, exist_ok=True)
if not TARGET.exists():
    with sqlite3.connect(f'file:{SOURCE}?mode=ro', uri=True) as source:
        if not source.execute('SELECT count(*) FROM versions').fetchone()[0]:
            raise RuntimeError('Existing isolated TEST publications required')
        with sqlite3.connect(TARGET) as destination:
            source.backup(destination)
os.environ.update(DATABASE_URL='sqlite:///./evidence/phase1_user_10min_preparation/user-test.db',
    UPLOAD_DIR='./evidence/phase1_user_10min_preparation/uploads',
    FRONTEND_ORIGIN='http://localhost:5174', VOICE_OUTPUT_PROVIDER='azure_tts',
    AZURE_SPEECH_VOICE='ja-JP-NanamiNeural', AZURE_SPEECH_STYLE='chat',
    AZURE_SPEECH_RATE='+15%', AZURE_SPEECH_STYLEDEGREE='1.15')
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.services.azure_tts import AzureTtsAdapter
if not settings.api_key or not settings.staff_password:
    raise RuntimeError('Existing OpenAI / Staff configuration is required')
AzureTtsAdapter(settings).check_config()
if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=8001, log_level='warning')
