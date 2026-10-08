import { useEffect, useState } from 'react'
import { Alert, Icon, SourceList } from './App'
import { ApiError, api, errorText, fmtDate, fmtMoney, post } from './api'
import type { Json } from './api'
import { usageNames } from './AdminReview'

type PublicationItem = { document_id: string, confirmation_id: number, replaces_document_id?: string, replaces_confirmation_id?: number }
const keyOf = (item: PublicationItem) => `${item.document_id}:${item.confirmation_id}`
const pretty = (value: unknown) => JSON.stringify(value, null, 2)
const rateLabels: Record<string, string> = { bank:'金融機関', product:'商品名', rate_type:'金利タイプ', rate:'参考金利', notes:'適用条件の補足', conditions:'適用条件', years_min:'返済期間の下限', years_max:'返済期間の上限', loan_amount_min:'借入額の下限', loan_amount_max:'借入額の上限', max_loan_to_value:'融資率の上限', rate_over_90_percent:'融資率9割超の参考金利', effective_date:'基準日', valid_until:'有効期限' }
const shortRevision = (value: unknown) => String(value || '未記録').slice(0, 8)
function visibleValue(value: unknown, label = ''): string {
  if (value == null || value === '' || (Array.isArray(value) && !value.length)) return 'なし'
  if (typeof value === 'number') return label.includes('価格') || label.includes('借入額') ? fmtMoney(value) : label.includes('金利') ? `年 ${value}%` : label.includes('返済期間') ? `${value}年` : label.includes('融資率の上限') ? `${Number(value) * 100}%` : String(value)
  if (typeof value === 'string') return label === '資料用途' ? usageNames[value] || value : label === '資料範囲' ? ({property:'具体物件',general:'共通住宅購入知識',company:'会社サービス・接客規則'} as Record<string,string>)[value] || value : value
  if (Array.isArray(value)) return value.map(item => visibleValue(item, label)).join('\n\n')
  if (typeof value === 'object') {
    const item = value as Json
    if ('question' in item || 'answer' in item) return `質問：${item.question || 'なし'}\n回答：${item.answer || 'なし'}`
    if ('bank' in item || 'product' in item || 'rate' in item) return Object.entries(rateLabels).filter(([key]) => key in item).map(([key,title]) => `${title}：${visibleValue(item[key], title)}`).join('\n')
    if ('text' in item) return String(item.text)
    return '拡張項目（診断用の詳細で確認してください）'
  }
  return String(value)
}
function historyItems(version: Json): Json[] {
  if (Array.isArray(version.document_revisions)) return version.document_revisions
  if (Array.isArray(version.items)) return version.items
  return (version.document_ids || Object.keys(version.document_approvals || {})).map((document_id: string) => ({ document_id,
    confirmation_id: version.document_approvals?.[document_id], revision_id: version.document_revisions?.[document_id] }))
}

export default function AdminPublication({ auth, documents, versions, reload, boundaryReady, onDirty }: {
  auth: string, documents: Json[], versions: Json[], reload: () => Promise<void>, boundaryReady: boolean, onDirty: (dirty: boolean) => void,
}) {
  const [pane, setPane] = useState('edit')
  const [drafts, setDrafts] = useState<Json[]>([])
  const [draft, setDraft] = useState<Json | null>(null)
  const [items, setItems] = useState<PublicationItem[]>([])
  const [options, setOptions] = useState<Json[]>([])
  const [note, setNote] = useState('')
  const [addition, setAddition] = useState('')
  const [preview, setPreview] = useState<Json | null>(null)
  const [checked, setChecked] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [submitKey, setSubmitKey] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [success, setSuccess] = useState('')
  const current = versions[0]
  const createLabel = current ? '現在の公開版から草案を作成' : '初めての公開草案を作成'

  async function refreshDrafts() {
    const data = await api<Json[]>('/admin/publication-drafts', {}, undefined, auth)
    setDrafts(data)
    return data
  }
  function useDraft(value: Json) {
    setDraft(value); setItems((value.items || []).map((item: Json) => ({ document_id: item.document_id, confirmation_id: item.confirmation_id,
      ...(item.replaces_document_id ? { replaces_document_id: item.replaces_document_id, replaces_confirmation_id: item.replaces_confirmation_id } : {}) })))
    setNote(value.note || ''); setDirty(false); onDirty(false); setPreview(null); setChecked(false); setSubmitKey(''); setError('')
  }
  useEffect(() => {
    let active = true
    refreshDrafts().then(async data => {
      const pending = data.find(value => value.state === 'open' && !value.published_version && !value.cancelled_at)
      if (!pending) return
      const value = await api<Json>(`/admin/publication-drafts/${pending.id}`, {}, undefined, auth)
      if (active) useDraft(value)
    }).catch(error => { if (active) setError(errorText(error)) })
    return () => { active = false; onDirty(false) }
  }, [auth])
  useEffect(() => {
    let active = true
    Promise.all(documents.filter(document => ['parsed', 'confirmed', 'published'].includes(document.status)).map(async document => {
      const data = await api<Json[]>(`/admin/documents/${document.id}/revisions`, {}, undefined, auth)
      return data.filter(value => value.usage === 'customer' && !value.cancelled && !value.revoked).map(value => ({ ...value, document_id: document.id, filename: document.filename }))
    })).then(values => { if (active) setOptions(values.flat()) }).catch(error => { if (active) setError(errorText(error)) })
    return () => { active = false }
  }, [auth, documents])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  function markDirty() { setDirty(true); onDirty(true); setPreview(null); setChecked(false); setSubmitKey(''); setSuccess('') }
  function identify(item: PublicationItem): Json {
    return options.find(option => keyOf(option as PublicationItem) === keyOf(item)) || draft?.items?.find((option: Json) => keyOf(option as PublicationItem) === keyOf(item)) || { ...item, filename: documents.find(document => document.id === item.document_id)?.filename || '資料' }
  }
  function label(item: Json) { return `${item.filename || '資料'} / 確認 #${item.confirmation_id} · 改訂 ${shortRevision(item.revision_id)}` }
  function changeItem(index: number, selected: string) {
    const option = options.find(value => keyOf(value as PublicationItem) === selected)
    if (!option) return
    const previous = items[index]
    const next: PublicationItem = { document_id: option.document_id, confirmation_id: option.confirmation_id }
    const original = (draft?.items || []).find((item: Json) => item.document_id === previous.document_id && item.confirmation_id === previous.confirmation_id)
    const baseline = versions.find(value => value.version === draft?.base_version)
    const replacedId = previous.replaces_document_id || original?.replaces_document_id || previous.document_id
    const replacedConfirmation = baseline?.document_approvals?.[replacedId]
    if (next.document_id !== replacedId && replacedConfirmation) { next.replaces_document_id = replacedId; next.replaces_confirmation_id = replacedConfirmation }
    setItems(values => values.map((value, position) => position === index ? next : value)); markDirty()
  }
  async function create(restoreVersion?: number) {
    if (dirty && !window.confirm('保存していない公開草案の変更があります。破棄して新しい草案を作成しますか？')) return
    setBusy('create'); setError(''); setSuccess('')
    try {
      const data = await api<Json>(restoreVersion == null ? '/admin/publication-drafts' : `/admin/versions/${restoreVersion}/restore-draft`, post(restoreVersion == null ? {} : undefined), undefined, auth)
      useDraft(data); setPane('edit'); await refreshDrafts()
      setSuccess(restoreVersion == null ? current ? '現在の公開版を基に草案を作成しました。変更しない資料はそのまま残ります。' : '初めての公開草案を作成しました。「確認済み資料を追加」で、顧客への案内に使用可と確認した資料を選び、必要な資料を一つずつ追加してください。' : `v${restoreVersion} の内容から復元草案を作成しました。現在の有効性を確認してから、新しい版として公開します。`)
    } catch (error) { setError(errorText(error)) } finally { setBusy('') }
  }
  async function load(id: string) {
    if (dirty && !window.confirm('保存していない変更を破棄して、別の公開草案を開きますか？')) return
    setBusy('load'); setError('')
    try { useDraft(await api<Json>(`/admin/publication-drafts/${id}`, {}, undefined, auth)); setSuccess('保存済み草案を開きました。') }
    catch (error) { setError(errorText(error)) } finally { setBusy('') }
  }
  async function save() {
    if (!draft) return
    setBusy('save'); setError(''); setSuccess('')
    try {
      const data = await api<Json>(`/admin/publication-drafts/${draft.id}`, post({ revision: draft.revision, items, note }), undefined, auth)
      useDraft(data); await refreshDrafts(); setSuccess('公開草案を保存しました。ページを再読み込みしても内容は保持されます。接客にはまだ反映されません。')
    } catch (error) { setError(errorText(error)) } finally { setBusy('') }
  }
  async function inspect() {
    if (!draft || dirty) return
    if (!note.trim()) { setFieldErrors({ note: '公開する変更の説明を入力してください。' }); return }
    setBusy('preview'); setError(''); setSuccess(''); setChecked(false)
    try {
      const data = await api<Json>(`/admin/publication-drafts/${draft.id}/preview`, post(), undefined, auth)
      setPreview(data); setSubmitKey(crypto.randomUUID())
    } catch (error) { setPreview(null); setError(errorText(error)) } finally { setBusy('') }
  }
  async function publish() {
    if (!draft || !preview || !checked || dirty) return
    setBusy('publish'); setError(''); setSuccess('')
    try {
      const snapshot = await api<Json>('/admin/publish', post({ draft_id: draft.id, draft_revision: preview.draft_revision, preview_token: preview.preview_token, idempotency_key: submitKey }), undefined, auth)
      await reload(); await refreshDrafts(); setPreview(null); setChecked(false); setDraft(null); setItems([]); setPane('published')
      setSuccess(`公開版 v${snapshot.version} を作成しました。新しい接客から反映されます。有効な既存接客は開始時の版を維持します。`)
    } catch (error) { setError(errorText(error)); setFieldErrors(error instanceof ApiError ? error.fieldErrors : {}) } finally { setBusy('') }
  }
  const pendingDrafts = drafts.filter(value => value.state === 'open' && !value.published_version && !value.cancelled_at)
  return <div className="admin-publication-workspace">
    <div className="admin-publish-options"><button className={`button ${pane === 'edit' ? 'primary' : 'secondary'}`} onClick={() => setPane('edit')}>公開内容を編集</button><button className={`button ${pane === 'published' ? 'primary' : 'secondary'}`} onClick={() => setPane('published')}>現在の公開情報</button><button className={`button ${pane === 'versions' ? 'primary' : 'secondary'}`} onClick={() => setPane('versions')}>公開バージョン履歴</button></div>
    <Alert message={error}/><Alert message={success} tone="success"/>
    {pane === 'edit' && <section className="card admin-publication-draft" aria-label="公開草案の編集">
      <div className="section-heading"><div><span className="eyebrow">公開草案</span><h2>{current ? '他の資料を残しながら、必要な内容を更新' : '確認済み資料を選び、初めての公開を準備'}</h2></div><button className="button secondary" disabled={!!busy || !boundaryReady} onClick={() => create()}>{createLabel}</button></div>
      <p className="small-note">{current ? '草案の保存・プレビューでは接客内容は変わりません。追加・差し替え・除外を明示し、最後に差分を確認して公開します。' : '草案を作成してから、業務確認済みで「顧客への案内に使用可」の資料を一つずつ追加してください。差分と注意事項を確認して、初めての公開を行います。草案の保存・プレビューだけでは公開されません。'}</p>
      {pendingDrafts.length > 0 && <label className="admin-field">保存済みの公開草案<select aria-label="保存済みの公開草案" value={draft?.id || ''} disabled={!!busy} onChange={event => event.target.value && load(event.target.value)}><option value="">草案を選択</option>{pendingDrafts.map(value => <option value={value.id} key={value.id}>{value.restore_version ? `v${value.restore_version} からの復元` : value.base_version ? `v${value.base_version} を基に更新` : '初回公開'} · {fmtDate(value.saved_at || value.updated_at || value.created_at)} · {value.note || '変更説明なし'}</option>)}</select></label>}
      {!draft ? <div className="empty-state compact"><Icon name="file" size={30}/><p>「{createLabel}」を押してください。<br/>既に保存した草案がある場合は上の一覧から再開できます。</p></div> : <>
        <div className="admin-draft-status"><strong>基準：{draft.base_version ? `公開版 v${draft.base_version}` : '初回公開'}{draft.restore_version ? ` / 復元元 v${draft.restore_version}` : ''}</strong><span>{dirty ? '未保存の変更あり' : `草案 第${draft.revision}版 · 保存済み`}</span></div>
        {current?.version !== (draft.base_version || undefined) && <Alert tone="info" message="現在の公開版がこの草案の基準版から更新されています。古い草案では公開できません。現在の公開版から新しい草案を作成し、変更を確認してください。"/>}
        <div className="publication-items">{items.map((item, index) => { const value = identify(item); return <article className="publication-item" key={`${index}-${keyOf(item)}`}><div><strong>{value.filename || '資料'}</strong><span>改訂 {shortRevision(value.revision_id)} · 確認 #{item.confirmation_id} · {usageNames[value.usage || 'customer']}</span>{item.replaces_document_id && <small>差し替え元：{documents.find(document => document.id === item.replaces_document_id)?.filename || '旧資料'} / 確認 #{item.replaces_confirmation_id}</small>}</div><label className="admin-field">この資料の次版<select aria-label={`${value.filename || '資料'} の公開改訂`} value={keyOf(item)} disabled={!!busy} onChange={event => changeItem(index, event.target.value)}>{!options.some(option => keyOf(option as PublicationItem) === keyOf(item)) && <option value={keyOf(item)}>{label(value)}</option>}{options.filter(option => option.document_id === item.document_id || !items.some(selected => selected.document_id === option.document_id)).map(option => <option value={keyOf(option as PublicationItem)} key={keyOf(option as PublicationItem)}>{label(option)}</option>)}</select></label><button className="button subtle delete-button" disabled={!!busy} aria-label={`${value.filename || '資料'} を次版から除外`} onClick={() => { setItems(values => values.filter((_, position) => position !== index)); markDirty() }}>次版から除外</button></article> })}</div>
        {!items.length && <p className="admin-empty-message">現在の草案に資料はありません。必要な確認済み資料を追加してください。</p>}
        <div className="publication-add"><label className="admin-field">確認済み資料を追加<select aria-label="公開草案に追加する資料" value={addition} disabled={!!busy} onChange={event => setAddition(event.target.value)}><option value="">資料・改訂を選択</option>{options.filter(option => !items.some(selected => selected.document_id === option.document_id)).map(option => <option value={keyOf(option as PublicationItem)} key={keyOf(option as PublicationItem)}>{label(option)}</option>)}</select></label><button className="button secondary" disabled={!!busy || !addition} onClick={() => { const option = options.find(value => keyOf(value as PublicationItem) === addition); if (option) { setItems(values => [...values, { document_id: option.document_id, confirmation_id: option.confirmation_id }]); setAddition(''); markDirty() } }}>資料を追加</button></div>
        <label className="admin-field">変更の説明<textarea aria-label="公開変更の説明" value={note} rows={3} disabled={!!busy} onChange={event => { setNote(event.target.value); setFieldErrors({}); markDirty() }}/>{fieldErrors.note && <span className="field-error" role="alert">{fieldErrors.note}</span>}<small className="field-hint">何を更新・除外するのか記録します。共有管理者による操作として履歴に残ります。</small></label>
        <div className="publication-actions"><button className="button secondary" onClick={save} disabled={!!busy || !boundaryReady}>{busy === 'save' ? '草案を保存しています…' : '公開草案を保存'}</button><button className="button primary" onClick={inspect} disabled={!!busy || dirty || !boundaryReady}>{busy === 'preview' ? '変更と有効性を確認しています…' : '公開前の差分を確認'}<Icon name="arrow" size={17}/></button>{dirty && <span className="small-note">変更を保存してから差分を確認してください。</span>}</div>
      </>}
    </section>}
    {pane === 'edit' && preview && <section className="card publication-preview" aria-label="公開差分プレビュー"><span className="eyebrow">公開前の最終確認</span><h2>{preview.base_version ? `v${preview.base_version} からの変更` : '初回公開の内容'}</h2><div className="publication-diff-groups">{[['added','追加'],['replaced','差し替え'],['retained','維持'],['removed','除外']].map(([name,title]) => <div className={`publication-diff-group ${name}`} key={name}><h3>{title} <small>{preview[name]?.length || 0}件</small></h3>{preview[name]?.length ? preview[name].map((value: Json,index: number) => <p key={index}>{name === 'replaced' ? <>{label(value.before)}<span className="diff-arrow">↓</span>{label(value.after)}</> : label(value)}</p>) : <p className="small-note">なし</p>}</div>)}</div>
      <h3>主な業務内容の変更</h3>{preview.changes?.length ? <div className="publication-change-table"><table><thead><tr><th>項目</th><th>変更前</th><th>変更後</th></tr></thead><tbody>{preview.changes.map((change: Json,index: number) => <tr key={index}><th>{change.label}</th><td>{visibleValue(change.before, change.label)}</td><td>{visibleValue(change.after, change.label)}</td></tr>)}</tbody></table></div> : <p className="small-note">主要な業務項目の変更はありません。</p>}
      <h3>接客で使える内容・注意事項</h3><div className="publication-notices">{(preview.warnings || []).map((warning: Json,index: number) => <Alert key={index} tone="info" message={warning.message}/>)}{(preview.blockers || []).map((blocker: Json,index: number) => <Alert key={index} message={blocker.message}/>)}{!preview.warnings?.length && !preview.blockers?.length && <p className="small-note">公開を妨げる確認事項はありません。</p>}</div>
      <p className="small-note">最終公開時にも、基準版・改訂・用途・日付をサーバーで再確認します。変更があった場合は、新しい差分の確認が必要です。</p><label className="check-field"><input type="checkbox" aria-label="公開差分と注意事項を確認しました" checked={checked} disabled={!!busy || !!preview.blockers?.length} onChange={event => setChecked(event.target.checked)}/><span>追加・差し替え・維持・除外と、業務への影響を確認しました。</span></label><button className="button primary" disabled={!boundaryReady || !!busy || !checked || !!preview.blockers?.length || dirty} onClick={publish}>{busy === 'publish' ? '公開しています…' : 'この内容で新しい版を公開'}<Icon name="check" size={17}/></button>
    </section>}
    {pane === 'published' && <section className="card published-admin">{current ? <><div className="section-heading"><div><span className="eyebrow">PUBLISHED / v{current.version}</span><h2>{current.property?.property_name || '住宅購入の共通・会社資料'}</h2></div><span className="badge published">公開中</span></div><p className="small-note">変更は公開草案で準備します。現在の公開版・過去の確認内容を上書きしません。</p><dl className="property-facts"><div><dt>販売価格</dt><dd>{fmtMoney(current.property?.price)}</dd></div><div><dt>間取り</dt><dd>{current.property?.layout || '記載なし'}</dd></div><div><dt>公開日時</dt><dd>{fmtDate(current.published_at)}</dd></div></dl><h3>FAQ</h3>{(current.faq || []).map((item: Json,index: number) => <details key={index}><summary>{item.question}</summary><p>{item.answer}</p><SourceList references={item.reference ? [item.reference] : []}/></details>)}<h3>住宅ローン参考金利</h3><div className="rate-grid">{(current.rates || []).map((rate: Json,index: number) => <div className="rate-card" key={rate.id || index}><span>{rate.bank}</span><h4>{rate.product}</h4><strong>年 {rate.rate}%</strong><p>{rate.rate_type}</p><p>基準日 {rate.effective_date} / 期限 {rate.valid_until || '記載なし'}</p><p>{rate.notes}</p>{rate.conditions?.length > 0 && <ul>{rate.conditions.map((condition: string,position: number) => <li key={position}>{visibleValue(condition)}</li>)}</ul>}<SourceList references={rate.reference ? [rate.reference] : []}/></div>)}</div><SourceList references={current.references || []}/></> : <div className="empty-state"><Icon name="home" size={33}/><h2>資料はまだ公開されていません</h2><p>確認済み資料を公開草案へ追加し、差分を確認して公開してください。</p></div>}</section>}
    {pane === 'versions' && <section className="card publication-history" aria-label="公開バージョン履歴"><h2>公開バージョン履歴</h2><p className="small-note">復元は過去版を消さず、現在の用途・期限を再確認して新しい公開版を作成します。取り消された用途や期限を自動で復活させません。</p>{versions.length ? versions.map(version => <details className="version-row" key={version.version}><summary><span>v{version.version} · {version.property?.property_name || '共通・会社資料'}</span><small>{fmtDate(version.published_at)}</small></summary><dl className="metadata"><div><dt>操作した管理者</dt><dd>{version.published_by === 'admin' || version.actor === 'admin' ? 'admin（共有管理アカウント）' : version.published_by || version.actor || '未記録（旧版）'}</dd></div><div><dt>変更の説明</dt><dd>{version.change_note || version.note || '旧版：変更説明の記録なし'}</dd></div></dl><h3>含まれる資料と確認改訂</h3><ul className="publication-history-items">{historyItems(version).map((item: Json,index: number) => <li key={index}>{item.filename || documents.find(document => document.id === item.document_id)?.filename || '資料'} · 改訂 {shortRevision(item.revision_id)} · 確認 #{item.confirmation_id}</li>)}</ul><button className="button secondary" disabled={!!busy || !boundaryReady} onClick={() => create(version.version)}>v{version.version} の内容から復元草案を作成</button><details className="admin-diagnostics"><summary>公開版の診断データ</summary><pre className="json-view">{pretty(version)}</pre></details></details>) : <p className="admin-empty-message">公開版はまだありません。</p>}</section>}
  </div>
}
