const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),{randomUUID}=require('node:crypto');
const html=fs.readFileSync(path.join(__dirname,'../lib/portal.html'),'utf8');
assert.ok(!/function history\s*\(/.test(html),'Do not shadow native window.history');
assert.ok(html.includes('function requestHistoryView('));
const code=html.split('<script>')[1].split('const ADMIN_MODE')[0];
async function tab(saved=[],name='',search=''){
 const data=new Map(saved),calls=[],location={origin:'https://portal.test',href:'https://portal.test/'+search,search};
 const c={name,location,URL,URLSearchParams,Headers,Request,crypto:{randomUUID},sessionStorage:{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)},history:{replaceState(a,b,p){location.href=location.origin+p;location.search=new URL(location.href).search}},fetch:async(i,o)=>{calls.push({url:i,tab:o.headers.get('X-Session-Tab'),body:o.body});return {ok:true}}};
 c.window=c;c.top=c;c.self=c;vm.createContext(c);vm.runInContext(code,c);await vm.runInContext('tabSessionReady',c);return {c,data,calls};
}
(async()=>{
 const a=await tab(),b=await tab(),key='hkicf-session-tab-v1',id=a.data.get(key);
 assert.notEqual(id,b.data.get(key));
 const copy=await tab(a.data);assert.notEqual(copy.data.get(key),id);assert.equal(copy.calls[0].url,'/api/auth/fork');assert.equal(copy.calls[0].tab,id);assert.equal(a.data.get(key),id);
 const reload=await tab(a.data,a.c.name,'?sessionTab='+id);assert.equal(reload.data.get(key),id);assert.equal(reload.calls.length,0);
 const fresh=await tab(a.data,'','?newAccount=1&sessionTab='+id);assert.notEqual(fresh.data.get(key),id);assert.equal(fresh.calls.length,0);assert.ok(!fresh.c.location.search.includes('newAccount'));assert.equal(a.data.get(key),id);
 await a.c.fetch('/api/profile');assert.equal(a.calls[0].tab,id);
 console.log('Fresh tabs, duplicated tabs, reloads and another-account isolation passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
