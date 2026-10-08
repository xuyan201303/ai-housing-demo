// Read-only UI preparation check. No sessions, confirmation, publication or AI calls.
import {chromium,expect} from '../frontend/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const root=path.resolve(import.meta.dirname,'..')
const env=Object.fromEntries((await fs.readFile(path.join(root,'.env'),'utf8')).split(/\r?\n/).filter(l=>/^[A-Z_][A-Z0-9_]*=/.test(l)).map(l=>{const i=l.indexOf('=');return [l.slice(0,i),l.slice(i+1).replace(/^['"]|['"]$/g,'')]}))
const base='http://localhost:5173'; const dir=path.join(root,'evidence/normal_demo_chrome'); await fs.mkdir(dir,{recursive:true})
const result={status:'PREPARING',browser:'installed Google Chrome headless',base,ai_calls:0,confirmation_calls:0,publication_calls:0,session_calls:0,page_errors:[],console_errors:[],mutations:[],started_at:new Date().toISOString()}
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true})
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'ja-JP'})
 const health=await(await context.request.get(base+'/api/health')).json();assert.equal(health.demo_mode,'demo');assert.equal(health.sdk_version,'1.8.0');result.health=health
 for(const role of ['admin','staff']){
  const page=await context.newPage();page.on('pageerror',e=>result.page_errors.push(e.message));page.on('console',m=>{if(m.type()==='error')result.console_errors.push(m.text())});page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method()))result.mutations.push({method:r.method(),path:new URL(r.url()).pathname})})
  await page.goto(base+'/'+role,{waitUntil:'networkidle'});await page.getByLabel('パスワード',{exact:true}).fill(env[role==='admin'?'ADMIN_PASSWORD':'STAFF_PASSWORD']);await page.getByRole('button',{name:'ログイン',exact:true}).click()
  if(role==='admin'){
   await expect(page.locator('.document-row')).toHaveCount(4);await expect(page.locator('.admin-stats')).toContainText('未公開');await expect(page.locator('.document-row .badge.parsed')).toHaveCount(4)
   await page.locator('.document-row button').filter({hasText:'物件概要_demo.pdf'}).click();await expect(page.locator('#review-json')).toHaveValue(/76900000/)
   assert.equal(await page.getByRole('button',{name:'管理者確認を保存',exact:true}).isDisabled(),true)
   result.admin={document_rows:4,parsed_badges:4,publication:'未公開',confirmation_button_disabled:true,horizontal_overflow:await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)}
  }else{
   await expect(page.getByRole('button',{name:'ログアウト',exact:true})).toBeVisible();result.staff={authenticated:true,horizontal_overflow:await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)}
  }
  await page.screenshot({path:path.join(dir,role+'.png'),fullPage:true});await page.close()
 }
 assert.deepEqual(result.mutations,[]);assert.deepEqual(result.page_errors,[]);assert.deepEqual(result.console_errors,[]);result.status='PASS_NORMAL_ADMIN_STAFF_READONLY_CHROME';result.completed_at=new Date().toISOString()
}catch(e){result.status='FAIL';result.failure=String(e.message);throw e}finally{await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(result,null,2)+'\n');await browser.close()}
console.log(JSON.stringify({status:result.status,health:result.health,admin:result.admin,staff:result.staff,mutations:result.mutations,page_errors:result.page_errors,console_errors:result.console_errors}))
