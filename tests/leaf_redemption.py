import unittest,uuid,base64
from integration import SystemTests,PASSWORD

LEAF='gift66e7d1f75cda4ddd93ef092ecfa59178'
class LeafTests(SystemTests):
 def test_leaf_workflow(self):
  admin=self.client();alice=self.client();bob=self.client();anon=self.client()
  self.call(admin,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  cfg=self.call(admin,'/api/config?admin=1')[1];c=cfg['draft'];c['categories'].append({'id':LEAF,'enabled':True,'icon':'♧','cover':'','order':5});c['fields'][LEAF]=[]
  self.assertEqual(self.call(admin,'/api/config','POST',{'config':c,'revision':cfg['revision'],'action':'publish'})[0],200)
  donors=[]
  for who,client in [('alice',alice),('bob',bob)]:
   d=self.call(admin,'/api/donors','POST',{'prefix':'Ms','englishName':who,'chineseName':'','phone':'','email':who+'@example.com'})[1]['donor'];donors.append(d)
   self.call(admin,'/api/donors/points','POST',{'donorId':d['id'],'entryId':str(uuid.uuid4()),'amount':10000})
   credentials=self.call(admin,'/api/accounts','POST',{'donorId':d['id']})[1];self.call(client,'/api/auth/login','POST',credentials)
  def profile():return self.call(alice,'/api/profile')[1]['donor']
  def request(**changes):
   fields={'leafMode':'en','leafName':'A'*38,'leafQuantity':'1','leafLayout':'multiple'};fields.update(changes)
   return {'requestId':str(uuid.uuid4()),'category':LEAF,'fields':fields}
  def submit(payload):return self.call(alice,'/api/requests','POST',payload)
  for fields in [dict(leafName='A'*39),dict(leafName=''),dict(leafMode='zh',leafName='中'*15),dict(leafMode='en',leafName='中文'),dict(leafMode='zh',leafName='English'),dict(leafName='A\nB'),dict(leafName='😀'),dict(leafQuantity='1.5'),dict(leafMode='logo'),dict(leafLayout='invalid')]:
   self.assertEqual(submit(request(**fields))[0],400,fields)
  self.assertEqual(profile()['entitlements'][LEAF]['remaining'],10)
  payload=request(leafMode='zh',leafName='中'*14,leafQuantity='2',leafLayout='larger');code,r=submit(payload);self.assertEqual(code,201)
  self.assertEqual(profile()['entitlements'][LEAF]['remaining'],8)
  self.assertEqual(submit(payload)[0],200)
  self.assertEqual(self.call(bob,'/api/requests','PATCH',{'id':r['id'],'status':'cancelled'})[0],403)
  self.assertEqual(self.call(alice,'/api/requests','PATCH',{'id':r['id'],'status':'approved'})[0],403)
  self.assertEqual(self.call(alice,'/api/requests','PATCH',{'id':r['id'],'status':'cancelled'})[0],200)
  self.assertEqual(profile()['entitlements'][LEAF]['remaining'],10)
  self.assertEqual(self.call(alice,'/api/requests','PATCH',{'id':r['id'],'status':'cancelled'})[0],200)
  self.assertEqual(self.call(admin,'/api/requests','PATCH',{'id':r['id'],'status':'approved'})[0],409)
  code,r=submit(request());self.assertEqual(code,201)
  self.assertEqual(self.call(admin,'/api/requests','PATCH',{'id':r['id'],'status':'approved'})[0],200)
  self.assertEqual(self.call(alice,'/api/requests','PATCH',{'id':r['id'],'status':'cancelled'})[0],409)
  self.assertEqual(self.call(admin,'/api/requests','PATCH',{'id':r['id'],'status':'complete'})[0],200)
  self.assertEqual(profile()['entitlements'][LEAF]['remaining'],9)
  r=submit(request())[1];self.assertEqual(self.call(admin,'/api/requests','PATCH',{'id':r['id'],'status':'rejected'})[0],200)
  self.assertEqual(profile()['entitlements'][LEAF]['remaining'],9)
  # Logo access is private to its donor and administrators.
  png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1kAAAAASUVORK5CYII=')
  code,logo=self.upload(alice,'/api/leaf-logo',{},png);self.assertEqual(code,201)
  self.assertEqual(self.upload(anon,'/api/leaf-logo',{},png)[0],401)
  self.assertEqual(self.upload(alice,'/api/leaf-logo',{},b'not image')[0],400)
  self.assertEqual(submit(request(leafMode='logo',leafLogo=logo['key']))[0],201)
  url='/api/leaf-logo?donorId='+donors[0]['id']+'&key='+logo['key']
  self.assertEqual(self.call(alice,url)[0],200);self.assertEqual(self.call(admin,url)[0],200);self.assertEqual(self.call(bob,url)[0],403)
  stolen=request(leafMode='logo',leafLogo=logo['key']);self.assertEqual(self.call(bob,'/api/requests','POST',stolen)[0],400)
  self.assertEqual(profile()['entitlements']['tree']['remaining'],10)
  self.stop();self.start();self.assertEqual(profile()['entitlements'][LEAF]['remaining'],8)
  self.assertEqual({r['status'] for r in self.call(alice,'/api/requests')[1]['requests']},{'pending','complete','rejected','cancelled'})

if __name__=='__main__':unittest.main(defaultTest='LeafTests.test_leaf_workflow',verbosity=2)
