// Actual normal Chrome read-only check. Never creates sessions or mutates business data.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const root=path.resolve(import.meta.dirname,'..');const env=Object.fromEntries((await fs.readFile(path.join(root,'.env'),'utf8')).split(/\r?\n/).filter(l=>/^[A-Z_][A-Z0-9_]*=/.test(l)).map(l=>{const i=l.indexOf('=');return[l.slice(0,i),l.slice(i+1).replace(/^['"]|['"]$/g,'')]}))
const base='http://localhost:5173',dir=path.join(root,'evidence/normal_demo_published_chrome');await fs.mkdir(dir,{recursive:true})
const result={started_at:new Date().toISOString(),browser:'installed Google Chrome headless',base,ai_calls:0,session_calls:0,microphone_permission_requested:false,mutations:[],page_errors:[],console_errors:[],status:'PREPARING'}
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true})
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'ja-JP'});result.health=await(await context.request.get(base+'/api/health')).json();assert.equal(result.health.demo_mode,'demo')
 const property=await context.request.get(base+'/api/property');result.public_property={http:property.status(),data:await property.json()};const published=property.ok()
 for(const target of ['customer','admin']){
  const page=await context.newPage();page.on('pageerror',e=>result.page_errors.push(e.message));page.on('console',m=>{if(m.type()==='error')result.console_errors.push(m.text())});page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method()))result.mutations.push({method:r.method(),path:new URL(r.url()).pathname})});await page.goto(base+(target==='admin'?'/admin':'/'),{waitUntil:'networkidle'})
  if(target==='admin'){
   await page.getByLabel('パスワード',{exact:true}).fill(env.ADMIN_PASSWORD);await page.getByRole('button',{name:'ログイン',exact:true}).click();await expect(page.locator('.document-row')).toHaveCount(4);if(!published)await expect(page.locator('.admin-stats')).toContainText('未公開');else await expect(page.locator('.admin-stats')).toContainText(`v${result.public_property.data.version}`)
   result.admin={stats:await page.locator('.admin-stats').innerText(),document_count:await page.locator('.document-row').count(),horizontal_overflow:await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)}
  }else{
   await expect(page.getByRole('button',{name:/接客を開始/})).toBeVisible();result.customer={text:await page.locator('body').innerText(),start_disabled:await page.getByRole('button',{name:/接客を開始/}).isDisabled(),horizontal_overflow:await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)}
  }
  await page.screenshot({path:path.join(dir,target+'.png'),fullPage:true});await page.close()
 }
 assert.deepEqual(result.mutations,[]);assert.deepEqual(result.page_errors,[]);result.status=published?'PASS_NORMAL_PUBLISHED_RENDER_READONLY':'WAITING_FOR_NORMAL_PUBLICATION_RENDER_VERIFIED';result.completed_at=new Date().toISOString()
}catch(e){result.status='FAIL';result.failure=String(e.message);throw e}finally{await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(result,null,2)+'\n');await browser.close()}
console.log(JSON.stringify({status:result.status,public_property_http:result.public_property.http,admin:result.admin,customer_start_disabled:result.customer.start_disabled,mutations:result.mutations,page_errors:result.page_errors,console_errors:result.console_errors}))
