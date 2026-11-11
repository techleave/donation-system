import unittest,copy
from integration import SystemTests,PASSWORD
class CopyTests(SystemTests):
 def test_05_targeted_copy(self):
  admin=self.client();self.call(admin,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  d=self.call(admin,'/api/config?admin=1')[1];cfg=d['draft'];target='gift66e7d1f75cda4ddd93ef092ecfa59178';other='gifta94a1d5bd0014b7fa00ebe992bf7016c'
  for gid in [target,other]:
   cfg['categories'].append({'id':gid,'order':len(cfg['categories']),'enabled':True,'icon':'✧','cover':'/media/test.png','coverCrop':{'scale':1.25,'x':5,'y':-7},'content':{'title':{'zh':'新禮物','en':'New gift'},'short':{'zh':'測試','en':'Test'},'description':{'zh':'','en':''}}});cfg['fields'][gid]=[{'key':'requirements','label':{'zh':'需求','en':'Requirements'},'type':'textarea','required':True,'maxLength':2000}]
  self.assertEqual(self.call(admin,'/api/config','POST',{'config':cfg,'revision':d['revision'],'action':'publish'})[0],200)
  before=copy.deepcopy(self.call(admin,'/api/config?admin=1')[1]['published']);self.stop();self.start();after=self.call(admin,'/api/config?admin=1')[1]
  for kind in ['draft','published']:
   actual=after[kind];card=next(c for c in actual['categories'] if c['id']==target)
   self.assertEqual(card['content']['title']['en'],'Tree of Support Commemorative Leaf');self.assertIn('14 Chinese or 38 English characters',card['content']['description']['en'])
   expected=copy.deepcopy(before);next(c for c in expected['categories'] if c['id']==target)['content']=card['content'];self.assertEqual(actual,expected)
  # Subsequent manual Manage edits must not be overwritten by the one-time update.
  card=next(c for c in after['draft']['categories'] if c['id']==target);card['content']['title']['en']='Manual later edit'
  self.assertEqual(self.call(admin,'/api/config','POST',{'config':after['draft'],'revision':after['revision'],'action':'publish'})[0],200)
  self.stop();self.start();card=next(c for c in self.call(admin,'/api/config')[1]['config']['categories'] if c['id']==target);self.assertEqual(card['content']['title']['en'],'Manual later edit')
if __name__=='__main__':unittest.main(verbosity=2)
