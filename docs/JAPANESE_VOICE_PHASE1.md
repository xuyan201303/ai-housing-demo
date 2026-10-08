# Japanese voice output — Phase 1

Implemented 2026-10-07. This phase adds a replaceable speech output; it does not establish that Japanese speech sounds natural. Normal `.env`, DB and published materials are unchanged. R1/R2 business projections and permitted AI evidence remain in effect.

## Two output modes

- `VOICE_OUTPUT_PROVIDER=openai_realtime` (unchanged default): current model, WebRTC microphone/VAD/Tools, OpenAI audio output and audio transcript events; existing voice remains `marin` unless already configured otherwise.
- `VOICE_OUTPUT_PROVIDER=azure_tts`: same configured Realtime model/WebRTC/input/transcription/VAD/Tools, **text output only**, then independent Azure Japanese speech. No automatic OpenAI audio fallback.

`VoiceOutputProvider` selects the mode centrally. The Azure adapter receives only the final stored assistant text; it cannot query materials, calculate loans or generate another answer. `speech_ssml` escapes text and supplies pronunciation aliases for a small bank-name dictionary, No. identifiers and percentages. Money/years retain their original numbers and units for Japanese TTS. Display text is unchanged. Actual readings still require listening.

Realtime text deltas/done update provisional subtitles. A completed `response.done` commits exactly one assistant event; cancelled, failed, tool-only and interrupted old responses do not become speech. The frontend waits briefly for the sideband's persisted event, then uses **its text as the final subtitle**. Audio transcript events are ignored in text mode. TTS reads that same saved text, without another AI call.

## Customer API additions

Every route requires the existing `X-Session-Token` for its own active, R2-valid Session. Existing R1 response fields were not widened.

| Route | Input | Explicit output |
|---|---|---|
| `GET /api/sessions/{id}/voice-output` | Own Session | `{provider: "openai_realtime" \| "azure_tts"}` |
| `GET /api/sessions/{id}/voice-answer?response_id=...` | Realtime response identifier, max 200 chars | `null` until the current answer is saved; otherwise `{assistant_event_id, display_text}` |
| `POST /api/sessions/{id}/speech` | **Only** `{assistant_event_id: positive integer}` | WAV audio; `Cache-Control: no-store`, `X-Assistant-Event-Id`, `X-Audio-Test-Only` |
| `POST /api/sessions/{id}/speech/cancel` | No text | `{status: "cancelled"}` |

Unknown speech request fields are rejected. Browser text is never used as the synthesis source. The server checks role, event ownership, latest speech target, pinned version, property context, source evidence revision, voice turn epoch and active Session. Revoked/expired sources invalidate replay. At most 2,000 display characters; one generation per Session; duplicate event requests share work/cache, retaining only the latest result. A 30-second overall timeout includes voice-list validation/synthesis. HTTP disconnect, VAD barge-in, end and server shutdown cancel work; cancellation cannot undo Azure usage already incurred. Usage audit stores event ID, input character count/hash and result, not secrets or arbitrary customer-visible raw fields. This is not a billing ledger.

## Playback and recovery

`thinking` during generation → `speaking` on actual HTML Audio playback → `idle` on end. `speech_started` immediately pauses/resets audio, aborts fetch/delayed event resolution and moves Avatar to `listening`. Late old responses are suppressed. End stops TTS/mic, revokes object URLs and closes the existing Realtime peer after authenticated server hangup. No delayed TTS timer can restart playback after end.

Azure failure explicitly displays `日本語音声生成に失敗しました`, retains subtitles and offers `音声を再試行`. The existing text input remains available. There is **no automatic switch** to OpenAI voice. Repeated retry after an actual failure may incur a new charge; successful same-event replays reuse the cached audio.

## Credentials and audition

Current status: **READY_FOR_AZURE_CREDENTIALS**. Only configure these on the Backend, without replacing existing `.env` entries:

```dotenv
AZURE_SPEECH_KEY=<your Speech resource key>
AZURE_SPEECH_REGION=<the resource region, for example japaneast>
AZURE_SPEECH_VOICE=ja-JP-NanamiNeural
# Optional; validated against the actual region's StyleList:
AZURE_SPEECH_STYLE=
# Keep the normal default unchanged until listening/explicit selection:
VOICE_OUTPUT_PROVIDER=openai_realtime
```

No key reaches the frontend. A configured candidate is not proof it is available: the adapter fetches this region's official voice list before the first synthesis and rejects unavailable voice/style. No account or resource is created by this project. Key/region alone suffice for the standalone audition's selected candidates; a voice is also needed when enabling Demo TTS later.

The next separately authorized paid step is **one voice-list request and up to nine synthesis requests** (three voices × these same three phrases), not a normal Demo switch. Default command is a network-free plan:

```sh
backend/.venv/bin/python scripts/azure_voice_audition.py --voices ja-JP-NanamiNeural ja-JP-ShioriNeural ja-JP-Nanami:DragonHDLatestNeural
```

Only after explicit paid authorization, add `--execute-paid` and an unused `--output evidence/azure_voice_audition_<date>` directory. Unavailable candidates/errors stop without retry or substitution. Nanami/Shiori and optional Nanami DragonHD/Sakura MAI are candidates, not a final selection. All audition voices use neutral style for a fair baseline; Nanami `customerservice` is a separately disclosed follow-up option when present in the region list. Original WAV, exact input/SSML, safe configuration, submitted character counts/API result and a relative-path `index.html` are retained. Azure REST returns audio, not a recognized output transcript or exact billed usage; neither is fabricated. Naturalness remains **WAITING_FOR_USER_LISTENING**.

## Isolated verification

`backend/tests/test_japanese_voice.py` exercises real routes/service logic with TEST transports and a **FakeTtsProvider electronic beep**. It cannot be selected through production config. `scripts/japanese_voice_test_server.py` uses its own `evidence/japanese_voice_architecture_phase1/ui-test.db`, ports 8018/5188 and a non-loopback network guard. TEST-only controls exist solely in that harness. Chrome uses a fake peer/VAD and silent synthetic input track, while decoding/playing actual Fake WAV via HTML Audio. This proves lifecycle behavior, not the physical Mac microphone, speakers, real API or Japanese naturalness.

```sh
HOUSING_TEST_EVIDENCE_DIR=evidence/japanese_voice_architecture_phase1/r2_regression_payloads backend/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm run build
```

The evidence override preserves frozen R2 capture files while running their unchanged assertions. No normal DB is opened by these checks. Paid calls in this phase: **0**. Evidence: `evidence/japanese_voice_architecture_phase1/acceptance.md`.

## Official protocol references (checked 2026-10-07)

- [OpenAI Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations): text output modalities, `response.output_text.delta/done`, `response.done`, existing WebRTC input route.
- [Azure Speech REST](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech): regional voice list, SSML synthesis, key stays on server and WAV output format.
- [Azure language and voice support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support): Japanese candidates and Nanami styles; region/account availability is checked at runtime, not assumed.
- [Azure HD voices](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/high-definition-voices) and [MAI voices](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/mai-voices): REST/SSML support differs by voice family; optional candidates remain subject to actual regional availability and successful synthesis/listening. No voice or model is substituted automatically.

Actual Azure/OpenAI text-only interoperability, latency/interrupt behavior with real services, Japanese pronunciation/naturalness and the user's physical mic/speaker ten-minute acceptance remain unverified. R1/R2's prior limitations remain: field boundaries do not classify secrets inside legal text fields or establish complete live transport confidentiality. Do not import real mixed confidential materials on the strength of this phase. Phase 2 is not started.
