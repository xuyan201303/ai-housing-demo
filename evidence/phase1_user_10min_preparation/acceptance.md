# Phase 1 user ten-minute preparation — 2026-10-08

Status: READY_FOR_USER_10MIN_TEST. User experience: WAITING_FOR_USER_10MIN_TEST.
PHASE1_CUSTOMER_EXPERIENCE_ACCEPTED: NOT_RECORDED.

## Changes
Azure adapter now reads AZURE_SPEECH_RATE and AZURE_SPEECH_STYLEDEGREE, validates them before network access, and nests prosody inside express-as. Candidate: ja-JP-NanamiNeural / chat / +15% / 1.15, pitch and volume omitted (defaults). Existing configurations without these fields preserve previous SSML. OpenAI audio backup remains supported; normal .env provider remains openai_realtime.

Shared AI instructions now request short conversational Japanese, answer before explanation, only necessary single follow-up, no repeated introduction/known conditions, latest customer corrections, less formulaic politeness. Existing source, rate, calculation and Staff restrictions remain. No canned-answer replacement, subtitle rewriting or audio manipulation. Prompt changes do not guarantee naturalness or prevent every language switch.

## Verification
Backend: 190 passed, 1 existing dependency deprecation warning; see backend_tests.txt. Provider tests use TEST transports only. No real AI/TTS calls, microphone collection or auditions initiated by agent.
Frontend build passed. Live local health and Customer/Staff HTTP checks returned 200. These are readiness checks, not real microphone/speaker acceptance.
One pre-existing expiry test depended on 2026-10-07 remaining in the future. Its scenario clock is now fixed before publication, then moved forward for the same NO_CURRENT_RATES assertion. No production expiry behavior changed.
.env, normal DB, Tools, Session and policy files have matching before/after hashes (protected_after.json). SDK, loan/Staff rules and source publications were not changed.

## Isolated real-provider environment
Customer: http://localhost:5174/
Staff: http://localhost:5174/staff
Backend: 127.0.0.1:8001
DB: evidence/phase1_user_10min_preparation/user-test.db
The DB is a one-time SQLite backup of existing isolated Phase 1 TEST publications, never normal data. Original DB and its confirmations/publications are preserved. TEST prices and documents are not customer-demo facts. New user sessions are recorded only in this acceptance copy.
Startup: backend/.venv/bin/python scripts/phase1_user_voice_server.py
Frontend: cd frontend && VITE_API_TARGET=http://127.0.0.1:8001 npm run dev -- --port 5174 --strictPort
Both services are already running; no additional restart required. The script uses existing configured credentials/models without printing them, and overrides only isolated storage/origin and selected Azure output settings. It contains no fake provider or test-control routes.

## User test
Open Customer in Chrome, start a fresh reception and allow microphone (including macOS permission if prompted). Use actual speakers and freely converse for about ten minutes. Check naturalness, length, repetition/questions, changed conditions, language, amount pronunciation, latency, interruption and echo, cards, Staff and stop-microphone. Staff uses the existing login; accept/complete the corresponding session only.
End with 接客終了. Report when/where a problem occurred and what was heard versus displayed. Existing session events preserve input transcripts, assistant text, tools, Realtime/TTS usage and errors; this is not an independent recording proving the sound heard by the user. Never mark speaker/microphone quality PASS without user feedback. Only explicit user “这个可以拿给客户看” authorizes PHASE1_CUSTOMER_EXPERIENCE_ACCEPTED.

References consulted for implementation: https://developers.openai.com/api/docs/guides/voice-prompting and https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice . No model/service migration or Phase 2 work.
