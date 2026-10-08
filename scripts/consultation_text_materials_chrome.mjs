// Two actual AI turns to verify automatic materials after switching topics.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
const out=path.resolve(import.meta.dirname,'../evidence/consultation_positioning')
const target=path.join(out,'text_materials_chrome.json')
if(await fs.stat(target).catch(()=>null))throw new Error('Evidence already exists; no silent replay')
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true})
const context=await browser.newContext({viewport:{width:1440,height:1100}}),page=await context.newPage()
const result={mode:'REAL_CHROME_REAL_TEXT_AI_TWO_TURNS',api_mocks:0,physical_microphone:'NOT_VERIFIED',turns:[],page_errors:[],checks:{}}
let session
page.on('pageerror',e=>result.page_errors.push(e.message))
async function ask(question){
 await page.getByLabel('ご相談内容',{exact:true}).fill(question)
 const answer=page.waitForResponse(r=>r.url().endsWith('/messages')&&r.request().method()==='POST');answer.catch(()=>{})
 await page.getByRole('button',{name:'送信',exact:true}).click()
 const response=await answer;expect(response.ok()).toBe(true);const data=await response.json();result.turns.push({question,...data})
 return data
}
try{
 await page.goto('http://localhost:5174/')
 const started=page.waitForResponse(r=>r.url().endsWith('/api/sessions')&&r.request().method()==='POST')
 await page.getByRole('button',{name:'文字で開始',exact:true}).click();session=await(await started).json();result.session_id=session.id;result.version=session.version
 expect(session.property_id).toBeNull();expect(session.snapshot.property).toEqual({})
 await ask('借入額は三千万円です。35年です。三菱UFJ銀行の変動金利でお願いします。月額の試算をお願いします。')
 await expect(page.locator('.consultation-materials .mortgage-result')).toContainText('87,439 円',{timeout:20000})
 await expect(page.locator('.consultation-materials input[type=number]').first()).toHaveValue('30000000')
 result.checks.text_real_loan_card_and_form='PASS'
 await ask('No.15の価格と設備を教えてください。')
 await expect(page.locator('.consultation-materials .property-panel')).toContainText('No.15',{timeout:20000})
 await expect(page.locator('.consultation-materials')).toContainText('食洗機')
 result.checks.property_after_loan_auto_materials='PASS'
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
 result.checks.material_drawer_does_not_overflow='PASS'
 await page.screenshot({path:path.join(out,'text-property-after-loan.png'),fullPage:true})
 await page.getByRole('button',{name:'資料を閉じる',exact:true}).click();await expect(page.locator('.consultation-materials')).toHaveCount(0)
 await page.waitForTimeout(2500);await expect(page.locator('.consultation-materials')).toHaveCount(0)
 result.checks.material_closes_and_stays_closed='PASS'
 const response=page.waitForResponse(r=>r.url().endsWith(`/sessions/${session.id}/end`));response.catch(()=>{})
 await page.getByRole('button',{name:'接客終了',exact:true}).click();expect((await response).status()).toBe(200)
 expect(result.page_errors).toEqual([]);result.status='PASS'
}catch(e){result.status='FAIL';result.error=e.message;await page.screenshot({path:path.join(out,'text-material-failure.png'),fullPage:true}).catch(()=>{})}finally{
 if(session){const state=await(await context.request.get(`http://localhost:5174/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}})).json();result.final_state={status:state.status,property_id:state.property_id,tool_events:state.tool_events};if(state.status==='active')await context.request.post(`http://localhost:5174/api/sessions/${session.id}/end`,{headers:{'X-Session-Token':session.token}})}
 await fs.writeFile(target,JSON.stringify(result,null,2));await browser.close()
}
console.log(JSON.stringify({status:result.status,checks:result.checks,error:result.error}))
if(result.status==='FAIL')process.exitCode=1
