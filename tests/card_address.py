import unittest,uuid
from integration import SystemTests,PASSWORD
class AddressTests(SystemTests):
 def test_address_sync(self):
  a=self.client();u=self.client();self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  d=self.call(a,'/api/donors','POST',{'prefix':'Ms','englishName':'Address Test','chineseName':'','phone':'','email':'address@example.com'})[1]['donor'];self.assertEqual(d['address'],'')
  self.call(u,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':d['id']})[1])
  cfg=self.call(a,'/api/config?admin=1')[1];c=cfg['draft'];c['fields']['card']=[];c['items']=[x for x in c['items'] if x['category']!='card'];self.call(a,'/api/config','POST',{'config':c,'revision':cfg['revision'],'action':'publish'})
  self.call(a,'/api/donors/points','POST',{'donorId':d['id'],'entryId':str(uuid.uuid4()),'amount':3000})
  def submit(address):return self.call(u,'/api/requests','POST',{'requestId':str(uuid.uuid4()),'category':'card','fields':{'address':address}})
  self.assertEqual(submit('')[0],400);self.assertEqual(self.call(u,'/api/profile')[1]['donor']['address'],'')
  self.assertEqual(submit('Flat 1, Hong Kong')[0],201);self.assertEqual(self.call(u,'/api/profile')[1]['donor']['address'],'Flat 1, Hong Kong')
  code,res=submit('One-off delivery');self.assertEqual(code,201);self.assertEqual(res['fields']['address']['value'],'One-off delivery');self.assertEqual(res['donor']['address'],'Flat 1, Hong Kong')
  d=self.call(a,'/api/donors?id='+d['id'])[1]['donor'];d['address']='Updated profile';self.assertEqual(self.call(a,'/api/donors','PATCH',d)[0],200)
  self.assertEqual(self.call(u,'/api/profile')[1]['donor']['address'],'Updated profile')
  self.stop();self.start();self.assertEqual(self.call(u,'/api/profile')[1]['donor']['address'],'Updated profile')
if __name__=='__main__':unittest.main(defaultTest='AddressTests.test_address_sync',verbosity=2)
