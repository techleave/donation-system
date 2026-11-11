"""Exercise unified gift config and dynamic redemption using disposable local data."""
import unittest,uuid
from integration import SystemTests,PASSWORD

class GiftTests(SystemTests):
 def test_05_unified_gifts(self):
  admin=self.client();donor=self.client();anon=self.client()
  self.assertEqual(self.call(admin,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})[0],200)
  data=self.call(admin,'/api/config?admin=1')[1];cfg=data['draft'];gid='gift'+uuid.uuid4().hex;iid=str(uuid.uuid4())
  cfg['categories'].append({'id':gid,'icon':'✧','enabled':True,'cover':'','order':4,'coverCrop':{'scale':1.4,'x':-5,'y':12},'content':{'title':{'zh':'紀念葉','en':'Commemorative leaf'},'short':{'zh':'專屬紀念','en':'Personalised for you'},'description':{'zh':'最多十四個中文字','en':'Up to 38 English characters'}}})
  cfg['fields'][gid]=[{'key':'requirements','label':{'zh':'製作要求','en':'Requirements'},'type':'textarea','required':True,'maxLength':2000},{'key':'explanation','label':{'zh':'請核對資料','en':'Check your details'},'type':'description','required':False}]
  cfg['items'].append({'id':iid,'category':gid,'title':{'zh':'紀念葉','en':'Leaf'},'description':{'zh':'說明','en':'Description'},'points':1000,'enabled':True})
  payload={'config':cfg,'revision':data['revision'],'action':'draft'};code,saved=self.call(admin,'/api/config','POST',payload);self.assertEqual(code,200)
  self.assertFalse(any(c['id']==gid for c in self.call(anon,'/api/config')[1]['config']['categories']))
  payload.update(revision=saved['revision'],action='publish');code,saved=self.call(admin,'/api/config','POST',payload);self.assertEqual(code,200)
  public=self.call(anon,'/api/config')[1]['config'];self.assertEqual(public['categories'][-1]['content']['title']['en'],'Commemorative leaf');self.assertEqual(public['categories'][-1]['coverCrop']['scale'],1.4)
  code,d=self.call(admin,'/api/donors','POST',{'prefix':'Ms','englishName':'Gift Test','chineseName':'','phone':'','email':'gift-test@example.com'});self.assertEqual(code,201);d=d['donor']
  self.assertEqual(self.call(admin,'/api/donors/donations','POST',{'donorId':d['id'],'entryId':str(uuid.uuid4()),'revision':d['revision'],'cumulativeDonation':5000,'donationDate':'2026-11-11'})[0],200)
  credentials=self.call(admin,'/api/accounts','POST',{'donorId':d['id']})[1];self.assertEqual(self.call(donor,'/api/auth/login','POST',credentials)[0],200)
  profile=lambda:self.call(donor,'/api/profile')[1]['donor']
  self.assertEqual(profile()['entitlements'][gid]['remaining'],1)
  request={'requestId':str(uuid.uuid4()),'category':gid,'itemId':iid,'fields':{}}
  self.assertEqual(self.call(donor,'/api/requests','POST',request)[0],400)
  request['fields']={'requirements':'Please put our name on the leaf'};code,result=self.call(donor,'/api/requests','POST',request);self.assertEqual(code,201)
  self.assertNotIn('explanation',result['fields']);self.assertEqual(result['fields']['requirements']['value'],request['fields']['requirements'])
  self.assertEqual(self.call(donor,'/api/requests','POST',request)[0],200)
  self.assertEqual(profile()['entitlements'][gid]['remaining'],0)
  for category in ['tree','airport','card','ticket']:self.assertEqual(profile()['entitlements'][category]['remaining'],1)
  self.assertEqual(self.call(donor,'/api/requests','POST',dict(request,requestId=str(uuid.uuid4())))[0],409)
  # Downlisting retains fields, requests and usage, and prevents new submissions.
  cfg['categories'][-1].update(archived=True,enabled=False);payload.update(config=cfg,revision=saved['revision']);code,saved=self.call(admin,'/api/config','POST',payload);self.assertEqual(code,200)
  self.assertEqual(self.call(donor,'/api/requests','POST',dict(request,requestId=str(uuid.uuid4())))[0],400)
  self.assertEqual(profile()['entitlements'][gid]['used'],1)
  cfg['categories'][-1].update(archived=False,enabled=True);payload.update(revision=saved['revision']);self.assertEqual(self.call(admin,'/api/config','POST',payload)[0],200)
  self.stop();self.start()
  self.assertEqual(profile()['entitlements'][gid]['used'],1)
  self.assertEqual(self.call(anon,'/api/config')[1]['config']['categories'][-1]['content']['description']['en'],'Up to 38 English characters')

if __name__=='__main__':unittest.main(verbosity=2)
