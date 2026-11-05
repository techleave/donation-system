// Exercise actual UI rendering against donor allowance payloads without a production session.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const config=JSON.parse(fs.readFileSync('lib/default-config.json','utf8'));
function load(file,lastCall){
 let js=fs.readFileSync(file,'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
 js=js.replace(new RegExp(lastCall+'\\(\\);\\s*$'),'');
 const ctx=vm.createContext({console,URLSearchParams,Date,Intl,structuredClone,localStorage:{getItem:()=>null,setItem:()=>{}},location:{search:'',origin:'http://localhost',pathname:'/'},window:{addEventListener:()=>{}},document:{querySelector:()=>null,addEventListener:()=>{}},setInterval:()=>{},setTimeout:()=>{},clearTimeout:()=>{}});
 vm.runInContext(js,ctx);return ctx;
}
const donor={id:'test',prefix:'Ms',englishName:'Test Donor',chineseName:'',phone:'1234',email:'test@example.com',revision:3,cumulativeDonation:10000,cumulativePoints:2000,entitlements:{tree:{earned:2,used:1,remaining:1},airport:{earned:2,used:1,remaining:1},card:{earned:2,used:1,remaining:1},ticket:{earned:1,used:1,remaining:0}}};
const portal=load('lib/portal.html','boot');
portal.configFixture=config;portal.donorFixture=donor;
vm.runInContext('config=configFixture;ownProfile=donorFixture;ownProfileStatus="ready";state.logged=true;applyRewardRules()',portal);
for(const lang of ['zh','en']){
 vm.runInContext(`state.lang='${lang}'`,portal);
 const home=vm.runInContext('home()',portal);
 assert.equal((home.match(/class="reward-tile"/g)||[]).length,4);
 assert(home.includes('2,000'));assert(!home.includes('HK$'));assert(!home.includes('Cumulative donation'));assert(!home.includes('累計捐款'));
 vm.runInContext('state.view="ticket"',portal);
 assert(vm.runInContext('reward()',portal).includes('class="primary" disabled'));
 vm.runInContext('state.view="airport"',portal);
 assert(!vm.runInContext('reward()',portal).includes('class="primary" disabled'));
 assert(!vm.runInContext('ownProfileView()',portal).includes('HK$'));
 assert(vm.runInContext('treeQuantity()',portal).includes('max="1"'));
}
const admin=load('lib/admin.html','load');admin.configFixture=config;admin.donorFixture=donor;
vm.runInContext('draft=configFixture;selectedDonor=donorFixture;donorRows=[donorFixture]',admin);
for(const lang of ['zh','en']){
 vm.runInContext(`lang='${lang}'`,admin);
 assert(vm.runInContext('donorList()',admin).includes('HK$10,000'));
 assert(vm.runInContext('donorProfileEditor()',admin).includes('openDonorPoints'));
 assert(vm.runInContext('donorsView()',admin).includes('Cumulative Donation'));
}
console.log('Bilingual donor cards, remaining counts, disabled ticket redemption and admin totals: passed');
