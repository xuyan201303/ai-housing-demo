import { useEffect, useRef, useState } from 'react'
import { Alert, Icon } from './App'
import SourceList from './CustomerSources'
import { api, errorText, fmtMoney, post } from './api'
import type { CustomerMortgage, CustomerProduct, CustomerSessionWithToken } from './customerTypes'
export function MortgageResult({result}:{result:CustomerMortgage}) {
  return <div className="mortgage-result"><span className="eyebrow">MONTHLY PAYMENT / ESTIMATE</span><span className="mortgage-month-label">月々の返済額（概算）</span><strong>{fmtMoney(result.monthly_payment)}</strong><dl><div><dt>借入額</dt><dd>{fmtMoney(result.loan_amount)}</dd></div>{result.down_payment!=null&&<div><dt>頭金</dt><dd>{fmtMoney(result.down_payment)}</dd></div>}<div><dt>参考金利</dt><dd>年 {result.annual_interest_rate}%</dd></div><div><dt>返済期間</dt><dd>{result.years} 年</dd></div><div><dt>商品</dt><dd>{result.bank} / {result.product}</dd></div><div><dt>計算日</dt><dd>{result.calculation_date}</dd></div><div><dt>金利基準日</dt><dd>{result.effective_date} / 有効期限 {result.valid_until}</dd></div></dl>{result.rate_basis&&<p className="small-note">{result.rate_basis}</p>}{result.conditions?.length ? <p className="small-note">{result.conditions.join(" / ")}</p>:null}{result.price_basis&&<p className="small-note">{result.price_basis}</p>}<p className="mortgage-disclaimer">本結果は概算です。実際の適用金利・融資条件等は金融機関により異なります。諸費用・税金・保険料・金利変動等は含みません。</p>{result.notes&&<p className="small-note">{Array.isArray(result.notes)?result.notes.join(' '):result.notes}</p>}<SourceList references={result.references || []}/></div>
}
export default function Mortgage({session,onResult,externalResult,externalResultEventId}:{session:CustomerSessionWithToken,onResult:(result:CustomerMortgage)=>void,externalResult?:CustomerMortgage,externalResultEventId?:number}) {
  const [loanAmount,setLoanAmount]=useState('')
  const [propertyPrice,setPropertyPrice]=useState('')
  const [downPayment,setDownPayment]=useState('5000000')
  const [years,setYears]=useState('35')
  const [rateId,setRateId]=useState('')
  const [result,setResult]=useState<CustomerMortgage|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const appliedExternalEvent=useRef<number|undefined>(undefined)
  const rates:CustomerProduct[]=session.products || []
  useEffect(()=>{
    if(!externalResult && appliedExternalEvent.current!==undefined){appliedExternalEvent.current=undefined;setResult(null)}
  },[externalResult,externalResultEventId])
  useEffect(()=>{
    // Polling can withdraw expired products/property. Do not keep a cached
    // calculation card presented as a currently usable result.
    if(result && (!rates.some(rate=>rate.id===result.rate_id) || (!result.price_basis && !session.property))){setResult(null);setRateId('')}
  },[session.products,session.property,result])
  useEffect(()=>{
    if(!externalResult || appliedExternalEvent.current===externalResultEventId)return
    appliedExternalEvent.current=externalResultEventId
    setResult(externalResult)
    setRateId(externalResult.rate_id)
    if(externalResult.down_payment!=null)setDownPayment(String(externalResult.down_payment))
    setLoanAmount(String(externalResult.loan_amount))
    setYears(String(externalResult.years))
  },[externalResult,externalResultEventId])
  async function calculate(event:React.FormEvent){event.preventDefault();setBusy(true);setError('');setResult(null);try{const calculated=await api<CustomerMortgage>(`/sessions/${session.id}/mortgage`,post(session.property_id?{down_payment:Number(downPayment),years:Number(years),rate_id:rateId}:{loan_amount:Number(loanAmount),property_price:propertyPrice?Number(propertyPrice):null,years:Number(years),rate_id:rateId}),session.token);setResult(calculated);onResult(calculated)}catch(error){setError(errorText(error))}finally{setBusy(false)}}
  return <section className="mortgage-panel"><div className="section-heading"><div><span className="eyebrow">PLAN YOUR LIFE</span><h2>住宅ローンの月額を知る</h2></div><Icon name="money" size={25}/></div><p className="small-note">公開版 v{session.version} の登録参考金利を使い、サーバーで概算を計算します。物件未選択時は入力いただいた借入額・取得価格だけを使用します。</p>{rates.length?<form className="mortgage-form" onSubmit={calculate}><div className="mortgage-input-row">{!session.property_id&&<><label>借入額（円）<input type="number" value={loanAmount} onChange={e=>setLoanAmount(e.target.value)} required min="1"/></label><label>取得価格（円・融資率商品の場合）<input type="number" value={propertyPrice} onChange={e=>setPropertyPrice(e.target.value)} min="1"/></label></>}{session.property_id&&<label>頭金（円）<input type="number" value={downPayment} onChange={event=>setDownPayment(event.target.value)} min="0" step="10000" required/></label>}<label>返済期間（年）<input type="number" value={years} onChange={event=>setYears(event.target.value)} min="1" max="50" required/></label></div><label>参考金利・商品<select required value={rateId} onChange={event=>setRateId(event.target.value)}><option value="">商品を選択してください</option>{rates.map(rate=><option key={rate.id} value={rate.id}>{rate.bank} / {rate.product} / 年 {rate.rate}%{rate.rate_over_90_percent!=null?`（9割以下）/ ${rate.rate_over_90_percent}%（9割超）`:''}</option>)}</select></label>{(()=>{const rate=rates.find(rate=>rate.id===rateId);return rate?<p className="small-note">基準日 {rate.effective_date} / 有効期限 {rate.valid_until}<br/>{rate.notes}<br/>返済期間 {rate.years_min}–{rate.years_max} 年 / 借入額 {fmtMoney(rate.loan_amount_min)}–{fmtMoney(rate.loan_amount_max)}<br/>{rate.requires_acquisition_price_for_estimate?"融資率確認のため取得価格が必要です。":"取得価格は試算入力に不要です。"}<SourceList references={rate.references}/></p>:null})()}<button className="button secondary wide" disabled={busy}>{busy?'計算しています…':'月額概算を計算'}<Icon name="arrow" size={17}/></button></form>:<p className="small-note">公開済みの参考金利がありません。金利資料の確認・公開が必要です。</p>}<Alert message={error}/>{result&&<MortgageResult result={result}/>}<p className="small-note mortgage-footnote">融資の可否や実際の条件については、担当スタッフ・金融機関へご相談ください。</p></section>
}
