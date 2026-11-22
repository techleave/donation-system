import unittest,uuid
from integration import SystemTests,PASSWORD
G='gifta94a1d5bd0014b7fa00ebe992bf7016c'
class DeliveryTests(SystemTests):
 def test_address_profile_sync(self):
  a=self.client();u=self.client();self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  cfg=self.call(a,'/api/config?admin=1')[1];c=cfg['draft'];c['categories'].append({'id':G,'enabled':True,'icon':'✧','cover':'','order':5});c['fields'][G]=[{'key':'shippingAddress','label':{'zh':'收件地址','en':'Shipping address'},'type':'textarea','required':True,'maxLength':1000}]
  self.assertEqual(self.call(a,'/api/config','POST',{'config':c,'revision':cfg['revision'],'action':'publish'})[0],200)
  d=self.call(a,'/api/donors','POST',{'englishName':'Shipping Test','email':'shipping@example.com'})[1]['donor'];did=d['id'];self.call(u,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':did})[1])
  self.assertEqual(self.call(a,'/api/donors/gift-allowance','POST',{'donorId':did,'revision':d['revision'],'total':2})[0],200)
  def request(address):return self.call(u,'/api/requests','POST',{'requestId':str(uuid.uuid4()),'category':G,'fields':{'shippingAddress':address}})
  self.assertEqual(request('')[0],400)
  code,data=request('Flat 1 Hong Kong');self.assertEqual(code,201);self.assertEqual(data['donor']['address'],'Flat 1 Hong Kong')
  self.assertEqual(self.call(a,'/api/donors?id='+did)[1]['donor']['address'],'Flat 1 Hong Kong')
  code,data=request('One-time address');self.assertEqual(code,201);self.assertEqual(data['donor']['address'],'Flat 1 Hong Kong');self.assertEqual(data['fields']['shippingAddress']['value'],'One-time address')
  self.stop();self.start();self.assertEqual(self.call(u,'/api/profile')[1]['donor']['address'],'Flat 1 Hong Kong')
if __name__=='__main__':unittest.main(defaultTest='DeliveryTests.test_address_profile_sync',verbosity=2)
