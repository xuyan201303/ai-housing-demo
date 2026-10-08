import { useEffect, useRef, useState } from 'react'
import { Alert, Icon } from './App'
import { ApiError, api, errorText, fmtDate, post } from './api'
import type { Json } from './api'

export type ReviewSection = 'documents' | 'property' | 'equipment' | 'faq' | 'rates'
export const usageNames: Record<string, string> = { customer: '顧客への案内に使用可', internal: '社内専用', unclassified: '未確認' }
export const stateNames: Record<string, string> = { uploaded: 'アップロード済み', parsed: '解析済み', confirmed: '確認済み', published: '公開済み', error: 'エラー' }
const sectionNames: Record<ReviewSection, string> = { documents: '資料管理', property: '物件情報', equipment: '設備情報', faq: 'FAQ', rates: '住宅ローン' }
const copy = <T,>(value: T): T => JSON.parse(JSON.stringify(value))
const pretty = (value: unknown) => JSON.stringify(value, null, 2)
type FieldErrors = Record<string, string>
type FieldSpec = { name: string, label: string, numeric?: boolean, type?: string, required?: boolean, area?: boolean, hint?: string }

const propertyFields: FieldSpec[] = [
  { name: 'property_name', label: '物件名' }, { name: 'lot', label: '号地' },
  { name: 'price', label: '価格（円）', numeric: true }, { name: 'address', label: '住所' },
  { name: 'layout', label: '間取り' }, { name: 'land_area', label: '土地面積（㎡）', numeric: true },
  { name: 'building_area', label: '建物面積（㎡）', numeric: true }, { name: 'station', label: '最寄駅' },
  { name: 'walking_minutes', label: '徒歩分数（分）', numeric: true },
  { name: 'completion_date', label: '完成年月', hint: '資料に記載された表記を入力してください。' }, { name: 'parking', label: '駐車場' },
]
const sourceFields: FieldSpec[] = [
  { name: 'source_name', label: '出典名' }, { name: 'source_url', label: '出典URL', type: 'url' },
  { name: 'checked_at', label: '出典の確認日', type: 'date' }, { name: 'effective_date', label: '基準日', type: 'date' },
  { name: 'valid_until', label: '有効期限', type: 'date' }, { name: 'scope_notes', label: '適用範囲・注意事項', area: true },
]
const rateFields: FieldSpec[] = [
  { name: 'bank', label: '金融機関', required: true }, { name: 'product', label: '商品名', required: true },
  { name: 'rate_type', label: '金利タイプ', required: true }, { name: 'rate', label: '参考金利（年率％）', numeric: true, required: true },
  { name: 'notes', label: '適用条件の補足', area: true, required: true },
  { name: 'effective_date', label: '基準日', type: 'date', required: true }, { name: 'valid_until', label: '金利の有効期限', type: 'date', required: true },
  { name: 'source_name', label: '出典名' }, { name: 'source_url', label: '出典URL', type: 'url', required: true },
  { name: 'checked_at', label: '出典の確認日', type: 'date' },
]
const borrowingFields: FieldSpec[] = [
  { name: 'years_min', label: '返済期間の下限（年）', numeric: true }, { name: 'years_max', label: '返済期間の上限（年）', numeric: true },
  { name: 'loan_amount_min', label: '借入額の下限（円）', numeric: true }, { name: 'loan_amount_max', label: '借入額の上限（円）', numeric: true },
  { name: 'rate_over_90_percent', label: '融資率9割超の参考金利（年率％）', numeric: true, hint: '資料に該当する参考金利が記載されている場合のみ入力します。' },
]

function Field({ path, label, value, change, errors, disabled, numeric, type, required, area, hint }: {
  path: string, label: string, value: unknown, change: (value: string) => void, errors: FieldErrors, disabled?: boolean,
  numeric?: boolean, type?: string, required?: boolean, area?: boolean, hint?: string,
}) {
  const id = `admin-field-${path.replaceAll('.', '-')}`
  const message = errors[path]
  const props = { id, 'aria-label': label, 'aria-invalid': !!message, 'aria-describedby': message ? `${id}-error` : undefined,
    disabled, value: value == null ? '' : String(value), onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => change(event.target.value) }
  return <label className={`admin-field ${area ? 'full-field' : ''} ${message ? 'has-error' : ''}`} htmlFor={id}>
    <span>{label}{required && <small className="required-label">確認時必須</small>}</span>
    {area ? <textarea {...props} rows={3} /> : <input {...props} type={numeric ? 'number' : type || 'text'} step={numeric ? 'any' : undefined} />}
    {message ? <span className="field-error" id={`${id}-error`} role="alert">{message}</span> : hint && <small className="field-hint">{hint}</small>}
  </label>
}

function candidate(data: Json): Json {
  const review = copy(data.reviewed)
  // A financial-only SDK result has no property. These values are a review candidate, never SDK raw.
  if (data.revision !== 0 || review.document?.scope || !review.rates?.length || Object.keys(review.property || {}).length) return review
  const values = (key: string): string[] => [...new Set<string>(review.rates.map((rate: Json) => String(rate[key] || '')).filter(Boolean))]
  return { ...review, document: { ...review.document, scope: 'general', source_name: values('source_name').join(' / '),
    source_url: review.rates[0].source_url || '', source_urls: values('source_url'), checked_at: values('checked_at').sort()[0] || '',
    effective_date: values('effective_date').sort().at(-1) || '', valid_until: values('valid_until').sort()[0] || '',
    scope_notes: '金融商品の参考金利。各商品の出典・期間・適用条件を照合してください。特定物件への適用や審査承認を意味しません。' } }
}

export default function AdminReview({ document, auth, reload, onUpdated, boundaryReady, section, onDirty, onSection }: {
  document: Json, auth: string, reload: () => Promise<void>, onUpdated: (document: Json) => void,
  boundaryReady: boolean, section: ReviewSection, onDirty: (dirty: boolean) => void, onSection: (section: ReviewSection) => void,
}) {
  const [envelope, setEnvelope] = useState<Json | null>(null)
  const [review, setReview] = useState<Json | null>(null)
  const [usage, setUsage] = useState('unclassified')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState('')
  const [loading, setLoading] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [checked, setChecked] = useState(false)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [errorFocusRequest, setErrorFocusRequest] = useState(0)
  const reviewRef = useRef<HTMLElement>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [diagnostic, setDiagnostic] = useState('')
  const [jsonError, setJsonError] = useState('')
  const editable = ['parsed', 'confirmed', 'published'].includes(document.status)
  const scope = review?.document?.scope || 'property'
  const propertyScope = scope === 'property'

  useEffect(() => {
    let current = true
    setEnvelope(null); setReview(null); setDirty(false); onDirty(false); setChecked(false); setErrors({}); setError(''); setSuccess(''); setJsonError('')
    if (!['parsed', 'confirmed', 'published'].includes(document.status)) return
    setLoading(true)
    api<Json>(`/admin/documents/${document.id}/draft`, {}, undefined, auth).then(data => {
      if (!current) return
      const next = candidate(data)
      setEnvelope(data); setReview(next); setDiagnostic(pretty(next)); setUsage(data.usage || 'unclassified'); setNote(data.note || '')
    }).catch(error => { if (current) setError(errorText(error)) }).finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [document.id, document.parsed_at, document.confirmed_at, document.confirmation_id, document.usage_changed_at, document.published_version, auth])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  useEffect(() => {
    if (!Object.keys(errors).length) return
    const target = reviewRef.current?.querySelector<HTMLElement>('[aria-invalid="true"], .admin-field-error-links')
    // Prefer the editable field when it is in this section; otherwise show the existing section links.
    const field = reviewRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]') || target
    field?.scrollIntoView({ block: 'center' })
    field?.focus({ preventScroll: true })
  }, [errorFocusRequest, section])

  function markDirty() { setDirty(true); onDirty(true); setChecked(false); setSuccess('') }
  function update(next: Json) { setReview(next); setDiagnostic(pretty(next)); markDirty() }
  function patch(section: 'property' | 'document', key: string, value: string, numeric = false) {
    if (!review) return
    const next = copy(review)
    next[section] = { ...next[section] }
    if (numeric && value === '') delete next[section][key]
    else next[section][key] = numeric ? Number(value) : value
    update(next); setErrors(current => { const result = { ...current }; delete result[`${section}.${key}`]; return result })
  }
  function changeScope(value: string) {
    if (!review || value === scope) return
    const next = copy(review)
    next.document = { ...next.document }
    next.property = { ...next.property }
    if (scope === 'property' && value !== 'property' && Object.keys(next.property).length) {
      if (!window.confirm('共通・会社資料へ変更すると、この下書きの具体物件情報を外します。出典・日付・注意事項は資料欄に引き継ぎ、資料欄に既存の値がある場合はその値を保持します。資料本文・FAQ・金利は保持されるため、新しい知識範囲に合う内容か必ず確認してください。SDKの元結果・確認済みデータ・公開版は変わりません。続けますか？')) return
      for (const { name } of sourceFields) if (next.document[name] == null || next.document[name] === '') {
        if (next.property[name] != null) next.document[name] = copy(next.property[name])
      }
      next.property = {}
    } else if (value === 'property') {
      for (const { name } of sourceFields) if (next.property[name] == null || next.property[name] === '') {
        if (next.document[name] != null) next.property[name] = copy(next.document[name])
      }
    }
    next.document.scope = value
    update(next); setErrors({})
  }
  function patchItem(section: 'faq' | 'rates' | 'knowledge', index: number, key: string, value: string, numeric = false) {
    if (!review) return
    const next = copy(review)
    const item = next[section][index]
    if (key === 'reference.location') item.reference = { ...item.reference, location: value }
    else if (numeric && value === '' && key !== 'rate') delete item[key]
    else item[key] = numeric ? value === '' ? null : Number(value) : value
    update(next); setErrors(current => { const result = { ...current }; delete result[`${section}.${index}.${key}`]; return result })
  }
  function addItem(section: 'faq' | 'rates' | 'knowledge') {
    if (!review) return
    const next = copy(review)
    const item = section === 'faq' ? { question: '', answer: '', reference: { location: '' } } : section === 'knowledge' ? { text: '', reference: { location: '' } } : { bank: '', product: '', rate_type: '', rate: null, notes: '', effective_date: '', valid_until: '', source_url: '' }
    next[section] = [...(next[section] || []), item]; update(next)
  }
  function removeItem(section: 'faq' | 'rates' | 'knowledge', index: number) {
    if (!review) return
    const next = copy(review); next[section].splice(index, 1); update(next); setErrors({})
  }
  function editEquipment(index: number, value: string) {
    if (!review) return
    const next = copy(review); next.property.equipment[index] = value; update(next)
  }
  function editCondition(rateIndex: number, conditionIndex: number, value: string) {
    if (!review) return
    const next = copy(review)
    next.rates[rateIndex].conditions[conditionIndex] = value
    update(next)
    setErrors(current => { const result = { ...current }; delete result[`rates.${rateIndex}.conditions.${conditionIndex}`]; return result })
  }
  function changeConditions(rateIndex: number, conditionIndex?: number) {
    if (!review) return
    const next = copy(review)
    const conditions = [...(next.rates[rateIndex].conditions || [])]
    if (conditionIndex === undefined) conditions.push('')
    else conditions.splice(conditionIndex, 1)
    next.rates[rateIndex].conditions = conditions
    update(next); setErrors({})
  }
  function presentErrors(next: FieldErrors) { setErrors(next); setErrorFocusRequest(current => current + 1) }
  function handleError(error: unknown) { setError(errorText(error)); presentErrors(error instanceof ApiError ? error.fieldErrors : {}) }
  async function parse() {
    setBusy('parse'); setError(''); setSuccess('')
    try { const data = await api<Json>(`/admin/documents/${document.id}/parse`, post(), undefined, auth); onUpdated(data); await reload(); setSuccess('資料を読み取りました。候補の内容と出典を確認してください。') }
    catch (error) { handleError(error); await reload() } finally { setBusy('') }
  }
  async function save() {
    if (!review || !envelope) return
    setBusy('save'); setError(''); setErrors({}); setSuccess('')
    try {
      const data = await api<Json>(`/admin/documents/${document.id}/draft`, post({ document_sha256: envelope.document_sha256, source_revision: envelope.source_revision, revision: envelope.revision, reviewed: review, usage, note }), undefined, auth)
      setEnvelope(data); setReview(copy(data.reviewed)); setDiagnostic(pretty(data.reviewed)); setDirty(false); onDirty(false); setChecked(false)
      setSuccess('下書きを保存しました。再度開いても内容は保持されます。確認・公開はまだ行われません。'); await reload()
    } catch (error) { handleError(error) } finally { setBusy('') }
  }
  async function confirm() {
    if (!envelope || dirty || !checked) return
    if (!note.trim()) { presentErrors({ note: '確認した内容を確認メモに入力してください。' }); return }
    setBusy('confirm'); setError(''); setErrors({}); setSuccess('')
    try {
      const data = await api<Json>(`/admin/documents/${document.id}/draft/confirm`, post({ document_sha256: envelope.document_sha256, source_revision: envelope.source_revision, revision: envelope.revision, note }), undefined, auth)
      onUpdated(data); await reload(); setChecked(false); setSuccess('内容と用途を確認済みにしました。公開管理で対象資料を選び、別途公開してください。')
    } catch (error) { handleError(error) } finally { setBusy('') }
  }
  async function changeUsage() {
    if (!note.trim()) { presentErrors({ note: '用途を再確認する理由を確認メモに入力してください。' }); return }
    if (!window.confirm('この資料の旧確認を無効にします。新しい確認・公開が必要になります。続けますか？')) return
    setBusy('usage'); setError('')
    try { const data = await api<Json>(`/admin/documents/${document.id}/usage`, post({ usage, note }), undefined, auth); onUpdated(data); await reload(); setChecked(false); setSuccess('旧確認を無効にしました。内容と用途を再確認してください。') }
    catch (error) { handleError(error) } finally { setBusy('') }
  }
  function applyDiagnostic() {
    try {
      const next = JSON.parse(diagnostic)
      if (!next || Array.isArray(next) || typeof next.property !== 'object' || !Array.isArray(next.knowledge) || !Array.isArray(next.faq) || !Array.isArray(next.rates)) throw new Error()
      update(next); setJsonError('')
    } catch { setJsonError('入力の形式を確認してください。物件・資料本文・FAQ・金利の構造が必要です。') }
  }

  const metadataTarget = propertyScope ? 'property' : 'document'
  const itemCount = (name: string) => review?.[name]?.length || 0
  const errorSections = [...new Set(Object.keys(errors).map(path => path.startsWith('faq.') ? 'faq' : path.startsWith('rates.') ? 'rates' : path.startsWith('property.equipment') ? 'equipment' : path.startsWith('property.') ? 'property' : path.startsWith('knowledge.') || path.startsWith('document.') ? 'documents' : '').filter(Boolean))] as ReviewSection[]
  return <section ref={reviewRef} className="document-detail card admin-review" aria-label="資料の業務編集">
    <div className="section-heading"><div><span className="eyebrow">資料の確認・編集</span><h2>{document.filename}</h2></div><span className={`badge ${document.status}`}>{stateNames[document.status] || document.status}</span></div>
    <dl className="metadata"><div><dt>登録</dt><dd>{fmtDate(document.created_at)}</dd></div><div><dt>SDK解析</dt><dd>{fmtDate(document.parsed_at)}</dd></div><div><dt>業務確認</dt><dd>{fmtDate(document.confirmed_at)}</dd></div><div><dt>公開版</dt><dd>{document.published_version ? `v${document.published_version}` : '未公開'}</dd></div></dl>
    <Alert message={document.update_cancelled ? 'この差し替え候補は取り消されています。必要な場合は元の資料から改めて更新を準備してください。' : ''} tone="info"/><Alert message={error || document.error?.message || (typeof document.error === 'string' ? document.error : '')} /><Alert message={success} tone="success" />
    {!editable ? <div className="parse-step"><Icon name="file" size={31} /><h3>資料の内容を読み取る</h3><p>SDKの解析結果を保存し、識別できた項目を編集候補に反映します。<br />読み取り後も社員による照合・確認が必要です。</p><button className="button primary" onClick={parse} disabled={!!busy || !boundaryReady || !!document.update_cancelled || document.status === 'error'}>{busy === 'parse' ? '資料を読み取っています…' : 'SDK解析を実行'}<Icon name="arrow" size={17} /></button>{document.status === 'error' && <p className="small-note">ファイル形式・読み取り内容を確認し、修正した資料を新しく登録してください。</p>}</div> : loading ? <p role="status">保存内容を読み込んでいます…</p> : review && envelope && <>
      <div className="review-notice"><Icon name="check" /><p>読み取り結果は編集候補です。資料と照合して修正・追加入力してください。手入力はSDKの元結果を変更せず、下書き・確認・公開を別々に保存します。</p></div>
      {document.active_publication_confirmation_id && document.active_publication_confirmation_id !== document.confirmation_id && <Alert tone="info" message={`現在の公開版は確認 #${document.active_publication_confirmation_id} を使用しています。このフォームは新しい改訂候補です。公開するまでは、旧版の内容と確認根拠を使用します。`}/>} 
      {errorSections.length > 0 && <div className="admin-field-error-links" role="alert" tabIndex={-1}><span>入力内容を確認してください：</span>{errorSections.map(value => <button className="button subtle" key={value} onClick={() => onSection(value)}>{sectionNames[value]}</button>)}</div>}
      <div className="admin-draft-status" role="status"><strong>{dirty ? '未保存の変更があります' : envelope.saved_at ? `下書き保存済み · ${fmtDate(envelope.saved_at)}` : '編集候補 · 下書き未保存'}</strong><span>この資料に紐づく下書き / 第{envelope.revision || 0}版</span></div>
      {envelope.stale && <Alert tone="info" message="下書き保存後に資料の確認・公開状態が変わっています。現在の資料と照合し直してから、下書きを保存してください。" />}
      <div className="admin-edit-section-heading"><h3>{sectionNames[section]}</h3><span>{section === 'faq' ? `${itemCount('faq')}件` : section === 'rates' ? `${itemCount('rates')}件` : ''}</span></div>
      {section === 'property' && (propertyScope ? <div className="property-edit-grid">{propertyFields.map(field => <Field key={field.name} {...field} path={`property.${field.name}`} value={review.property?.[field.name]} errors={errors} change={value => patch('property', field.name, value, field.numeric)} disabled={!!busy} />)}</div> : <Alert tone="info" message="この資料は共通知識または会社資料です。物件情報を登録する場合は、資料管理で知識範囲を具体物件に変更し、適用範囲を確認してください。" />)}
      {section === 'equipment' && (propertyScope ? <>
        <p className="small-note">名称と説明を一つの欄に記入してください。元資料で確認できる設備だけを登録します。</p>
        {errors['property.equipment'] && <p className="field-error" role="alert">{errors['property.equipment']}</p>}
        {(review.property?.equipment || []).map((text: string, index: number) => <div className="admin-list-editor" key={index}><Field path={`property.equipment.${index}`} label={`設備名称・説明 ${index + 1}`} value={text} change={value => editEquipment(index, value)} errors={errors} area disabled={!!busy} /><button className="button subtle delete-button" onClick={() => { const next = copy(review); next.property.equipment.splice(index, 1); update(next) }} disabled={!!busy} aria-label={`設備 ${index + 1} を削除`}>削除</button></div>)}
        {!review.property?.equipment?.length && <p className="admin-empty-message">設備情報はまだありません。</p>}
        <button className="button secondary" disabled={!!busy || (review.property?.equipment?.length || 0) >= 100} onClick={() => { const next = copy(review); next.property.equipment = [...(next.property.equipment || []), '']; update(next) }}>設備を追加</button>
      </> : <Alert tone="info" message="設備情報は具体物件の資料で編集できます。共通・会社資料とは分けて確認してください。" />)}
      {section === 'faq' && <>
        <p className="small-note">回答はこの資料の確認範囲内で入力してください。手入力した内容も確認・公開前には案内に使用されません。</p>
        {(review.faq || []).map((item: Json, index: number) => <article className="admin-item-card" key={index} aria-label={`FAQ ${index + 1}`}><div className="section-heading"><h4>FAQ {index + 1}</h4><button className="button subtle delete-button" aria-label={`FAQ ${index + 1} を削除`} disabled={!!busy} onClick={() => removeItem('faq', index)}>削除</button></div><div className="property-edit-grid"><Field path={`faq.${index}.question`} label="質問" value={item.question} errors={errors} change={value => patchItem('faq', index, 'question', value)} area required disabled={!!busy} /><Field path={`faq.${index}.answer`} label="回答" value={item.answer} errors={errors} change={value => patchItem('faq', index, 'answer', value)} area required disabled={!!busy} /><Field path={`faq.${index}.reference.location`} label="出典の位置（ページ・章）" value={item.reference?.location} errors={errors} change={value => patchItem('faq', index, 'reference.location', value)} disabled={!!busy} /><Field path={`faq.${index}.source_url`} label="出典URL（任意）" value={item.source_url} errors={errors} change={value => patchItem('faq', index, 'source_url', value)} type="url" disabled={!!busy} /></div><p className="field-hint">登録元資料：{document.filename}</p></article>)}
        {!itemCount('faq') && <p className="admin-empty-message">FAQはまだありません。</p>}<button className="button secondary" disabled={!!busy || itemCount('faq') >= 50} onClick={() => addItem('faq')}>FAQを追加</button>
      </>}
      {section === 'rates' && <>
        <p className="small-note">参考金利・適用条件・借入条件は金融機関の資料どおりに入力してください。記載のない条件を推測して補わないでください。</p>
        {(review.rates || []).map((item: Json, index: number) => <article className="admin-item-card" key={index} aria-label={`金利商品 ${index + 1}`}><div className="section-heading"><h4>{item.product || `金利商品 ${index + 1}`}</h4><button className="button subtle delete-button" disabled={!!busy} aria-label={`金利商品 ${index + 1} を削除`} onClick={() => removeItem('rates', index)}>削除</button></div><div className="property-edit-grid">{rateFields.map(field => <Field key={field.name} {...field} path={`rates.${index}.${field.name}`} value={item[field.name]} errors={errors} change={value => patchItem('rates', index, field.name, value, field.numeric)} disabled={!!busy} />)}</div><h5>適用条件（項目ごと）</h5><p className="field-hint">項目別の適用条件を登録順に表示します。上の補足欄や数値の借入条件とは別に保存します。</p>{errors[`rates.${index}.conditions`] && <p className="field-error" role="alert">{errors[`rates.${index}.conditions`]}</p>}{(item.conditions || []).map((condition: unknown, conditionIndex: number) => typeof condition === 'string' ? <div className="admin-list-editor" key={conditionIndex}><Field path={`rates.${index}.conditions.${conditionIndex}`} label={`適用条件 ${conditionIndex + 1}`} value={condition} errors={errors} area disabled={!!busy} change={value => editCondition(index, conditionIndex, value)}/><button className="button subtle delete-button" disabled={!!busy} aria-label={`金利商品 ${index + 1} の適用条件 ${conditionIndex + 1} を削除`} onClick={() => changeConditions(index, conditionIndex)}>削除</button></div> : <div className="admin-preserved-condition" key={conditionIndex}><p className="small-note">条件 {conditionIndex + 1} は拡張形式のため、そのまま保持します。必要な場合は診断用の詳細で確認してください。</p><pre className="json-view">{pretty(condition)}</pre></div>)}{!item.conditions?.length && <p className="admin-empty-message">項目ごとの適用条件は登録されていません。</p>}<button className="button secondary" disabled={!!busy} onClick={() => changeConditions(index)}>適用条件を追加</button><h5>借入条件</h5><p className="field-hint">資料に条件がある場合のみ入力します。空欄は条件を追加しません。</p><div className="property-edit-grid">{borrowingFields.map(field => <Field key={field.name} {...field} path={`rates.${index}.${field.name}`} value={item[field.name]} errors={errors} change={value => patchItem('rates', index, field.name, value, true)} disabled={!!busy} />)}<Field path={`rates.${index}.max_loan_to_value`} label="融資率の上限（％）" value={item.max_loan_to_value == null ? '' : Number(item.max_loan_to_value) * 100} errors={errors} numeric change={value => patchItem('rates', index, 'max_loan_to_value', value === '' ? '' : String(Number(value) / 100), true)} hint="例：90％は90と入力します。保存時は既存の比率形式を維持します。" disabled={!!busy} /></div><Field path={`rates.${index}.reference.location`} label="出典の位置（シート・行など）" value={item.reference?.location} errors={errors} change={value => patchItem('rates', index, 'reference.location', value)} disabled={!!busy} /><p className="field-hint">登録元資料：{document.filename}。このフォームにない既存条件も保存時に保持します。</p></article>)}
        {!itemCount('rates') && <p className="admin-empty-message">金利商品はまだありません。</p>}<button className="button secondary" disabled={!!busy || itemCount('rates') >= 10} onClick={() => addItem('rates')}>金利商品を追加</button>
      </>}
      {section === 'documents' && <>
        <label className="admin-field">知識範囲<select aria-label="知識範囲" disabled={!!busy} value={scope} onChange={event => changeScope(event.target.value)}><option value="property">具体物件</option><option value="general">共通住宅購入知識</option><option value="company">会社サービス・接客規則</option></select><span className="field-error">{errors['document.scope']}</span></label>
        <p className="small-note">知識範囲は資料の内容、資料用途は顧客への使用可否です。それぞれ確認してください。</p>
        <p className="small-note">知識範囲を変更しても資料本文・FAQ・金利は保持されます。具体物件の内容を共通知識として扱わないよう、本文と回答も資料に照らして確認してください。</p>
        <details className="admin-sdk-preview" open><summary>SDKが読み取った本文（原文・変更不可）</summary>{(document.normalized?.knowledge || []).length ? document.normalized.knowledge.map((item: Json, index: number) => <div className="sdk-text-item" key={index}><span>{item.reference?.location || `本文 ${index + 1}`}</span><p>{item.text}</p></div>) : <p className="small-note">本文の候補はありません。Excelの金利行は「住宅ローン」で確認できます。SDKが取得した全内容は診断用の詳細に保持されています。</p>}</details>
        <h4>案内に使用する資料本文</h4><p className="small-note">自動整理できない資料は、対応する業務項目を各フォームへ手動で入力してください。全てのPDFを正しく自動整理できるものではありません。下の候補を編集しても、上のSDK原文は変わりません。</p>
        {(review.knowledge || []).map((item: Json, index: number) => <article className="admin-item-card" key={index}><div className="section-heading"><h4>資料本文 {index + 1}</h4><button className="button subtle delete-button" onClick={() => removeItem('knowledge', index)} disabled={!!busy} aria-label={`資料本文 ${index + 1} を削除`}>削除</button></div><Field path={`knowledge.${index}.text`} label="資料本文" value={item.text} errors={errors} change={value => patchItem('knowledge', index, 'text', value)} area disabled={!!busy} /><Field path={`knowledge.${index}.reference.location`} label="資料の位置（ページ・章）" value={item.reference?.location} errors={errors} change={value => patchItem('knowledge', index, 'reference.location', value)} disabled={!!busy} /></article>)}
        <button className="button secondary" disabled={!!busy || itemCount('knowledge') >= 100} onClick={() => addItem('knowledge')}>資料本文を追加</button>
      </>}
      <details className="admin-source-panel" open={section === 'documents' || sourceFields.some(field => errors[`${metadataTarget}.${field.name}`])}><summary>出典・適用範囲・有効期間</summary><p className="small-note">この資料全体に適用する出典と日付です。金利商品ごとの条件は住宅ローン欄で確認します。</p><div className="property-edit-grid">{sourceFields.map(field => <Field key={field.name} {...field} path={`${metadataTarget}.${field.name}`} value={review[metadataTarget]?.[field.name]} errors={errors} change={value => patch(metadataTarget, field.name, value)} disabled={!!busy} />)}</div></details>
      <div className="admin-confirm-section"><h3>下書きの保存と業務確認</h3><label className="admin-field">資料用途<select aria-label="資料用途" value={usage} disabled={!!busy} onChange={event => { setUsage(event.target.value); markDirty() }}><option value="unclassified">未確認</option><option value="customer">顧客への案内に使用可</option><option value="internal">社内専用</option></select><span className="field-error">{errors.usage}</span></label><p className="small-note">現在の確認済み用途：{usageNames[document.usage || 'unclassified']}。選択・下書き保存だけでは承認されません。公開中の原資料・過去の版も変わりません。</p><Field path="note" label="確認メモ" value={note} errors={errors} area change={value => { setNote(value); markDirty(); setErrors(current => ({ ...current, note: '' })) }} hint="照合した内容、手入力した項目、出典・適用条件などを記録してください。" disabled={!!busy} />
        <button className="button secondary" onClick={save} disabled={!!busy || !boundaryReady}>{busy === 'save' ? '下書きを保存しています…' : '下書きを保存'}<Icon name="file" size={17} /></button>
        {['confirmed', 'published'].includes(document.status) && !envelope.confirmed_at && <Alert tone="info" message="通常の更新では新しい改訂を確認します。公開するまでは、期限内で用途が取り消されていない旧公開版とその確認根拠を引き続き使用します。" />}
        <label className="check-field"><input type="checkbox" aria-label="資料と下書きの内容・用途を確認しました" checked={checked} disabled={!!busy || dirty || !envelope.saved_at || !!envelope.confirmed_at} onChange={event => setChecked(event.target.checked)} /><span>資料と保存済み下書きを照合し、内容・適用条件・出典・資料用途を確認しました。</span></label>
        {dirty ? <p className="small-note">変更を下書きに保存してから確認してください。</p> : !envelope.saved_at ? <p className="small-note">まず「下書きを保存」を押してください。</p> : envelope.confirmed_at ? <p className="small-note">この下書きは確認済みです。新しい編集内容を下書きに保存すると、再度確認できます。</p> : <p className="small-note">確認欄は社員が実際に照合した後にチェックしてください。</p>}
        <button className="button primary" onClick={confirm} disabled={!boundaryReady || !!busy || dirty || !checked || !envelope.saved_at || !!envelope.confirmed_at}>{busy === 'confirm' ? '業務確認を保存しています…' : '管理者確認を保存'}<Icon name="check" size={17} /></button>
        <p className="small-note">確認後も自動公開されません。公開管理の草案でこの改訂への差し替えを選び、差分を確認して公開します。通常の更新で旧確認・旧公開版を上書きしません。</p>
        {['confirmed', 'published'].includes(document.status) && <details className="admin-source-panel"><summary>資料用途だけを再確認する</summary><p className="small-note">内容を確認する前に用途を取り消す場合に使います。旧確認を無効にし、再確認が必要になります。</p><button className="button subtle" disabled={!boundaryReady || !!busy} onClick={changeUsage}>用途を再確認（旧確認を無効化）</button></details>}
      </div>
      <details className="admin-diagnostics"><summary>開発・診断用の詳細</summary><p className="small-note">日常の入力は上のフォームで行います。フォームで扱っていない既存項目はそのまま保持します。</p><details><summary>SDKの元の解析結果（変更不可）</summary><pre className="json-view">{pretty(document.raw)}</pre></details><details><summary>標準化された解析結果（変更不可）</summary><pre className="json-view">{pretty(document.normalized)}</pre></details><details><summary>確認候補のJSON（高度な編集）</summary><label className="sr-only" htmlFor="review-json">確認データ JSON</label><textarea id="review-json" className="json-editor" value={diagnostic} spellCheck={false} onChange={event => setDiagnostic(event.target.value)} rows={15} disabled={!!busy} /><Alert message={jsonError} /><button className="button secondary" onClick={applyDiagnostic} disabled={!!busy}>JSONをフォームへ反映</button><p className="small-note">反映後に下書きを保存してください。SDKの元結果は変更しません。</p></details></details>
    </>}
  </section>
}
