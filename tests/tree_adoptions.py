import unittest,uuid
from integration import SystemTests,PASSWORD

class TreeAdoptionTests(SystemTests):
 def test_tree_links_sync(self):
  admin=self.client();alice=self.client();bob=self.client();anon=self.client()
  self.call(admin,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  for name,client in [('alice',alice),('bob',bob)]:
   d=self.call(admin,'/api/donors','POST',{'prefix':'Ms','englishName':name,'chineseName':'','phone':'','email':name+'@example.com'})[1]['donor']
   self.call(admin,'/api/donors/points','POST',{'donorId':d['id'],'entryId':str(uuid.uuid4()),'amount':5000})
   self.call(client,'/api/auth/login','POST',self.call(admin,'/api/accounts','POST',{'donorId':d['id']})[1])
  self.assertEqual(self.call(alice,'/api/tree-adoptions')[1]['adoptions'],[])
  req={'requestId':str(uuid.uuid4()),'category':'tree','fields':{'leaves':'3'}}
  self.assertEqual(self.call(alice,'/api/requests','POST',req)[0],201)
  managed=self.call(admin,'/api/requests')[1]['requests'];self.assertIn(req['requestId'],[r['id'] for r in managed])
  path='/api/tree-adoptions?requestId='+req['requestId']
  self.assertEqual(self.call(admin,path)[1]['quantity'],3)
  self.assertEqual(self.call(bob,path)[0],403);self.assertEqual(self.call(anon,path)[0],401)
  payload={'requestId':req['requestId'],'treeIndex':1,'url':'https://example.com/tree/1','label':'First tree','revision':0}
  self.assertEqual(self.call(alice,'/api/tree-adoptions','POST',payload)[0],403)
  for url in ['javascript:alert(1)','http://example.com','https://user:password@example.com/tree','not a URL']:
   self.assertEqual(self.call(admin,'/api/tree-adoptions','POST',dict(payload,url=url))[0],400)
  self.assertEqual(self.call(admin,'/api/tree-adoptions','POST',dict(payload,treeIndex=4))[0],400)
  for i in range(1,4):
   self.assertEqual(self.call(admin,'/api/tree-adoptions','POST',dict(payload,treeIndex=i,url='https://example.com/tree/'+str(i)))[0],200)
  group=self.call(alice,'/api/tree-adoptions')[1]['adoptions'][0]
  self.assertEqual(group['quantity'],3);self.assertEqual([t['treeIndex'] for t in group['trees']],[1,2,3])
  self.assertEqual(group['trees'],self.call(admin,path)[1]['trees'])
  qr='/api/tree-adoptions/qr?requestId='+req['requestId']+'&index=1'
  code,svg=self.call(alice,qr);self.assertEqual(code,200);self.assertIn(b'<svg',svg);self.assertIn(b'shape-rendering="crispEdges"',svg);self.assertNotIn(b'<script',svg)
  self.assertEqual(self.call(admin,qr)[0],200);self.assertEqual(self.call(bob,qr)[0],403);self.assertEqual(self.call(anon,qr)[0],401)
  self.assertEqual(self.call(admin,'/api/tree-adoptions','POST',payload)[0],409)
  updated=dict(payload,url='https://example.com/tree/updated',revision=1)
  self.assertEqual(self.call(admin,'/api/tree-adoptions','POST',updated)[0],200)
  self.assertEqual(self.call(alice,path)[1]['trees'][0]['url'],updated['url'])
  self.assertNotEqual(self.call(alice,qr)[1],svg)
  self.assertEqual(self.call(alice,'/api/profile')[1]['donor']['entitlements']['tree']['remaining'],2)
  self.assertEqual(self.call(bob,'/api/tree-adoptions')[1]['adoptions'],[])
  self.stop();self.start()
  self.assertEqual(self.call(alice,path)[1]['trees'][0]['revision'],2)
  self.assertEqual(len(self.call(alice,'/api/tree-adoptions')[1]['adoptions'][0]['trees']),3)

if __name__=='__main__':unittest.main(defaultTest='TreeAdoptionTests.test_tree_links_sync',verbosity=2)
