import unittest,uuid,concurrent.futures,json,hashlib,secrets
from integration import SystemTests,PASSWORD

class ConcertTests(SystemTests):
 def test_independent_concerts(self):
  a=self.client();u=self.client();v=self.client();guest=self.client()
  self.assertEqual(self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})[0],200)
  def donor(email,total,client):
   d=self.call(a,'/api/donors','POST',{'englishName':'Concert Test','email':email})[1]['donor']
   if total:self.assertEqual(self.call(a,'/api/donors/donations','POST',{'donorId':d['id'],'total':total,'donationDate':'2026-11-22','requestId':str(uuid.uuid4()),'revision':d['revision']})[0],200)
   self.assertEqual(self.call(client,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':d['id']})[1])[0],200)
   return d['id']
  # Reuse the production-compatible CSV path for donation snapshots.
  def seed(email,total,client):
   code,d=self.call(a,'/api/donors/import','POST',{'csv':'姓名,郵箱,捐款總額（HKD）\nConcert Test,'+email+','+str(total),'action':'import'});self.assertEqual(code,200,d)
   d=next(d for d in self.call(a,'/api/donors')[1]['donors'] if d['email']==email)
   self.call(client,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':d['id']})[1]);return d['id']
  uid=seed('concert-u@example.com',10000,u);vid=donor('concert-v@example.com',0,v)
  event={'id':str(uuid.uuid4()),'revision':0,'title':'VIP 音樂會','titleEn':'VIP Concert','description':'Details','descriptionEn':'Details','eventDate':'2026-12-20T19:30','venue':'Hong Kong','cover':'/assets/hkicf-logo.svg','published':False,'tiers':[{'min':'0','max':'4999.99','tickets':0},{'min':'5000','max':'19999.99','tickets':2},{'min':'20000','max':'','tickets':4}]}
  def save(c):return self.call(a,'/api/concerts','POST',c)
  code,r=save(event);self.assertEqual(code,200,r);event['revision']=r['event']['revision']
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'],[])
  self.assertEqual(self.call(guest,'/api/concerts')[0],401)
  self.assertEqual(self.call(u,'/api/concerts','POST',event)[0],403)
  event['published']=True;code,r=save(event);self.assertEqual(code,200,r);event['revision']=r['event']['revision']
  self.assertEqual(self.call(v,'/api/concerts')[1]['events'][0]['allowance']['earned'],0)
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'][0]['allowance']['remaining'],2)
  self.assertEqual(save({**event,'revision':1})[0],409)
  self.assertEqual(save({**event,'tiers':[{'min':'0','max':'100','tickets':1},{'min':'100','max':'','tickets':2}]})[0],400)
  before=self.call(u,'/api/profile')[1]['donor']['entitlements']
  def submit(client,kind,qty,id=None):return self.call(client,'/api/concert-responses','POST',{'id':id or str(uuid.uuid4()),'eventId':event['id'],'kind':kind,'quantity':qty,'note':''})
  self.assertEqual(submit(u,'extra',1)[0],400)
  self.assertEqual(submit(v,'redeem',1)[0],400)
  rid=str(uuid.uuid4());self.assertEqual(submit(u,'redeem',1,rid)[0],201);self.assertEqual(submit(u,'redeem',1,rid)[0],200)
  self.assertEqual(submit(v,'redeem',1,rid)[0],409)
  self.assertEqual(submit(u,'redeem',2)[0],400)
  self.assertEqual(submit(u,'extra',3)[0],201)
  self.assertEqual(self.call(u,'/api/profile')[1]['donor']['entitlements'],before)
  self.assertEqual(self.call(v,'/api/concert-responses','PATCH',{'id':rid,'status':'cancelled'})[0],403)
  self.assertEqual(self.call(u,'/api/concert-responses','PATCH',{'id':rid,'status':'approved'})[0],403)
  self.assertEqual(self.call(a,'/api/concert-responses','PATCH',{'id':rid,'status':'approved'})[0],200)
  self.assertEqual(next(r for r in self.call(u,'/api/concert-responses')[1]['responses'] if r['id']==rid)['status'],'approved')
  self.assertEqual(self.call(u,'/api/concert-responses','PATCH',{'id':rid,'status':'cancelled'})[0],400)
  code,r=submit(u,'decline',1);self.assertEqual(code,201,r);decline=r['response'];self.assertTrue(decline['created_at'].endswith('Z'))
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'][0]['allowance']['remaining'],0)
  self.assertEqual(self.call(a,'/api/concert-responses','PATCH',{'id':decline['id'],'status':'approved'})[0],400)
  self.assertEqual(submit(v,'decline',0)[0],201)
  self.assertEqual(submit(v,'decline',0)[0],409)
  self.assertEqual(len(self.call(v,'/api/concert-responses')[1]['responses']),1)
  rows=self.call(a,'/api/concert-responses')[1]['responses'];self.assertEqual(len(rows),4);self.assertTrue(all('email' in r and r['reviews'] for r in rows))
  # Donation increases earn only the delta for this concert; rejected requests release tickets.
  seed('concert-u@example.com',20000,u)
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'][0]['allowance']['remaining'],2)
  code,r=submit(u,'redeem',2);self.assertEqual(code,201,r);rid2=r['response']['id']
  self.assertEqual(self.call(a,'/api/concert-responses','PATCH',{'id':rid2,'status':'rejected'})[0],200)
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'][0]['allowance']['remaining'],2)
  # Concurrent last-seat claims cannot overdraw.
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(lambda _:submit(u,'redeem',2)[0],range(2)))
  self.assertEqual(sorted(codes),[201,400])
  event['published']=False;code,r=save(event);self.assertEqual(code,200,r);event['revision']=r['event']['revision']
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'],[]);self.assertEqual(submit(u,'redeem',1)[0],409)
  self.assertTrue(self.call(u,'/api/concert-responses')[1]['responses'])
  event['published']=True;code,r=save(event);self.assertEqual(code,200,r)
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'][0]['allowance']['remaining'],0)
  # Ordinary benefit forfeitures expose an immutable timestamp to the administrator.
  fid=str(uuid.uuid4());self.assertEqual(self.call(u,'/api/rewards/forfeit','POST',{'requestId':fid,'category':'tree','quantity':1})[0],200)
  forfeited=next(r for r in self.call(a,'/api/requests')[1]['requests'] if r['id']==fid);self.assertTrue(forfeited['forfeitedAt'].endswith('Z'))
  # Bootstrap only the requested fictional donor, and preserve it on restart.
  seed('hkicf-test-a@example.com',5000,v);password=secrets.token_urlsafe(18);salt=secrets.token_hex(16);hashed=salt+':'+hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1,dklen=64,maxmem=64*1024*1024).hex()
  self.stop();self.env['HKICF_TEST_DONOR_LOGIN_HASHES']=json.dumps([{'email':'hkicf-test-a@example.com','passwordHash':hashed},{'email':'hkicf-test-b@example.com','passwordHash':hashed,'createIfMissing':{'name':'Test Donor B','phone':'','address':'','total':'10000'}}]);self.start()
  login=self.client();self.assertEqual(self.call(login,'/api/auth/login','POST',{'email':'hkicf-test-a@example.com','password':password})[0],200)
  other=self.client();self.assertEqual(self.call(other,'/api/auth/login','POST',{'email':'hkicf-test-b@example.com','password':password})[0],200);self.assertEqual(self.call(other,'/api/profile')[1]['donor']['cumulativeDonation'],10000)
  self.assertEqual(self.call(u,'/api/concerts')[1]['events'][0]['allowance']['remaining'],0)
  self.assertTrue(next(r for r in self.call(a,'/api/requests')[1]['requests'] if r['id']==fid)['forfeitedAt'])
  self.stop();self.start();self.assertEqual(self.call(login,'/api/profile')[0],200)

if __name__=='__main__':unittest.main(defaultTest='ConcertTests.test_independent_concerts',verbosity=2)
