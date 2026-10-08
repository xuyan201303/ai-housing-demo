"""TEST ONLY: electronic beep, NOT Japanese speech or naturalness evidence.

Not selectable via production configuration. Explicit injection into isolated tests.
"""
import asyncio
import io
import math
import struct
import wave
from app.services.voice_output import SpeechAudio


class FakeTtsProvider:
    test_only = True

    def __init__(self, delay=0, duration=0.3):
        self.calls = []
        self.cancelled = 0
        self.delay = delay
        self.duration = duration
        self.fail = False

    async def synthesize(self, display_text):
        self.calls.append(display_text)
        try:
            await asyncio.sleep(self.delay)
            if self.fail:
                raise RuntimeError('TEST_ONLY_failure_not_an_Azure_call')
            raw = io.BytesIO()
            with wave.open(raw, 'wb') as wav:
                wav.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                wav.writeframes(b''.join(struct.pack('<h', int(1200 * math.sin(2 * math.pi * 660 * i / 24000)))
                                         for i in range(int(24000 * self.duration))))
            return SpeechAudio(raw.getvalue(), test_only=True)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
