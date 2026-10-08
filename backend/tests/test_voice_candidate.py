from types import SimpleNamespace
from xml.etree import ElementTree as ET
import pytest
from app.services.azure_tts import AzureTtsAdapter, speech_ssml
from app.models.domain import AppError
from app.services.ai import voice_instructions, CONVERSATION_STYLE


def config(**changes):
    values = dict(azure_speech_key='TEST', azure_speech_region='japaneast', azure_speech_voice='ja-JP-NanamiNeural', azure_speech_style='chat', azure_speech_rate='+15%', azure_speech_styledegree='1.15')
    return SimpleNamespace(**dict(values, **changes))


def test_selected_candidate_and_unchanged_text():
    cfg = config(); adapter = AzureTtsAdapter(cfg); adapter.check_config()
    root = ET.fromstring(speech_ssml('借入額は3,000万円、35年です。', adapter.voice, adapter.style, adapter.rate, adapter.styledegree))
    ns = {'s':'http://www.w3.org/2001/10/synthesis', 'm':'https://www.w3.org/2001/mstts'}
    voice = root.find('s:voice', ns); style = voice.find('m:express-as', ns); prosody = style.find('s:prosody', ns)
    assert voice.attrib == {'name':'ja-JP-NanamiNeural'}
    assert style.attrib == {'style':'chat', 'styledegree':'1.15'}
    assert prosody.attrib == {'rate':'+15%'}
    assert ''.join(prosody.itertext()) == '借入額は3,000万円、35年です。'


@pytest.mark.parametrize('changes', [{'azure_speech_rate':'+101%'}, {'azure_speech_rate':'fast'}, {'azure_speech_styledegree':'NaN'}, {'azure_speech_styledegree':'2.1'}, {'azure_speech_style':''}])
def test_invalid_candidate_rejected(changes):
    with pytest.raises(AppError): AzureTtsAdapter(config(**changes)).check_config()


def test_all_response_instructions_keep_business_and_style():
    for task in ['開場', 'Tool後の回答', 'スタッフ引継ぎ', 'エラー説明']:
        instruction = voice_instructions(task)
        assert CONVERSATION_STYLE in instruction
        for rule in ['接客の発話は常に日本語', '月返済額を自分で計算しない', '商品を明示して選ぶまで計算しない', 'call_staff', '必要な場合だけ一つ']:
            assert rule in instruction
