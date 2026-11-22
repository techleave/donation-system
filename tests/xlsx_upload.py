import base64, io, zipfile, unittest
from pathlib import Path
from integration import SystemTests, PASSWORD

FIXTURE=Path(__file__).resolve().parent/'fixtures/donor-upload.xlsx'
class XlsxUploadTests(SystemTests):
 def test_supplied_workbook(self):
  a=self.client();self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  cfg=self.call(a,'/api/config?admin=1')[1];c=cfg['draft'];leaf='gift66e7d1f75cda4ddd93ef092ecfa59178';c['categories'].append({'id':leaf,'enabled':True,'icon':'✧','cover':'','order':5});c['fields'][leaf]=[]
  self.assertEqual(self.call(a,'/api/config','POST',{'config':c,'revision':cfg['revision'],'action':'publish'})[0],200)
  data=FIXTURE.read_bytes()
  def upload(data,action):return self.call(a,'/api/donors/import','POST',{'xlsx':base64.b64encode(data).decode(),'action':action})
  code,p=upload(data,'preview');self.assertEqual(code,200,p);self.assertEqual(p['total'],4);self.assertEqual(p['added'],3);self.assertEqual(p['skippedBelowMinimum'],1)
  self.assertEqual(self.call(a,'/api/donors')[1]['donors'],[])
  code,p=upload(data,'import');self.assertEqual(code,200,p)
  donors=self.call(a,'/api/donors')[1]['donors'];self.assertEqual(len(donors),3)
  expected={'hkicf-test-a@example.com':1,'hkicf-test-b@example.com':2,'hkicf-test-c@example.com':1}
  for d in donors:
   self.assertEqual(d['latestDonationDate'],'2026-11-22')
   for cat in ['tree','airport','card','gift66e7d1f75cda4ddd93ef092ecfa59178']:self.assertEqual(d['entitlements'][cat]['remaining'],expected[d['email']])
  self.assertEqual(upload(data,'import')[1]['donationUpdates'],0)
  # Equivalent default-namespace XML with inline strings and ISO date cells.
  out=io.BytesIO()
  with zipfile.ZipFile(io.BytesIO(data)) as z,zipfile.ZipFile(out,'w') as target:
   for name in z.namelist():
    value=z.read(name)
    if name.endswith('sheet1.xml'):
     text=value.decode().replace('x:','').replace('xmlns:x=','xmlns=').replace('t="n"><v>46348</v>','t="d"><v>2026-11-22T00:00:00</v>')
     value=text.encode()
    target.writestr(name,value)
  self.assertEqual(upload(out.getvalue(),'preview')[0],200)
  self.assertEqual(self.call(self.client(),'/api/donors/import','POST',{'xlsx':base64.b64encode(data).decode(),'action':'import'})[0],403)
if __name__=='__main__':unittest.main(defaultTest='XlsxUploadTests.test_supplied_workbook',verbosity=2)
