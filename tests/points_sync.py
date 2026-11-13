import unittest,uuid
from integration import SystemTests,PASSWORD

class PointsSyncTests(SystemTests):
 def test_points_sync(self):
  admin=self.client();donor=self.client();anon=self.client()
  self.assertEqual(self.call(admin,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})[0],200)
  code,d=self.call(admin,'/api/donors','POST',{'prefix':'Ms','englishName':'Points Sync','chineseName':'','phone':'','email':'sync@example.com'});self.assertEqual(code,201);d=d['donor']
  credentials=self.call(admin,'/api/accounts','POST',{'donorId':d['id']})[1]
  payload={'donorId':d['id'],'entryId':str(uuid.uuid4()),'amount':1000}
  self.assertEqual(self.call(anon,'/api/donors/points','POST',payload)[0],403)
  code,awarded=self.call(admin,'/api/donors/points','POST',payload);self.assertEqual(code,200)
  self.assertEqual(awarded['donor']['cumulativePoints'],1000)
  self.assertEqual(self.call(donor,'/api/auth/login','POST',credentials)[0],200)
  profile=lambda:self.call(donor,'/api/profile')[1]['donor']
  self.assertEqual(profile()['cumulativePoints'],1000)
  self.assertEqual(profile()['entitlements']['tree']['remaining'],1)
  self.call(admin,'/api/donors/points','POST',payload)
  self.assertEqual(profile()['cumulativePoints'],1000)
  self.assertEqual(self.call(donor,'/api/donors/points','POST',dict(payload,entryId=str(uuid.uuid4())))[0],403)
  req={'requestId':str(uuid.uuid4()),'category':'tree','fields':{'leaves':'1'}}
  self.assertEqual(self.call(donor,'/api/requests','POST',req)[0],201)
  self.assertEqual(profile()['entitlements']['tree']['remaining'],0)
  self.assertEqual(profile()['entitlements']['airport']['remaining'],1)
  payload.update(entryId=str(uuid.uuid4()),amount=1000)
  updated=self.call(admin,'/api/donors/points','POST',payload)[1]['donor']
  self.assertEqual(profile()['cumulativePoints'],2000)
  self.assertEqual(profile()['entitlements']['tree']['remaining'],1)
  self.assertEqual(profile()['entitlements']['ticket']['earned'],1)
  self.assertEqual(self.call(admin,'/api/donors/donations','POST',{'donorId':d['id'],'entryId':str(uuid.uuid4()),'revision':updated['revision'],'cumulativeDonation':5000,'donationDate':'2026-11-13'})[0],200)
  self.assertEqual(profile()['cumulativePoints'],3000)
  self.assertEqual(profile()['cumulativeDonation'],5000)
  self.stop();self.start()
  self.assertEqual(profile()['cumulativePoints'],3000)

if __name__=='__main__':unittest.main(defaultTest='PointsSyncTests.test_points_sync',verbosity=2)
