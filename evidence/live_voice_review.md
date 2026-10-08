# Live Realtime review — 2026-10-07

**PASS for the tested Chrome / synthetic-input / real-OpenAI round trip. Physical microphone and speaker acceptance remains NOT_VERIFIED.** Final record: `live_voice_final_verified/result.json`, screenshot `live-voice.png`, real received audio `actual_openai_response.webm`.

Installed Google Chrome connected the real application through WebRTC to the configured `gpt-realtime-2.1`. Input was an explicitly labeled macOS Kyoko test WAV saying `駅から何分ですか。`; it was not physical microphone capture. Output audio and transcripts came from the actual OpenAI Realtime API. No API mock, alternate voice generator or model switch was used.

The actual opening begins `こんにちは。AI住宅コンシェルジュです。`, names the published No.15 property and asks what the customer wishes to know. The station answer says maximum 12 minutes applies to four sale lots and is not a No.15-only measured value. Actual Japanese subtitles, source references, persisted voice history and the pinned publication version were checked. Browser-observed Avatar states include listening, thinking and speaking; received audio packets and playback completion were recorded. No uncaught page error or Realtime protocol error occurred.

The final answer's completed response had no remaining function call, playback stopped and Avatar returned to idle. Ending used the real UI: input tracks and playback were silenced, the authenticated Backend ended the real call, and the browser peer was closed after completion. Chrome readback observed sender tracks ended and peer closed; Backend readback was `status=ended`, `realtime.status=closed`, **`upstream_hangup_status=200`**. The earlier null hangup status is not treated as a success.

## Preserved earlier records

| Directory | Observed limit / finding |
|---|---|
| `live_voice/` | Initial harness counted split greeting output and stopped before the station response. Reclassified as transport-only after event-order inspection. |
| `live_voice_roundtrip/` | Harness stopped at a tool preamble before continuation; station answer was not awaited. |
| `live_voice_final/` | Real station answer, subtitles and playback received; listening Avatar was overwritten by interrupted-output clearing. |
| `live_voice_verified/` | Round trip and Avatar passed. Harness read before async end completion; later readback found stale Realtime metadata. |
| `live_voice_complete/` | Audio/UI round trip completed, but greeting did not meet the required opening and close metadata showed a sideband error. |
| `live_voice_greeting_verified/` | Required greeting, real answer and UI passed; upstream hangup status was null, so complete close acceptance failed. Its transport-error subtype was not recorded; no cause is invented. |
| `live_voice_accepted/` | Greeting, response, active UI states, persistence and actual hangup 200 passed. Subsequent timeline/UI review found Avatar could remain thinking after continuous tool audio. |
| `live_voice_final_verified/` | Corrected continuous audio state; required greeting, completed response, playback, final idle, source/history, ended input tracks, closed peer and hangup 200 all passed. |

The fixes revalidated here are narrow: greeting-only tool suppression after Backend property validation, event-based input/audio/generation state (including continuous tool audio), fresh Session state on end, and ordered media/Backend/peer shutdown. Each new run has separate evidence; earlier errors and test-harness shortcomings were retained. These were separate verification runs after corrections, not automatic connection retries.

The final screenshot was visually checked. This record does not establish physical Tablet behavior, customer speaker audibility, a full voice mortgage conversation, or the user's on-site acceptance. The isolated test page remains on port 5174 for the separate microphone check.
