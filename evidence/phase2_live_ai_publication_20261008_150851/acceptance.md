# HOUSING_PHASE2_LIVE_AI_PUBLICATION_CHECK

**PASS**, limited to this owned TEST FAQ update. Employee usability: **WAITING_FOR_USER_REVIEW**. Normal environment: **NOT_SWITCHED**.

| Session | Fixed publication | Immutable source | Actual real AI answer | Mixed versions |
|---|---|---|---|---|
| S_old / 14ddd0ae54d144e2a0cb2cb5420e5fbc | v4 | Confirmation #9 / 22b7dbd1113d49ef8a1b92cda1b8e5b1 / own TEST FAQ green ticket | 「TEST案内の確認方法は、SANZOが用意した動作確認用のTEST資料で、緑色の確認票を使って確認します。これは実際の会社サービスや公的制度の案内ではありません。」とあります（確認・公開済み住宅購入資料より）。 | Not observed |
| S_new / 61892e7d3dc04fdc9e94b7fcfac7da1c | v5 | Confirmation #10 / 4d295a8584f84f1fa436d567714848ad / same own TEST FAQ orange ticket | TEST案内の確認方法は、SANZOが用意した動作確認用のTEST資料を使い、橙色の確認票で確認する形です。これは実際の会社サービスや公的制度の案内ではありませんのでご注意ください。（確認・公開済み住宅購入資料より） | Not observed |

Both questions were exactly `TEST案内の確認方法は？`, with no expected-answer cue. Both actual responses preserve the limitation that the material is a SANZO TEST, not real company service or public policy.

## Four evidence layers

1. `session_version_basis_before_paid.json`: S_old was normally created before v5 publication; S_new after. Both had zero historical messages and no selected property. Immutable confirmations #9/#10 contain green/orange respectively. Versions were not edited and no ended Session was revived.
2. `tool_results.json`: the actual app invoked get_consultation_context once per question against each fixed publication. The raw permitted Tool/audit data is preserved; `request_1.json` / `request_2.json` show the controlled provider evidence contained only the corresponding exact TEST FAQ, with no opposite color or unrelated loan body. This is existing application evidence, not test-harness prompt injection.
3. `response_1.json` / `response_2.json` are unaltered actual OpenAI Responses HTTP 200 completed results; `answer_1.json` / `answer_2.json` hold the application answers and sole own TEST source identity. Configured model remained `gpt-4.1-mini`; application class `app.services.ai.AiService`. No scripted provider or paid voice service was used.
4. `06_old_v4_real_answer_and_source.png/.txt` and `07_new_v5_real_answer_and_source.png/.txt` show the actual Customer answers and safe generic source label. `customer_views_after_end.json` independently preserves the same answer strings and source fields. Both have a single generic approved-material reference and no unrelated official URL. Internal own TEST source identity remains `urn:sanzo:phase2-live-faq`; R1 deliberately does not publish this as a website link.

The model answered directly from application-supplied evidence. It did not request a search Tool or continuation; no Tool round was fabricated or forced. The broad raw Tool result is not claimed to consist solely of this FAQ: the provider projection and answer references are the narrowed boundary.

## Admin update actually performed in Chrome

The copy started at existing v4 with six published documents and the approved self-authored TEST FAQ from the earlier live-isolation environment. Source and copy identity are recorded in `isolation.json`. This was a read-only consistency copy, not another upload or SDK parse.

Chrome created S_old first, then Admin selected the existing TEST FAQ, supplied an explicit TEST reason, created a business revision, changed green to orange, saved, explicitly TEST-confirmed, previewed and published v5. Preview replaces one document's confirmation, retains five, adds/removes zero. S_new was normally created after this publication. Browser automated checks are TEST workflow operations, not the user's employee approval.

Screenshots/AX: `01_old_v4_created_no_question`, `02_faq_orange_draft_saved`, `03_v4_update_publish_preview`, `04_v5_published`, `05_new_v5_created_no_question`. No backend mutation script substituted for the Admin editing/confirmation/publication sequence.

## Request limits and actual usage

- Customer questions: 2/2.
- Actual upstream Responses generation POSTs: 2/4, one per customer turn (maximum two allowed per turn).
- Failed requests: 0; retries: 0; configured output cap preserved at 1500 tokens.
- Usage: input 3874, output 136, total 4010 tokens; cached 0, reasoning 0 (actual provider records).
- Exact billing amount is not available; no price invented.
- A fixed task-wide ledger `../phase2_live_ai_publication_check_budget.json` is persisted before each outbound request and bound to this output directory. Process lifetime flock prevents parallel budget owners; restart after any created Session/question/request is refused. Session/question/total4/per-turn2 limits cannot be reset by output-directory or Session changes. Failure requests count before send; no redirects or HTTP retries. Static peer review found no remaining blocker. No remaining allowance was spent after success.

## Minimal fix and offline validation

The preceding run's actual source-association failure remains intact in its original directory. This round made only the necessary generic correction in `backend/app/services/ai.py` and `ai_evidence.py`: complete approved FAQ-question matches take priority, and answer references follow actual admitted evidence rather than all context references. No FAQ-specific system prompt or expected answer was added. Original system-instruction hash `41f8b838b3a696ee4c4a31b55bbb8a7e31036cc146412deb5a33f04a2f1d5f67` equals the preceding live record.

`offline_source_fix.md` records the targeted offline tests: test_ai.py 13 passed and three relevant existing R2 tests passed. Initial fixture-metadata failure was retained; final fix supplies ordinary test Session fields without weakening assertions. These intercepted TEST tests are separate from the real calls above. No full backend/UI acceptance repetition was performed; frontend files/build artifacts were not changed. `git diff --check` passed.

## Preservation and cleanup

`preservation.json` and protected before/after hashes show .env, all frontend source and every original `evidence/phase2_admin_e2e/` record/screenshot/database unchanged. Source live TEST DB unchanged; document raw/normalized/file hashes, all prior confirmations and v1-v4 unchanged. Only the temporary copy receives v5 and the two new Sessions. Normal housing.db was never connected, queried, copied, migrated or published by this task. SDK1.8.0, dependencies, configured model/voice, mortgage and Staff rules were not changed. No SDK source access.

Both Sessions were ended through Customer buttons, recorded in `08_new_v5_session_ended`, `09_old_v4_session_ended` and `sessions_after_end.json`. Only this task's temporary 8005 process was stopped. `environment_after_stop.json` confirms 8005 stopped, while 5177 and 8004 remain status ok / mode test / ai_configured false / SDK1.8.0.

User Admin remains http://localhost:5177/admin, with the existing one-page `docs/ADMIN_END_TO_END_GUIDE.md` unchanged. Employee subjective acceptance is still pending. This result proves neither arbitrary FAQ paraphrases, all AI capabilities, real Japanese speech, microphone/speaker behavior nor production delivery. Work stops here; Phase 3 is not started.
