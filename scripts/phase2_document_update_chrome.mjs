// Evidence gallery only. Real Chrome interactions use cua_repl/native AX.
// This script does not automate a browser, read a business database, or call AI.
import fs from 'node:fs/promises'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..')
const out = path.join(root, 'evidence/phase2_document_update')
const observations = JSON.parse(await fs.readFile(path.join(out, 'ui_observations.json'), 'utf8'))
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]))
const screens = observations.screenshots || []
for (const screen of screens) {
  if (!/^[a-zA-Z0-9_-]+\.png$/.test(screen.file)) throw new Error('Unsafe screenshot filename')
  await fs.access(path.join(out, screen.file))
}
await fs.writeFile(path.join(out, 'index.html'), `<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phase 2 第2輪 / Chrome 検証画面</title><style>body{margin:0;background:#f2f5f2;color:#183f35;font-family:-apple-system,BlinkMacSystemFont,sans-serif}main{max-width:1200px;margin:auto;padding:28px}h1{font-size:27px}p{line-height:1.7}article{margin:25px 0;padding:18px;background:white;border:1px solid #dce4db;border-radius:12px}img{max-width:100%;height:auto;border:1px solid #dce4db}small{color:#5c6d61}a{color:#225d49}</style><main><h1>資料更新・公開 / 実際の Chrome 操作</h1><p>隔離 Admin: <a href="http://localhost:5176/admin">http://localhost:5176/admin</a><br>実際の Google Chrome を CUA で操作。SDK は正式配布物を使用。AI 文言は TEST provider で、実 AI・音声・マイクの受け入れではありません。</p><p>画面の人工修正は TEST 専用です。通常 DB、実資料の公開、音声設定は変更していません。</p>${screens.map(screen => `<article><h2>${escape(screen.title)}</h2><p>${escape(screen.observation || '')}</p><a href="${screen.file}"><img src="${screen.file}" alt="${escape(screen.title)}" loading="lazy"></a><p><small>${escape(screen.recorded_at || '')} / ${escape(screen.file)}</small></p></article>`).join('')}</main></html>`, 'utf8')
console.log(JSON.stringify({ gallery: 'evidence/phase2_document_update/index.html', screenshots: screens.length, ui_technology: 'cua_repl native AX', browser_automation_by_this_script: false }))
