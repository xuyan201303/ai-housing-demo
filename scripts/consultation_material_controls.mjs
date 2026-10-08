// Zero AI calls: actual Backend calculator events and Customer controls at narrow sizes.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
const out=path.resolve(import.meta.dirname,'../evidence/consultation_positioning')
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true})
const context=await browser.newContext(),result={ai_calls:0,api_mocks:0,mode:'REAL_HTTP_CALCULATOR_AND_CHROME_UI',sizes:[]}
try{
 for(const width of [1000,390]){
  const page=await context.newPage();await page.setViewportSize({width,height:900});await page.goto('http://localhost:5174/')
  expect((await(await context.request.get('http://localhost:5174/api/health')).json()).demo_mode).toBe('test')
  const started=page.waitForResponse(r=>r.url().endsWith('/api/sessions')&&r.request().method()==='POST')
  await page.getByRole('button',{name:'文字で開始',exact:true}).click();const session=await(await started).json()
  try{
   const rate=session.snapshot.rates.find(r=>/三菱/.test(r.bank))
   const response=await context.request.post(`http://localhost:5174/api/sessions/${session.id}/mortgage`,{headers:{'X-Session-Token':session.token},data:{loan_amount:30000000,years:35,rate_id:rate.id}})
   expect(response.ok()).toBe(true)
   await expect(page.locator('.consultation-materials .mortgage-result')).toContainText('87,439 円')
   expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
   const ended=page.waitForResponse(r=>r.url().endsWith(`/sessions/${session.id}/end`));ended.catch(()=>{})
   await page.getByRole('button',{name:'接客終了',exact:true}).click();expect((await ended).status()).toBe(200)
   await expect(page.getByRole('button',{name:'文字で開始',exact:true})).toBeVisible()
   result.sizes.push({width,material_card:'PASS',end_control_reachable:'PASS',overflow:false})
  }finally{
   const state=await(await context.request.get(`http://localhost:5174/api/sessions/${session.id}`,{headers:{'X-Session-Token':session.token}})).json()
   if(state.status==='active')await context.request.post(`http://localhost:5174/api/sessions/${session.id}/end`,{headers:{'X-Session-Token':session.token}})
   await page.close()
  }
 }
 result.status='PASS'
}catch(e){result.status='FAIL';result.error=e.message;throw e}finally{await fs.writeFile(path.join(out,'narrow_material_controls.json'),JSON.stringify(result,null,2));await browser.close()}
console.log(JSON.stringify(result))
