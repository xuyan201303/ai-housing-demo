# HOUSING_PHASE2_LIVE_FAQ_CHECK

Current real text integration: **NEEDS_FIX**. Old/new live comparison: **INCOMPLETE**, stopped after the first result's source-display anomaly. Employee review: **WAITING_FOR_USER_REVIEW**.

## Actual comparison

| | S_old | S_new |
|---|---|---|
| Session | 55d0892a48e24016a08b60d89d3b973f | 5e0da4a790534115accceaf131d093fd |
| Pinned publication | v3 | v4 |
| FAQ confirmation | #8 | #9 |
| Immutable revision | 2c33dd6e64ab4bd8a9a1452ef2441c22 | 22b7dbd1113d49ef8a1b92cda1b8e5b1 |
| Approved TEST change | 青色の確認票 | 緑色の確認票 |
| Real AI answer | Received | Not asked after anomaly |
| Final Session status | ended | ended |

Actual old-session answer (unaltered):

> TEST案内の確認方法についてですが、SANZOが用意した動作確認用のTEST資料で、実際の会社サービスや公的制度の案内ではありません。確認は青色の確認票を使って行います。詳細は確認・公開済み住宅購入資料を参照ください。

There is no actual new-session answer. Its approved v4 evidence contains green, but this is **not** a real AI verification result.

## Observed defect and stop

The old model input and answer use v3 / confirmation #8 / blue. No green value appears in the actual old request or answer. The key answer is supported and clearly marked TEST rather than actual company service or public policy.

However, `request_1.json` also includes irrelevant loan FAQ body; `answer_1.json` and the actual Customer screen show https://www.flat35.com/loan/lineup/flat35/flow_shinchiku.html as this answer's original-source link. This official page does not support the artificial TEST checking-ticket fact. See `07_old_real_answer_v3.png` and `.txt`.

Static cause: `backend/app/services/ai_evidence.py:45` matches common adjacent characters, retaining unrelated loan content; `backend/app/services/ai.py:99` initializes answer sources from all consultation references; Customer projection validates allowed source identities/URLs, but does not tie every returned reference to the selected answer evidence. This is a source-association defect, not observed version leakage or invented bank facts.

The provider response succeeded. Manual inspection then stopped the check, so the original provider ledger's `halted: false` is retained without rewriting it. No second question, retry, prompt patch or paid regeneration was performed. Temporary service is now stopped.

## Actual paid use

- Current configured model: gpt-4.1-mini; unchanged.
- Customer questions: 1/2.
- Actual outbound Responses POSTs: 1/4, durably counted before send.
- Provider HTTP: 200; response status: completed.
- input_tokens: 2585; output_tokens: 69; total_tokens: 2654.
- cached_tokens: 0; reasoning_tokens: 0 (actual provider records).
- No precise billing amount available; no cost estimate invented.
- Existing context already supplied FAQ via actual get_consultation_context → controlled tool_evidence → real AiService. Model made no additional Tool continuation request; no artificial Tool round was added.

## Isolation and preparation

5177 remains the original TEST environment. Only `evidence/phase2_admin_e2e/ui-test.db` was copied read-only to this separate `live-test.db`; normal housing.db was never connected or copied. Six existing documents were reused without upload or SDK reparse.

The earlier artificial FAQ had inherited an official source. Before either new Session, the temporary Admin page created, saved, explicitly TEST-confirmed and preview-published a self-authored TEST baseline v3: source `SANZO自有TEST FAQ（人工入力）`, local identifier `urn:sanzo:phase2-live-faq`, no official-source attribution. Its business knowledge candidate was cleared rather than relabeling official SDK prose. Raw / normalized originals remain intact. This is a TEST browser operation, not the user's employee acceptance.

Then Customer created S_old with no question; Admin edited that same FAQ to green, saved, confirmed #9, previewed and published v4 retaining the other five approved revisions; Customer created S_new with no question. `session_version_basis_before_paid.json` proves both new Sessions had zero historical messages. No TEST-provider answer was injected, no historical Session revived, no Session version edited.

Three evidence layers: pinned identities in `session_version_basis_before_paid.json`; actual application Tool data in `tool_results.json` and submitted provider evidence in `request_1.json`; actual output in `response_1.json`, `answer_1.json`, Customer screenshot/text and `customer_session_views_after_end.json`.

All pre-existing application Python/frontend source hashes, .env hash and the preserved 5177 TEST DB hash match the preflight record. Every document raw/normalized/file hash, prior confirmations and v1/v2 remain unchanged. `preservation_and_cleanup.json` records the checks. The new one-shot `scripts/phase2_live_faq_check_server.py` adds instrumentation and hard paid-call caps only; it does not change business prompts, model, SDK or normal configuration.

Both Sessions were ended through Customer buttons. `environment_after_stop.json` proves own 8005 process stopped, 5177 status ok / demo_mode test / ai_configured false / SDK 1.8.0.

## Deferred minimal scope

If separately authorized, repair general FAQ evidence-to-source association, preserving fixed publication and R1/R2 URL restrictions; first verify offline, then seek authorization for at most two questions/four real generations. No fix or additional paid verification was started in this task. No Phase 3. No voice, microphone, arbitrary-document, employee or production acceptance is claimed.
