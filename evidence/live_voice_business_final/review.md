# Continuous voice mortgage / Staff / end acceptance — 2026-10-07

**PASS for this isolated, synthetic-input, real-Realtime scenario.** Physical Mac microphone, speaker audibility, room echo and user acceptance remain **NOT_VERIFIED / WAITING_FOR_USER_MIC_TEST**. This does not establish normal port 5173 Demo acceptance.

Raw observations are unchanged in [result.json](result.json). The offline semantic review is [review.json](review.json). Installed Google Chrome ran the actual Customer and Staff UIs on 5174, backed by the isolated 8001 service / `evidence/http-test.db`. One Session `4d740adfb11f4408a21300808e07e76f` remained pinned to public-data test publication v3 throughout. No normal DB copy, confirmation or publication occurred. The configured Realtime model, SDK, environment and dependencies were retained.

Only microphone **input** was replaced by clearly labeled macOS Kyoko WAV speech, delivered through a test-only WebAudio MediaStream. Actual WebRTC, OpenAI audio/associated transcripts, private Backend tools, persistence and Staff workflow were used. Five speech inputs were delivered sequentially after each actual answer's final response, playback stop and idle Avatar. No Session restart, model switch, API mock or automatic connection retry occurred within the final scene. App source hashes were unchanged during the run.

| Continuous scene | Actual observation | Result |
| --- | --- | --- |
| `住宅ローンだったら月いくらですか？` | Retrieves published reference products; asks for product, head payment and years. First presentation states MUFG 1.195%, 2–40 years, ¥5m–¥300m and age / group-life / employment / account / screening requirements. Flat35 3.83% is paired with 9割以下; 3.94% with 9割超, with 21–35 years and ¥1m–¥120m boundaries. No Flat35 90% restriction transferred to MUFG. | PASS for the published conditions summarized here |
| `頭金は500万円です。` | Actual transcript and answer retain ¥5,000,000 and request remaining product / years. | PASS |
| `35年で考えています。` | Actual answer retains 35 years and explicitly says the years alone do not determine the product. Three preselection turns have zero successful calculator events and no monthly amount. | PASS |
| `フラット35でお願いします。` | Actual Backend `calculate_mortgage` event 232 uses the published Flat35 ID, ¥5m down and 35 years. Published price ¥76.9m → principal ¥71.9m, over-90% reference 3.94%, monthly ¥315,773, basis 2026-10-01 / expiry 2026-10-31 / calculation date 2026-10-07. Exactly one successful calculation. | PASS |
| Audio-associated transcript / subtitle / card | Actual Realtime answer and UI subtitle say `約31万5,773円`, Flat35 fixed, over-90% reference 3.94%. Actual card says `315,773 円`, principal `71,900,000 円`, down `5,000,000 円`, 35 years, 3.94%. Spoken mixed 万 / comma notation means exactly ¥315,773; it is not a different amount. | PASS after offline review |
| Voice result form | Actual DOM readback and screenshot show the same published Flat35 rate ID, down `5000000`, years `35`; the default MUFG product no longer remains selected above the Flat35 result. | PASS |
| `この年収なら、ローン審査に絶対通りますか？` | Real Japanese answer says AI cannot give a definite screening judgment and that Staff handles financing decisions. Backend creates a pending Staff record in the same Session and v3. | PASS |
| Staff受付 / 対応完了 | Actual authenticated Staff UI buttons transition the same record pending → accepted → completed. Customer polling visibly changes to accepted and completed. | PASS |
| Avatar / persistence | Every completed answer returns to idle; five actual voice customer messages, real assistant messages, source/tool events and calculation are stored under the same Session and pinned version. No uncaught page or Realtime protocol error. | PASS |
| 接客終了 | Actual UI end: input tracks ended, playback paused and source cleared, browser RTC closed, backend upstream hangup 200, Realtime closed, Session ended, Avatar idle and no active Customer Session caption. | PASS |

Actual received output audio is saved locally as `actual_openai_response.webm`; the browser observed 1,985,481 received RTP audio bytes / 13,573 packets. These observations establish real output transport and recording, not a human hearing the Mac's speakers. Input WAVs and audio recordings are ignored local artifacts; no credentials are included in evidence.

Screenshots were visually inspected: [loan result](loan-result.png), [Staff completed](staff-completed.png), [Customer completed](customer-staff-completed.png), [ended Customer](ended.png). No clipping or conflicting selected product was observed. The initial rate answer summarizes published applicability and product boundaries; it does not read every source note verbatim. Complete source notes and exact expiry remain present in the published UI / actual tool data.

The raw harness status retains `PENDING_MANUAL_TRANSCRIPT_REVIEW`: its money regex did not recognize `31万5,773円`. Offline review normalized that observed text to ¥315,773 and compared it to the actual subtitle and Backend card. No response, tool value or raw evidence was altered and no extra AI call was made.

## Preserved earlier attempts

| Record | Actual finding / limit |
| --- | --- |
| `../live_voice_business/result.json` | FAIL before any loan round completed. Real greeting succeeded; the finite synthetic WebAudio source produced speech_started but did not keep silence frames flowing for VAD completion. A test-only silent oscillator fixed the input clock. Cleanup was ended / closed / hangup 200. No application business defect is claimed from this attempt. |
| `../live_voice_business_clocked/result.json` | FAIL / incomplete scene after three actual collection turns. Flat35 bands, head-payment memory, years and no preselection calculation were observed. Mortgage HMR at 10:49:35 coincided with Session end at 10:49:39 and `REALTIME_SIDEBAND`; no underlying exception subtype was captured, so a transport root cause is UNCONFIRMED. This is not full business acceptance. |
| Final record here | After freezing source and narrowly improving first rate-condition wording plus form synchronization, all five sequential voice inputs / real calculation / Staff UI / end checks completed in one Session. |

The final device acceptance must be performed by the user at normal `http://localhost:5173/` after their four normal documents have been manually confirmed and published. Synthetic audio cannot substitute for that acceptance.
