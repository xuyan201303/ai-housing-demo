// R1: real local HTTP + Chrome, synthetic TEST provider; no AI or microphone.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
const out=path.resolve(import.meta.dirname,'../evidence/public_response_boundary_r1')
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true})
const context=await browser.newContext({viewport:{width:1440,height:1100}})
const page=await context.newPage()
const result={status:'RUNNING',provider:'TEST_DETERMINISTIC_NOT_REAL_AI',database:'evidence/public_response_boundary_r1/ui-test.db',ports:[5184,8014],paid_api_calls:0,physical_microphone:'NOT_TESTED',checks:{},responses:[],page_errors:[]}
let session
page.on('pageerror',e=>result.page_errors.push(e.message))
page.on('response',async response=>{
 if(!response.url().includes('/api/')||!response.headers()['content-type']?.includes('json'))return
 const body=await response.json().catch(()=>null);if(!body)return
 const safeCopy=structuredClone(body);delete safeCopy.token
 result.responses.push({path:new URL(response.url()).pathname,status:response.status(),body:safeCopy})
})
async function ask(text){
 await page.getByLabel('ご相談内容',{exact:true}).fill(text)
 const answer=page.waitForResponse(r=>r.url().endsWith('/messages')&&r.request().method()==='POST');answer.catch(()=>{})
 await page.getByRole('button',{name:'送信',exact:true}).click();expect((await answer).ok()).toBe(true)
}
try{
 await page.goto('http://localhost:5184/')
 await expect(page.locator('.property-panel')).toHaveCount(0)
 await expect(page.locator('.customer-shell')).not.toContainText('No.15')
 const started=page.waitForResponse(r=>r.url().endsWith('/api/sessions')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'文字で開始',exact:true}).click();session=await(await started).json()
 expect(session.property).toBeNull();expect(session.property_id).toBeNull();expect(session.snapshot).toBeUndefined()
 result.session_id=session.id;result.version=session.version;result.checks.general_home_without_property='PASS'
 await ask('住宅購入は何から始めればよいですか？')
 await expect(page.locator('.consultation-materials')).toContainText('共通住宅購入資料')
 expect(await page.locator('.consultation-materials a[href*="mlit.go.jp"]').count()).toBeGreaterThan(0)
 result.checks.general_hits_safe_sources='PASS'
 await ask('紹介できる物件はありますか？')
 await expect(page.getByRole('button',{name:'この物件について相談',exact:true})).toBeVisible()
 await expect(page.locator('.property-panel')).toHaveCount(0)
 result.checks.candidates_without_details='PASS'
 await page.getByRole('button',{name:'この物件について相談',exact:true}).click()
 await expect(page.locator('.property-panel')).toContainText('76,900,000 円')
 await expect(page.locator('.property-panel')).toContainText('分譲全体')
 await page.getByRole('tab',{name:'設備・周辺',exact:true}).click();await expect(page.locator('.property-panel')).toContainText('TEST設備')
 await page.getByRole('button',{name:'資料を閉じる',exact:true}).click()
 await expect(page.locator('.consultation-materials')).toHaveCount(0);await page.waitForTimeout(2300);await expect(page.locator('.consultation-materials')).toHaveCount(0)
 result.checks.property_selection_details_close='PASS'
 await ask('No.15の設備を教えてください。')
 await expect(page.locator('.property-panel')).toBeVisible()
 result.checks.automatic_material_reopen_for_new_query='PASS'
 await ask('住宅ローンについて相談したい')
 await expect(page.locator('.mortgage-panel')).toBeVisible()
 await page.getByLabel('頭金（円）').fill('5000000')
 await page.getByLabel('返済期間（年）').fill('35')
 await page.getByLabel('参考金利・商品').selectOption('TEST-mufg')
 await expect(page.locator('.mortgage-panel')).toContainText('TEST審査・利用条件')
 await expect(page.locator('.mortgage-panel')).toContainText('返済期間 1–35 年')
 await page.getByRole('button',{name:'月額概算を計算',exact:true}).click()
 await expect(page.locator('.mortgage-result')).toContainText('209,563 円')
 result.checks.backend_loan_product_conditions_card='PASS'
 await page.screenshot({path:path.join(out,'customer-loan.png'),fullPage:true})
 await page.getByRole('button',{name:'スタッフを呼ぶ',exact:true}).click()
 await page.getByRole('button',{name:'スタッフへの呼出を送信',exact:true}).click()
 await expect(page.locator('.staff-status')).toContainText('確認をお待ちください')
 const staff=await context.newPage();await staff.goto('http://localhost:5184/staff')
 await staff.getByLabel('パスワード').fill('TEST-r1-staff');await staff.getByRole('button',{name:'ログイン',exact:true}).click()
 const card=staff.locator('article.staff-call').filter({hasText:session.id})
 await card.getByRole('button',{name:'受付',exact:true}).click()
 await expect(page.locator('.staff-status')).toContainText('スタッフが確認しました')
 await card.getByRole('button',{name:'対応完了',exact:true}).click()
 await expect(page.locator('.staff-status')).toContainText('対応が完了しました')
 result.checks.staff_pending_accepted_completed='PASS'
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
 await page.getByRole('button',{name:'接客終了',exact:true}).click()
 await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
 const final=await(await context.request.get(`http://localhost:5184/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}})).json()
 expect(final.status).toBe('ended');expect(final.token).toBeUndefined();result.checks.end='PASS'
 // Unknown markers deliberately exist in internal service/DB records.
 const serialized=JSON.stringify(result.responses)
 expect(serialized).not.toContain('TEST_INTERNAL_R1_DO_NOT_RETURN')
 for(const field of ['"snapshot"','"tool_events"','"tool_results"','"arguments"','"filename"','"location"','"internal_note"'])expect(serialized).not.toContain(field)
 expect(result.page_errors).toEqual([])
 result.checks.browser_actual_response_allowlist='PASS';result.status='PASS'
}catch(error){result.status='FAIL';result.error=error.message;await page.screenshot({path:path.join(out,'customer-failure.png'),fullPage:true}).catch(()=>{})}
finally{
 if(session)await context.request.post(`http://localhost:5184/api/sessions/${session.id}/end`,{headers:{'X-Session-Token':session.token}}).catch(()=>{})
 await fs.writeFile(path.join(out,'chrome_result.json'),JSON.stringify(result,null,2));await browser.close()
}
console.log(JSON.stringify({status:result.status,checks:result.checks,error:result.error}))
if(result.status!=='PASS')process.exitCode=1
