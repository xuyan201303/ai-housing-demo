// Actual Google Chrome, real installed SDK through actual Admin endpoints.
// Customer replies alone use the explicitly labelled TEST provider. No paid API/mic.
import { chromium, expect } from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
import crypto from 'node:crypto'

const root = path.resolve(import.meta.dirname, '..')
const evidence = path.join(root, 'evidence/phase2_admin_forms')
const run = process.env.PHASE2_RUN || 'initial'
if (!/^[a-zA-Z0-9_-]+$/.test(run)) throw new Error('Use a simple TEST run name')
const out = path.join(evidence, run)
await fs.mkdir(out, { recursive: true })
const origin = 'http://localhost:5175'
const headers = { Authorization: `Basic ${Buffer.from('admin:TEST-phase2-admin').toString('base64')}` }
const stable = value => value && typeof value === 'object' ? Array.isArray(value) ? value.map(stable) : Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, stable(v)])) : value
const hash = value => crypto.createHash('sha256').update(JSON.stringify(stable(value))).digest('hex')
const context = await chromium.launchPersistentContext(path.join(evidence, `chrome-${run}-profile`), {
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: !process.argv.includes('--keep-open'), viewport: { width: 1440, height: 1100 },
})
await context.route('**/*', route => {
  const url = new URL(route.request().url())
  return ['localhost', '127.0.0.1', '::1'].includes(url.hostname) || ['data:', 'blob:'].includes(url.protocol) ? route.continue() : route.abort()
})
const admin = context.pages()[0] || await context.newPage()
const result = { status: 'RUNNING', run, browser: 'Google Chrome', provider: 'TEST_DETERMINISTIC_NOT_REAL_AI',
  sdk: 'REAL_INSTALLED_DISTRIBUTION', database: 'evidence/phase2_admin_forms/ui-test.db', ports: [5175, 8002],
  paid_ai_tts_calls: 0, microphone: 'NOT_USED', checks: {}, documents: {}, screenshots: [], customer_responses: [], page_errors: [] }
const resumeCore = process.env.PHASE2_RESUME_CORE === '1'
const resumePublished = process.env.PHASE2_RESUME_PUBLISHED === '1'
if (resumeCore || resumePublished) {
  const prior = resumePublished ? 'verified' : 'initial'
  const initial = JSON.parse(await fs.readFile(path.join(evidence, `${prior}/chrome_result.json`), 'utf8'))
  result.previous_run = { path: `${prior}/chrome_result.json`, status: initial.status, error: initial.error }
  result.checks = { ...initial.checks }
}
let customer, customerSession
context.on('page', page => page.on('pageerror', error => result.page_errors.push(error.message)))
admin.on('pageerror', error => result.page_errors.push(error.message))
context.on('response', async response => {
  const url = new URL(response.url())
  if (!url.pathname.startsWith('/api/') || url.pathname.includes('/admin/') || url.pathname.includes('/staff/') || !response.headers()['content-type']?.includes('json')) return
  const body = await response.json().catch(() => null)
  if (!body) return
  const safe = structuredClone(body); delete safe.token
  result.customer_responses.push({ path: url.pathname, status: response.status(), body: safe })
})
async function api(endpoint, options = {}, employee = true) {
  const response = await context.request.fetch(`${origin}/api${endpoint}`, { ...options, headers: { ...(employee ? headers : {}), ...options.headers } })
  return { response, body: await response.json().catch(() => null) }
}
async function checkpoint() { await fs.writeFile(path.join(out, 'chrome_result.json'), JSON.stringify(result, null, 2)) }
async function screenshot(name, locator = admin) {
  const target = `${name}.png`; await locator.screenshot({ path: path.join(out, target), fullPage: locator === admin })
  result.screenshots.push(target); await checkpoint()
}
async function login(page, role = 'admin') {
  if (await page.getByLabel('パスワード', { exact: true }).count()) {
    await page.getByLabel('パスワード', { exact: true }).fill(`TEST-phase2-${role}`)
    await page.getByRole('button', { name: 'ログイン', exact: true }).click()
  }
}
async function section(name) { await admin.getByRole('navigation', { name: '業務管理メニュー' }).getByRole('button', { name, exact: true }).click() }
async function choose(filename, pane) {
  await section('資料管理')
  await admin.locator('.document-row button').filter({ hasText: filename }).click()
  await expect(admin.locator('.document-detail h2')).toHaveText(filename)
  await expect(admin.getByRole('button', { name: '下書きを保存', exact: true })).toBeVisible()
  if (pane) await section(pane)
}
async function uploadParse(filename) {
  await section('資料管理')
  const existing = (await api('/admin/documents')).body
  const bytes = await fs.readFile(path.join(root, 'demo_documents', filename))
  const digest = crypto.createHash('sha256').update(bytes).digest('hex')
  let document = existing.find(row => row.filename === filename && row.sha256 === digest)
  if (document?.status === 'error') throw new Error(`STOP: previous SDK parse failed for ${filename}; no retry`)
  if (!document) {
    const uploaded = admin.waitForResponse(response => response.url().endsWith('/api/admin/documents') && response.request().method() === 'POST')
    await admin.locator('input[type=file]').setInputFiles(path.join(root, 'demo_documents', filename))
    const response = await uploaded; expect(response.ok()).toBe(true); document = await response.json()
  } else {
    await admin.locator('.document-row button').filter({ hasText: filename }).click()
  }
  if (document.status === 'uploaded') {
    const parsed = admin.waitForResponse(response => response.url().endsWith(`/documents/${document.id}/parse`) && response.request().method() === 'POST')
    await admin.getByRole('button', { name: 'SDK解析を実行', exact: true }).click()
    const response = await parsed
    if (!response.ok()) throw new Error(`STOP: actual SDK parse failed for ${filename}; no retry`)
    document = await response.json()
  } else document = (await api(`/admin/documents/${document.id}`)).body
  expect(document.sdk_version).toBe('1.8.0'); expect(document.raw).toBeTruthy(); expect(document.normalized).toBeTruthy()
  const priorPath = path.join(evidence, 'sdk_parse_records.json')
  const prior = JSON.parse(await fs.readFile(priorPath, 'utf8').catch(() => '{}'))
  const proof = { id: document.id, filename, sha256: document.sha256, sdk_version: document.sdk_version,
    sdk_api: document.sdk_api, raw_sha256: hash(document.raw), normalized_sha256: hash(document.normalized), parsed_at: document.parsed_at }
  if (prior[filename]) {
    expect(proof.raw_sha256).toBe(prior[filename].raw_sha256); expect(proof.normalized_sha256).toBe(prior[filename].normalized_sha256)
  } else { prior[filename] = proof; await fs.writeFile(priorPath, JSON.stringify(prior, null, 2)) }
  result.documents[filename] = proof; await checkpoint()
  await expect(admin.getByRole('button', { name: '下書きを保存', exact: true })).toBeVisible()
  return document
}
async function save() {
  const saved = admin.waitForResponse(response => /\/documents\/[^/]+\/draft$/.test(response.url()) && response.request().method() === 'POST')
  await admin.getByRole('button', { name: '下書きを保存', exact: true }).click()
  const response = await saved; expect(response.ok()).toBe(true)
  await expect(admin.locator('.admin-draft-status')).toContainText('下書き保存済み')
  await expect(admin.getByRole('checkbox', { name: '資料と下書きの内容・用途を確認しました', exact: true })).not.toBeChecked()
  return response.json()
}
async function prepare(usage = 'customer') {
  await admin.getByLabel('資料用途', { exact: true }).selectOption(usage)
  await admin.getByLabel('確認メモ', { exact: true }).fill('TEST隔離Chrome：SDK原文とフォームを照合。手入力のTEST項目を区別。通常DB・公開資料とは無関係。')
  return save()
}
async function confirm() {
  const checkbox = admin.getByRole('checkbox', { name: '資料と下書きの内容・用途を確認しました', exact: true })
  await expect(checkbox).not.toBeChecked(); await checkbox.check()
  const confirmed = admin.waitForResponse(response => response.url().endsWith('/draft/confirm') && response.request().method() === 'POST')
  await admin.getByRole('button', { name: '管理者確認を保存', exact: true }).click()
  const response = await confirmed; expect(response.ok()).toBe(true)
  await expect(admin.locator('.document-detail .badge').first()).toHaveText('確認済み')
  return response.json()
}
async function ask(text) {
  await customer.getByLabel('ご相談内容', { exact: true }).fill(text)
  const response = customer.waitForResponse(item => item.url().endsWith('/messages') && item.request().method() === 'POST')
  await customer.getByRole('button', { name: '送信', exact: true }).click(); expect((await response).ok()).toBe(true)
}
try {
  await admin.goto(`${origin}/admin`); await login(admin)
  const property = await uploadParse('物件概要_demo.pdf')
  const equipment = await uploadParse('設備仕様_demo.pdf')
  const faq = await uploadParse('住宅購入基礎FAQ_demo.pdf')
  const rates = await uploadParse('住宅ローン_demo.xlsx')
  const internal = await uploadParse('住宅ローン基礎FAQ_demo.pdf')
  const unclassified = await uploadParse('周辺環境_demo.pdf')
  result.checks.real_sdk_pdf_excel_upload_parse = 'PASS'
  await screenshot('01-document-list')
  let confirmedRates, version
  if (!resumePublished) {
  if (!resumeCore) {
  await choose(property.filename, '物件情報')
  await expect(admin.getByLabel('価格（円）', { exact: true })).toHaveValue(String(property.normalized.property.price))
  await admin.getByLabel('物件名', { exact: true }).fill('TEST Phase2 No.15')
  await admin.getByLabel('価格（円）', { exact: true }).fill(String(property.normalized.property.price))
  await prepare(); await screenshot('02-property-edit')
  await admin.reload(); await login(admin); await choose(property.filename, '物件情報')
  await expect(admin.getByLabel('物件名', { exact: true })).toHaveValue('TEST Phase2 No.15')
  await expect(admin.getByRole('checkbox', { name: '資料と下書きの内容・用途を確認しました', exact: true })).not.toBeChecked()
  await screenshot('03-draft-restored')
  const propertyDraft = (await api(`/admin/documents/${property.id}`)).body
  expect(propertyDraft.status).toBe('parsed'); expect(propertyDraft.reviewed).toBeUndefined(); expect(propertyDraft.confirmation_id).toBeFalsy()
  expect(hash(propertyDraft.raw)).toBe(result.documents[property.filename].raw_sha256)
  const beforePublish = await api('/sessions', { method: 'POST', data: { mode: 'text' } }, false)
  expect(beforePublish.body.version).toBeNull(); expect(beforePublish.body.property).toBeNull()
  expect(JSON.stringify(beforePublish.body)).not.toContain('TEST Phase2 No.15')
  const unpublished = await api('/admin/publish', { method: 'POST', data: { document_ids: [property.id] } })
  expect(unpublished.response.status()).toBe(409); expect(unpublished.body.error.code).toBe('UNCONFIRMED_DOCUMENT')
  await api(`/sessions/${beforePublish.body.id}/end`, { method: 'POST', headers: { 'X-Session-Token': beforePublish.body.token } }, false)
  result.checks.backend_draft_refresh_raw_immutable_unconfirmed_not_public = 'PASS'
  await confirm(); await screenshot('04-explicit-confirmation')

  await choose(equipment.filename, '設備情報')
  const count = equipment.normalized.property.equipment.length
  const originalEquipment = equipment.normalized.property.equipment[0]
  await admin.getByLabel('設備名称・説明 1', { exact: true }).fill(`${originalEquipment}（TEST画面入力）`)
  await admin.getByRole('button', { name: '設備を追加', exact: true }).click()
  await admin.getByLabel(`設備名称・説明 ${count + 1}`, { exact: true }).fill('TEST一時行：削除の検証')
  await admin.getByRole('button', { name: `設備 ${count + 1} を削除`, exact: true }).click()
  await expect(admin.getByLabel(`設備名称・説明 ${count + 1}`, { exact: true })).toHaveCount(0)
  await admin.getByRole('button', { name: '設備を追加', exact: true }).click()
  await admin.getByLabel(`設備名称・説明 ${count + 1}`, { exact: true }).fill('TEST追加：設備フォーム検証用。実物の設備ではありません。')
  await prepare(); await screenshot('05-equipment-edit'); await confirm()
  result.checks.equipment_add_edit_delete = 'PASS'

  await choose(faq.filename, 'FAQ')
  await admin.getByRole('button', { name: 'FAQを追加', exact: true }).click()
  const faqRow = admin.getByRole('article', { name: 'FAQ 1', exact: true })
  const sourceText = faq.normalized.knowledge.map(row => row.text).join('\n')
  const excerpt = sourceText.split('\n').find(text => text.length > 18 && !/^[a-z_]+[:：]/.test(text)) || sourceText.slice(0, 150)
  await faqRow.getByLabel('質問', { exact: true }).fill('TEST：住宅購入の進め方を確認できますか？')
  await faqRow.getByLabel('回答', { exact: true }).fill(`TEST手動補録：${excerpt}`)
  await faqRow.getByLabel('出典の位置（ページ・章）', { exact: true }).fill(faq.normalized.knowledge[0].reference.location)
  await faqRow.getByLabel('出典URL（任意）', { exact: true }).fill(faq.normalized.document.source_url)
  await faqRow.getByLabel('質問', { exact: true }).fill('TEST：住宅購入の進め方を資料で確認できますか？')
  await admin.getByRole('button', { name: 'FAQを追加', exact: true }).click()
  await admin.getByRole('button', { name: 'FAQ 2 を削除', exact: true }).click()
  await expect(admin.getByRole('article', { name: 'FAQ 2', exact: true })).toHaveCount(0)
  await prepare(); await screenshot('06-faq-edit'); await confirm()
  result.checks.faq_add_edit_delete_sources_manual_not_sdk = 'PASS'

  await choose(rates.filename, '住宅ローン')
  const firstRate = admin.getByRole('article', { name: '金利商品 1', exact: true })
  await firstRate.getByLabel('商品名', { exact: true }).fill(`${rates.normalized.rates[0].product}（TESTフォーム）`)
  await firstRate.getByLabel('参考金利（年率％）', { exact: true }).fill(String(rates.normalized.rates[0].rate))
  await firstRate.getByLabel('適用条件', { exact: true }).fill(rates.normalized.rates[0].notes)
  await firstRate.getByLabel('出典の位置（シート・行など）', { exact: true }).fill(`${rates.normalized.rates[0].reference.location}（TESTフォーム検証）`)
  await prepare()
  // Unknown existing nested fields are injected only into this owned TEST draft.
  // Subsequent ordinary form saves must preserve them without JSON editing.
  const hidden = (await api(`/admin/documents/${rates.id}/draft`)).body
  hidden.reviewed.rates[0].future_condition_note = 'TEST_PHASE2_PRESERVED_UNSUPPORTED_FIELD'
  const patched = await api(`/admin/documents/${rates.id}/draft`, { method: 'POST', data: {
    document_sha256: hidden.document_sha256, source_revision: hidden.source_revision, revision: hidden.revision,
    reviewed: hidden.reviewed, usage: hidden.usage, note: hidden.note,
  } }); expect(patched.response.ok()).toBe(true)
  await choose(rates.filename, '住宅ローン')
  const expiry = firstRate.getByLabel('金利の有効期限', { exact: true })
  const originalExpiry = await expiry.inputValue(); await expiry.fill(''); await save()
  await admin.getByRole('checkbox', { name: '資料と下書きの内容・用途を確認しました', exact: true }).check()
  const failed = admin.waitForResponse(response => response.url().endsWith('/draft/confirm') && response.request().method() === 'POST')
  await admin.getByRole('button', { name: '管理者確認を保存', exact: true }).click()
  expect((await failed).status()).toBe(400)
  await expect(firstRate.locator('#admin-field-rates-0-valid_until-error')).toHaveText('金利の有効期限を入力してください。')
  await expect(expiry).toHaveAttribute('aria-invalid', 'true'); await screenshot('07-rate-inline-error', firstRate)
  await expiry.fill(originalExpiry); await save()
  await screenshot('08-rate-edit', firstRate); confirmedRates = await confirm()
  expect(confirmedRates.reviewed.rates[0].future_condition_note).toBe('TEST_PHASE2_PRESERVED_UNSUPPORTED_FIELD')
  for (const key of ['notes', 'conditions', 'years_min', 'years_max', 'loan_amount_min', 'loan_amount_max', 'max_loan_to_value', 'rate_over_90_percent'])
    expect(confirmedRates.reviewed.rates[0][key]).toEqual(rates.normalized.rates[0][key])
  result.checks.rate_edit_existing_conditions_unknown_preserved_inline_error = 'PASS'
  } else {
    confirmedRates = (await api(`/admin/documents/${rates.id}`)).body
    // Clearing an optional numeric field must remove it, then restore the
    // actual source value so no financing condition is invented by this test.
    await choose(rates.filename, '住宅ローン')
    const optionalIndex = rates.normalized.rates.findIndex(item => item.rate_over_90_percent != null)
    if (optionalIndex < 0) throw new Error('TEST requires an existing source rate_over_90_percent value')
    const optional = admin.getByRole('article', { name: `金利商品 ${optionalIndex + 1}`, exact: true }).getByLabel('融資率9割超の参考金利（年率％）', { exact: true })
    const value = await optional.inputValue(); await optional.fill(''); const empty = await save()
    expect(Object.hasOwn(empty.reviewed.rates[optionalIndex], 'rate_over_90_percent')).toBe(false)
    await optional.fill(value); await save(); confirmedRates = await confirm()
    result.checks.optional_numeric_clear_deletes_key_and_original_restored = 'PASS'
  }
  // Restore the identity from the actual PDF after exercising draft edits.
  // All property documents must agree; the existing conflict rule is retained.
  await choose(property.filename, '物件情報')
  await admin.getByLabel('物件名', { exact: true }).fill(property.normalized.property.property_name)
  await save(); await confirm()
  result.checks.property_identity_matches_other_real_sdk_documents = 'PASS'

  await choose(internal.filename); await prepare('internal'); await confirm()
  const internalDenied = await api('/admin/publish', { method: 'POST', data: { document_ids: [internal.id] } })
  expect(internalDenied.response.status()).toBe(409); expect(internalDenied.body.error.code).toBe('CUSTOMER_USAGE_REQUIRED')
  await choose(unclassified.filename); await prepare('unclassified')
  await section('公開管理')
  await expect(admin.getByRole('checkbox', { name: `${internal.filename} を公開対象に選択`, exact: true })).toBeDisabled()
  await expect(admin.getByRole('checkbox', { name: `${unclassified.filename} を公開対象に選択`, exact: true })).toBeDisabled()
  for (const document of [property, equipment, faq, rates]) await admin.getByRole('checkbox', { name: `${document.filename} を公開対象に選択`, exact: true }).check()
  const published = admin.waitForResponse(response => response.url().endsWith('/admin/publish') && response.request().method() === 'POST')
  await admin.getByRole('button', { name: '選択資料を公開', exact: true }).click()
  const publishedResponse = await published; expect(publishedResponse.ok()).toBe(true)
  version = await publishedResponse.json(); result.published_version = version.version
  expect(version.document_ids).toEqual([property.id, equipment.id, faq.id, rates.id])
  await screenshot('09-confirmed-test-publication'); result.checks.r2_usage_independent_confirmation_publication = 'PASS'
  } else {
    confirmedRates = (await api(`/admin/documents/${rates.id}`)).body
    version = (await api('/admin/versions')).body[0]
    expect(version.document_ids).toEqual([property.id, equipment.id, faq.id, rates.id])
    result.published_version = version.version
  }

  customer = await context.newPage(); await customer.goto(origin)
  const started = customer.waitForResponse(response => response.url().endsWith('/api/sessions') && response.request().method() === 'POST')
  await customer.getByRole('button', { name: '文字で開始', exact: true }).click(); customerSession = await (await started).json()
  expect(customerSession.property).toBeNull(); expect(customerSession.version).toBe(version.version)
  await ask('紹介できる物件はありますか？')
  await customer.getByRole('button', { name: 'この物件について相談', exact: true }).click()
  await expect(customer.locator('.property-panel')).toContainText(property.normalized.property.property_name)
  await customer.getByRole('tab', { name: '設備・周辺', exact: true }).click(); await expect(customer.locator('.property-panel')).toContainText('TEST追加')
  const selected = (await api(`/sessions/${customerSession.id}`, { headers: { 'X-Session-Token': customerSession.token } }, false)).body
  await ask('住宅ローンについて相談したい')
  await customer.getByLabel('頭金（円）', { exact: true }).fill('5000000')
  await customer.getByLabel('返済期間（年）', { exact: true }).fill('35')
  await customer.locator('.mortgage-form select').selectOption(confirmedRates.reviewed.rates[0].id)
  const calculated = customer.waitForResponse(response => response.url().endsWith('/mortgage') && response.request().method() === 'POST')
  await customer.getByRole('button', { name: '月額概算を計算', exact: true }).click()
  const calculationResponse = await calculated; expect(calculationResponse.ok()).toBe(true)
  const calculation = await calculationResponse.json(); result.mortgage = calculation
  await expect(customer.locator('.mortgage-result')).toContainText(`${calculation.monthly_payment.toLocaleString('ja-JP')} 円`)
  await customer.getByRole('button', { name: 'スタッフを呼ぶ', exact: true }).click()
  await customer.getByRole('button', { name: 'スタッフへの呼出を送信', exact: true }).click()
  await expect(customer.locator('.staff-status')).toContainText('確認をお待ちください')
  const staff = await context.newPage(); await staff.goto(`${origin}/staff`); await login(staff, 'staff')
  const card = staff.locator('article.staff-call').filter({ hasText: customerSession.id })
  await card.getByRole('button', { name: '受付', exact: true }).click(); await expect(customer.locator('.staff-status')).toContainText('スタッフが確認しました')
  await card.getByRole('button', { name: '対応完了', exact: true }).click(); await expect(customer.locator('.staff-status')).toContainText('対応が完了しました')
  await customer.getByRole('button', { name: '接客終了', exact: true }).click(); await expect(customer.getByRole('button', { name: '文字で開始', exact: true })).toBeVisible()
  result.checks.customer_property_backend_loan_staff_end_regression = 'PASS'

  const versionsBeforeDraft = (await api('/admin/versions')).body
  const approvedBeforeDraft = (await api(`/admin/documents/${property.id}`)).body
  await choose(property.filename, '物件情報')
  await admin.getByLabel('物件名', { exact: true }).fill('TEST_PHASE2_UNPUBLISHED_UPDATE')
  await save()
  const approvedAfterDraft = (await api(`/admin/documents/${property.id}`)).body
  expect(approvedAfterDraft.status).toBe('published'); expect(approvedAfterDraft.confirmation_id).toBe(approvedBeforeDraft.confirmation_id)
  expect(approvedAfterDraft.reviewed).toEqual(approvedBeforeDraft.reviewed)
  expect((await api('/admin/versions')).body).toEqual(versionsBeforeDraft)
  const next = await api('/sessions', { method: 'POST', data: { mode: 'text' } }, false)
  const nextSelected = await api(`/sessions/${next.body.id}/property`, { method: 'POST', data: { property_id: selected.property_id }, headers: { 'X-Session-Token': next.body.token } }, false)
  expect(nextSelected.response.ok()).toBe(true); expect(nextSelected.body.property.property_name).toBe(property.normalized.property.property_name)
  const wrong = await api(`/sessions/${next.body.id}`, { headers: { 'X-Session-Token': customerSession.token } }, false)
  expect(wrong.response.status()).toBe(403)
  const unauthorized = await api(`/admin/documents/${property.id}/draft`, {}, false); expect(unauthorized.response.status()).toBe(401)
  await api(`/sessions/${next.body.id}/end`, { method: 'POST', headers: { 'X-Session-Token': next.body.token } }, false)
  result.checks.published_draft_preserves_current_approval_snapshot_customer_permissions = 'PASS'
  for (const proof of Object.values(result.documents)) {
    const record = (await api(`/admin/documents/${proof.id}`)).body
    expect(hash(record.raw)).toBe(proof.raw_sha256); expect(hash(record.normalized)).toBe(proof.normalized_sha256)
  }
  const serialized = JSON.stringify(result.customer_responses)
  for (const marker of ['TEST_PHASE2_UNPUBLISHED_UPDATE', 'TEST_PHASE2_PRESERVED_UNSUPPORTED_FIELD', '"snapshot"', '"normalized"', '"reviewed"', '"tool_events"', '"confirmation_note"']) expect(serialized).not.toContain(marker)
  result.checks.all_sdk_raw_normalized_preserved_customer_boundary = 'PASS'
  await choose(equipment.filename, '設備情報'); await screenshot('05-equipment-edit')
  await choose(faq.filename, 'FAQ'); await screenshot('06-faq-edit')
  await choose(rates.filename, '住宅ローン'); await screenshot('08-rate-edit', admin.getByRole('article', { name: '金利商品 1', exact: true }))
  await choose(property.filename, '物件情報'); await screenshot('02-property-edit')
  await admin.reload(); await login(admin); await choose(property.filename, '物件情報')
  await expect(admin.getByLabel('物件名', { exact: true })).toHaveValue('TEST_PHASE2_UNPUBLISHED_UPDATE')
  await expect(admin.getByRole('checkbox', { name: '資料と下書きの内容・用途を確認しました', exact: true })).not.toBeChecked()
  await screenshot('03-draft-restored')
  await section('資料管理'); await screenshot('10-final-document-list')
  await admin.setViewportSize({ width: 1024, height: 900 }); expect(await admin.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await admin.setViewportSize({ width: 1440, height: 1100 })
  expect(result.page_errors).toEqual([]); result.checks.pc_responsive_no_page_errors = 'PASS'; result.status = 'PASS'
} catch (error) {
  result.status = 'FAIL'; result.error = error.message; result.error_stack = error.stack
  await screenshot('failure').catch(() => {})
  if (customer) { await customer.screenshot({ path: path.join(out, 'customer-failure.png'), fullPage: true }).catch(() => {}); result.screenshots.push('customer-failure.png') }
} finally {
  if (customerSession) await api(`/sessions/${customerSession.id}/end`, { method: 'POST', headers: { 'X-Session-Token': customerSession.token } }, false).catch(() => {})
  await checkpoint()
  console.log(JSON.stringify({ status: result.status, run, checks: result.checks, documents: Object.keys(result.documents).length, error: result.error }))
}
if (result.status === 'PASS' && process.argv.includes('--keep-open')) {
  await admin.bringToFront()
  console.log('TEST Admin Chrome remains open for user review. Ctrl+C closes this dedicated TEST browser.')
  await new Promise(resolve => process.once('SIGINT', resolve))
}
await context.close()
if (result.status !== 'PASS') process.exitCode = 1
