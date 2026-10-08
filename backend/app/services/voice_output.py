"""Output selection only. No housing decisions, Tools, or AI text rewriting."""
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class VoiceMode(str, Enum):
    OPENAI_REALTIME_AUDIO = 'openai_realtime'
    JAPANESE_TTS = 'azure_tts'


@dataclass(frozen=True)
class SpeechAudio:
    data: bytes
    content_type: str = 'audio/wav'
    test_only: bool = False


class TtsAdapter(Protocol):
    async def synthesize(self, display_text: str) -> SpeechAudio: ...


@dataclass(frozen=True)
class VoiceOutputProvider:
    mode: VoiceMode
    adapter: TtsAdapter | None = None

    @property
    def modalities(self):
        return ['text'] if self.mode == VoiceMode.JAPANESE_TTS else ['audio']


def voice_output(settings):
    mode = VoiceMode(getattr(settings, 'voice_output_provider', 'openai_realtime'))
    if mode == VoiceMode.OPENAI_REALTIME_AUDIO:
        return VoiceOutputProvider(mode)
    from app.services.azure_tts import AzureTtsAdapter
    return VoiceOutputProvider(mode, AzureTtsAdapter(settings))
