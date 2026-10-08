// Actual installed Chrome UI; no mocked app APIs or responses.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'evidence/consultation_positioning')
const env=Object.fromEntries((await fs.readFile(path.join(root,'.env'),'utf8')).split(/\r?\n/).filter(l=>/^[A-Z_]+=/.test(l)).map(l=>{const i=l.indexOf('=');return [l.slice(0,i),l.slice(i+1).replace(/^['"]|['"]$/g,'')]}))
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true})
const context=await browser.newContext({viewport:{width:1440,height:1100}})
const result={browser:'installed Google Chrome headless',api_mocks:0,physical_microphone:'NOT_VERIFIED',checks:{},page_errors:[]}
try{
 const page=await context.newPage();page.on('pageerror',e=>result.page_errors.push(e.message))
 await page.goto('http://localhost:5173/');await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeEnabled()
 expect(await page.locator('body').innerText()).not.toMatch(/No\.15|7,690|八千代|76,900/)
 await expect(page.locator('.consultation-materials')).toHaveCount(0)
 await page.screenshot({path:path.join(out,'normal-centered-home.png'),fullPage:true})
 const response=page.waitForResponse(r=>r.url().endsWith('/api/sessions')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'文字で開始',exact:true}).click();const session=await(await response).json()
 expect(session.property_id).toBeNull();expect(session.version).toBeNull()
 await expect(page.locator('.session-caption')).toContainText('資料未公開')
 result.checks.normal_general_start_without_publication='PASS';result.normal_session_id=session.id
 await page.getByRole('button',{name:'接客終了',exact:true}).click();await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
 await page.goto('http://localhost:5173/admin');await page.getByLabel('パスワード',{exact:true}).fill(env.ADMIN_PASSWORD);await page.getByRole('button',{name:'ログイン',exact:true}).click()
 await expect(page.locator('.document-row')).toHaveCount(6)
 await page.locator('.document-row button').filter({hasText:'住宅購入基礎FAQ_demo.pdf'}).click()
 await expect(page.getByLabel('知識範囲',{exact:true})).toHaveValue('general')
 await expect(page.locator('#review-json')).toHaveValue(/mlit\.go\.jp/)
 expect(await page.getByRole('button',{name:'管理者確認を保存',exact:true}).isDisabled()).toBe(true)
 result.checks.normal_six_parsed_no_confirmation='PASS';await page.screenshot({path:path.join(out,'normal-faq-review.png'),fullPage:true})
 await page.locator('.document-row button').filter({hasText:'住宅ローン_demo.xlsx'}).click()
 await expect(page.getByLabel('知識範囲',{exact:true})).toHaveValue('general')
 await expect(page.locator('#review-json')).toHaveValue(/"source_urls"/)
 const rateDraft=JSON.parse(await page.locator('#review-json').inputValue())
 expect(rateDraft.document.source_urls.length).toBe(2);expect(rateDraft.document.effective_date).toBe('2026-10-01');expect(rateDraft.document.valid_until).toBe('2026-10-31')
 expect(rateDraft.property).toEqual({})
 expect(await page.getByRole('button',{name:'管理者確認を保存',exact:true}).isDisabled()).toBe(true)
 await fs.writeFile(path.join(out,'normal_rate_review_draft.json'),JSON.stringify(rateDraft,null,2))
 result.checks.normal_general_rate_source_draft_no_confirmation='PASS'
 await page.screenshot({path:path.join(out,'normal-rate-review-draft.png'),fullPage:true})
 // Targeted recovery of Staff UI after the text harness used wrong endpoint names.
 const evidence=JSON.parse(await fs.readFile(path.join(out,'live_text.json'),'utf8'))
 const caseData=evidence.cases.find(c=>c.name==='unselected_explicit_loan');const handoff=caseData.turns.at(-1)
 const call=handoff.staff_call
 const staff=await context.newPage();await staff.goto('http://localhost:5174/staff');await staff.getByLabel('パスワード',{exact:true}).fill(env.STAFF_PASSWORD);await staff.getByRole('button',{name:'ログイン',exact:true}).click()
 await staff.getByRole('button',{name:/すべて/}).click()
 const card=staff.locator('.staff-call').filter({hasText:caseData.session_id});await expect(card).toBeVisible();await expect(card).toContainText('住宅購入の一般相談')
 if(await card.getByRole('button',{name:'受付',exact:true}).count())await card.getByRole('button',{name:'受付',exact:true}).click()
 if(await card.getByRole('button',{name:'対応完了',exact:true}).count())await card.getByRole('button',{name:'対応完了',exact:true}).click()
 await expect(card).toContainText('対応完了')
 result.checks.general_staff_actual_ui_accept_complete='PASS';result.staff_call_id=call.id
 await staff.screenshot({path:path.join(out,'general-staff-completed.png'),fullPage:true})
 // Verify responsive default customer layout too.
 await page.setViewportSize({width:390,height:844});await page.goto('http://localhost:5173/')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
 await page.screenshot({path:path.join(out,'normal-centered-mobile.png'),fullPage:true})
 result.checks.mobile_no_horizontal_overflow='PASS';expect(result.page_errors).toEqual([]);result.status='PASS'
}catch(e){result.status='FAIL';result.error=e.message;throw e}finally{await fs.writeFile(path.join(out,'chrome_ui.json'),JSON.stringify(result,null,2));await browser.close()}
console.log(JSON.stringify(result))
