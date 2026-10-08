# HOUSING_V1_JAPANESE_VOICE_ARCHITECTURE — Phase 1

2026-10-07. Implementation status: **READY_FOR_AZURE_CREDENTIALS**. Paid OpenAI/Azure calls: **0**. Naturalness: **WAITING_FOR_USER_LISTENING**. Physical Mac microphone and speaker: **WAITING / NOT_TESTED**. No Phase 2 work started.

## Implemented

- Central `VoiceOutputProvider` and separate Azure ja-JP REST adapter. Default remains OpenAI Realtime audio/marin; current Realtime model remains configured as before. Text mode removes OpenAI audio output from session configuration and explicitly requests only text on every response.
- Text delta/done subtitles, completed-response assistant event persistence/dedup and server event resolution. New mode ignores audio transcript events; cancelled/failed/tool-only or interrupted old responses cannot become speech.
- Authenticated event-ID-only TTS API; server-side role/ownership/active state, latest-message, epoch, pinned version/property and R2 evidence checks. 2,000-character cap, single-session concurrency, dedup/cache, timeout, disconnect/VAD/end cancellation and usage audit. No arbitrary text, raw tool records or credentials returned.
- HTML Audio playback/Avatar, immediate barge-in abort, audio/object-URL cleanup, event-resolution timer cancellation, explicit Japanese failure/retry with retained subtitles and existing text input. No silent voice fallback.
- Escaped SSML with small pronunciation dictionary and numeric aliases that preserve values. Azure region voice/style validation precedes synthesis. Standalone audition tool requires `--execute-paid`, max three candidates × three identical phrases, no retries/substitution or normal-default change; local original WAV/SSML/results/player page prepared for eventual real run.

## Verification

| Requirement | Evidence / result |
|---|---|
| A old OpenAI audio start/regression | Existing Realtime tests and fresh R2 regression payload: `output_modalities=["audio"]`, voice `marin`; TEST HTTP/socket only |
| B new text-only output | Actual production session/request payloads captured through TEST transports: `["text"]`, no `audio.output` |
| C text events, final subtitle, one saved event | Backend tests and Chrome; audio transcript deliberately injected and ignored; no duplicate assistant message |
| D event-ID-only request | Actual Chrome fetch bodies contain only `assistant_event_id`; extra `text` rejected by real API schema |
| E speaking/idle | Actual Chrome decodes and plays Fake WAV; HTML Audio events drive Avatar speaking then idle |
| F interruption | Playback stops immediately (final run observed 9 ms in TEST), request aborted, server fake synthesis cancelled; max simultaneous playback = 1 |
| G end cleanup | Chrome verifies stopped synthetic track, closed fake peer/data channel, zero audio playback/object URLs; unfinished answer-event lookup stops after end. Final server connections/jobs/cache = 0 |
| H same business text | Real Backend computes TEST loan `87,439円` for explicit `3,000万円 / 35年 / 1.195%`; card, saved subtitle and fake TTS input agree. Property response/cards and Staff policy also pass unchanged text to fake TTS |
| I failures | Visible Japanese failure, retained subtitle, retry button/text input; no OpenAI audio fallback. Timeout and explicit retry checked; client request abort also checked independently of VAD |
| J R1/R2/business regression | Full Backend **183 passed**, Frontend build **PASS**, isolated Chrome **13 checks PASS**; no paid calls |

Tests use owned DB `ui-test.db`, ports **8018/5188**, explicit TEST Realtime HTTP/socket and fake WebRTC/VAD. Audio is a labelled **TEST ONLY electronic beep**, not Japanese speech. Chrome synthetic input is a silent MediaStream; no physical microphone is accessed. No sound sample/person recording is uploaded. Fixtures are synthetic and confirmed/published only inside this owned test DB.

Artifacts: [Backend results](backend_tests.txt), [Frontend build](frontend_build.txt), [Chrome results](chrome_result.json), [transport/usage](test_transport_evidence.json), [source manifest](verification_manifest.json), [scope preservation](protected_scope_check.json), [dry audition plan](audition_dry_plan.json), [final status](final_status.json), [speaking screenshot](test-tts-speaking.png), [ended screenshot](test-tts-ended.png).

## History and preserved scope

Initial harness attempts did not start a Session: the initial health flag/button selector prevented the start click. The selector failure/screenshot remain in `chrome_attempt_02_failure.*`; the earlier wait-response timeout is recorded here, not promoted to success. A first completed Chrome pass is preserved as `chrome_before_cleanup_hardening.json`; the final pass adds event-resolution timer cleanup and newer-text-turn protection. These are TEST harness runs, not API auditions. Cumulative TEST usage rows may include both successful runs; they are not Azure usage or bills.

Protected hashes match before/after for `.env`, dependency manifests, existing AI instructions/evidence, SDK adapter/document workflow, R2 knowledge rules, Customer serializer, Sessions, Tools, loan and Staff logic, and frozen R1/R2 evidence files. Normal DB files' size/mtime are unchanged; normal DB was not opened or copied. No SDK source, install, reset/clean, normal publication, model/service substitution or human recording operation occurred.

## Remaining acceptance

Azure Key/Region/voice are absent. Configure them privately on Backend; keep `VOICE_OUTPUT_PROVIDER=openai_realtime` for the normal Demo until explicit selection. Next step is a separately authorized regional voice-list check and **at most three-voice audition**, not Phase 2. Actual Azure synthesis, Japanese naturalness/pronunciation, real OpenAI text-only/WebRTC interoperability, real-service latency/barge-in and the user's physical mic/speaker ten-minute acceptance are unverified. This phase does not expand R1/R2 confidentiality or production readiness claims.
