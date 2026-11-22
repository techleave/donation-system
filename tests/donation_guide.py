import unittest,uuid,concurrent.futures
from integration import SystemTests,PASSWORD
class GuideTests(SystemTests):
 def test_guide_allowances(self):
  a=self.client();u=self.client();self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  cfg=self.call(a,'/api/config?admin=1')[1];c=cfg['draft'];leaf='gift66e7d1f75cda4ddd93ef092ecfa59178';c['categories'].append({'id':leaf,'enabled':True,'icon':'♧','cover':'','order':5});c['fields'][leaf]=[];self.assertEqual(self.call(a,'/api/config','POST',{'config':c,'revision':cfg['revision'],'action':'publish'})[0],200)
  d=self.call(a,'/api/donors','POST',{'englishName':'Guide','email':'guide@example.com'})[1]['donor'];did=d['id'];self.call(u,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':did})[1])
  self.call(a,'/api/donors/points','POST',{'donorId':did,'entryId':str(uuid.uuid4()),'amount':10000})
  categories=['tree','airport','card','gift66e7d1f75cda4ddd93ef092ecfa59178']
  def profile():return self.call(u,'/api/profile')[1]['donor']
  def total(n):
   donor=profile();self.assertEqual(self.call(a,'/api/donors/donations','POST',{'donorId':did,'entryId':str(uuid.uuid4()),'revision':donor['revision'],'cumulativeDonation':n,'donationDate':'2026-11-22'})[0],200)
  for amount,expected in [(4999,0),(5000,1),(9999,1),(10000,2)]:
   total(amount)
   for c in categories:self.assertEqual(profile()['entitlements'][c]['remaining'],expected)
  self.assertEqual(self.call(u,'/api/requests','POST',{'requestId':str(uuid.uuid4()),'category':'card','fields':{'color':'深綠','personalised':'否','message':'','address':''}})[0],400)
  op={'requestId':str(uuid.uuid4()),'category':'airport','quantity':1}
  self.assertEqual(self.call(u,'/api/rewards/forfeit','POST',op)[0],200);self.assertEqual(self.call(u,'/api/rewards/forfeit','POST',op)[0],200)
  self.assertEqual(profile()['entitlements']['airport']['remaining'],1);self.assertEqual(profile()['entitlements']['tree']['remaining'],2)
  self.assertEqual(self.call(u,'/api/rewards/forfeit','POST',dict(op,requestId=str(uuid.uuid4()),quantity=2))[0],409)
  self.assertEqual(self.call(u,'/api/requests','PATCH',{'id':op['requestId'],'status':'cancelled'})[0],403)
  self.assertEqual(self.call(a,'/api/requests','PATCH',{'id':op['requestId'],'status':'complete'})[0],409)
  self.assertEqual(self.call(u,'/api/requests','POST',{'requestId':str(uuid.uuid4()),'category':'tree','fields':{'leaves':'1'}})[0],201)
  self.assertEqual(profile()['entitlements']['tree']['remaining'],1)
  for c in ['card','gift66e7d1f75cda4ddd93ef092ecfa59178']:
   self.assertEqual(self.call(u,'/api/rewards/forfeit','POST',{'requestId':str(uuid.uuid4()),'category':c,'quantity':2})[0],200)
  total(15000);self.assertEqual(profile()['entitlements']['card']['remaining'],1)
  op={'requestId':str(uuid.uuid4()),'category':'card','quantity':1}
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.call(u,'/api/rewards/forfeit','POST',op)[0],range(2)))
  self.assertEqual(results,[200,200]);self.assertEqual(profile()['entitlements']['card']['remaining'],0)
  self.assertEqual(self.call(self.client(),'/api/rewards/forfeit','POST',op)[0],401)
  self.stop();self.start();self.assertEqual(profile()['entitlements']['card']['remaining'],0);self.assertEqual(profile()['entitlements']['tree']['remaining'],2)
  self.assertTrue(any(r['status']=='forfeited' for r in self.call(a,'/api/requests')[1]['requests']))
if __name__=='__main__':unittest.main(defaultTest='GuideTests.test_guide_allowances',verbosity=2)
