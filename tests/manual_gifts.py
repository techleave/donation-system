import unittest,uuid
from integration import SystemTests,PASSWORD
G='gifta94a1d5bd0014b7fa00ebe992bf7016c'
class ManualGiftTests(SystemTests):
 def test_manual_allocations(self):
  a=self.client();u=self.client();self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  cfg=self.call(a,'/api/config?admin=1')[1];c=cfg['draft'];c['categories'].append({'id':G,'enabled':True,'icon':'✧','cover':'','order':5});c['fields'][G]=[]
  self.assertEqual(self.call(a,'/api/config','POST',{'config':c,'revision':cfg['revision'],'action':'publish'})[0],200)
  d=self.call(a,'/api/donors','POST',{'englishName':'Manual Gift','email':'manual@example.com'})[1]['donor'];did=d['id'];self.call(u,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':did})[1])
  profile=lambda:self.call(u,'/api/profile')[1]['donor']
  self.assertEqual(profile()['entitlements'][G]['remaining'],0)
  def allocate(n):return self.call(a,'/api/donors/gift-allowance','POST',{'donorId':did,'total':n,'revision':profile()['revision']})
  self.assertEqual(allocate(2)[0],200);self.assertEqual(profile()['entitlements'][G]['remaining'],2);self.assertEqual(profile()['cumulativeDonation'],0)
  self.assertEqual(self.call(u,'/api/requests','POST',{'requestId':str(uuid.uuid4()),'category':G,'fields':{}})[0],201)
  self.assertEqual(profile()['entitlements'][G]['remaining'],1)
  self.assertEqual(allocate(2)[0],200);self.assertEqual(profile()['entitlements'][G]['remaining'],1)
  self.assertEqual(allocate(0)[0],400)
  self.assertEqual(self.call(u,'/api/donors/gift-allowance','POST',{'donorId':did,'total':99,'revision':profile()['revision']})[0],403)
  self.assertEqual(profile()['entitlements']['tree']['remaining'],0)
  self.assertEqual(allocate(3)[0],200);self.assertEqual(profile()['entitlements'][G]['remaining'],2)
  self.stop();self.start();self.assertEqual(profile()['entitlements'][G]['remaining'],2)
if __name__=='__main__':unittest.main(defaultTest='ManualGiftTests.test_manual_allocations',verbosity=2)
