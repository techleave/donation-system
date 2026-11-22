import unittest,uuid,base64,io,zipfile,concurrent.futures
from xml.sax.saxutils import escape
from integration import SystemTests,PASSWORD

HEADER='姓名,電話,郵箱,個人地址,捐款總額（HKD）,最新捐款日期\n'
class CumulativeImportTests(SystemTests):
 def test_cumulative_import(self):
  a=self.client();u=self.client();self.call(a,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  def upload(row,action='import'):
   code,data=self.call(a,'/api/donors/import','POST',{'csv':HEADER+row+'\n','action':action});self.assertEqual(code,200,data);return data
  row='陳大文,12345678,test@example.com,Flat 1 Hong Kong,20000,2026-11-01'
  preview=upload(row,'preview');self.assertEqual(preview['added'],1);self.assertEqual(preview['preview'][0]['newPoints'],4000)
  self.assertEqual(self.call(a,'/api/donors')[1]['donors'],[])
  upload(row);d=self.call(a,'/api/donors')[1]['donors'][0];donorid=d['id'];self.assertEqual(d['cumulativePoints'],4000)
  self.call(u,'/api/auth/login','POST',self.call(a,'/api/accounts','POST',{'donorId':donorid})[1])
  self.assertEqual(self.call(u,'/api/requests','POST',{'requestId':str(uuid.uuid4()),'category':'tree','fields':{'leaves':'1'}})[0],201)
  profile=lambda:self.call(u,'/api/profile')[1]['donor']
  self.assertEqual(profile()['entitlements']['tree']['remaining'],3);self.assertEqual(profile()['entitlements']['airport']['remaining'],4)
  upload('陳大文,,test@example.com,,25000,2026-11-02')
  d=profile();self.assertEqual(d['cumulativePoints'],5000);self.assertEqual(d['entitlements']['tree']['remaining'],4);self.assertEqual(d['address'],'Flat 1 Hong Kong');self.assertEqual(d['phone'],'12345678')
  upload('陳大文,,test@example.com,,44999,2026-11-03');self.assertEqual(profile()['cumulativePoints'],8000)
  upload('陳大文,,test@example.com,,45000,2026-11-04');self.assertEqual(profile()['cumulativePoints'],9000)
  upload('陳大文,,test@example.com,,45000,2026-11-10');self.assertEqual(profile()['cumulativePoints'],9000)
  upload(row);self.assertEqual(profile()['cumulativeDonation'],45000)
  self.assertEqual(profile()['entitlements']['tree']['used'],1)
  entries=self.call(a,'/api/donors/donations?id='+donorid)[1]['entries'];self.assertEqual(len(entries),4)
  skipped=upload('Under,,, ,4999,');self.assertEqual(skipped['skippedBelowMinimum'],1)
  # Missing email stays blank and cannot be used to provision an account.
  upload('No Email,8888,,,5000,');upload('Other Donor,9999,,,5000,')
  rows=self.call(a,'/api/donors')[1]['donors'];blank=next(x for x in rows if x['englishName']=='No Email');self.assertEqual(blank['email'],'')
  self.assertEqual(self.call(a,'/api/accounts','POST',{'donorId':blank['id']})[0],400)
  upload('No Email,8888,later@example.com,,10000,2026-11-15')
  rows=self.call(a,'/api/donors')[1]['donors'];self.assertEqual(len(rows),3);self.assertEqual(next(x for x in rows if x['email']=='later@example.com')['id'],blank['id'])
  # Real XLSX zip/cell handling, including a serial Excel date and blank cells.
  z=io.BytesIO();matrix=[HEADER.strip().split(','),['Excel Donor','','excel@example.com','','10000','46348']]
  xml='<worksheet><sheetData>'+''.join('<row>'+''.join('<c r="'+chr(65+j)+str(i+1)+'" t="inlineStr"><is><t>'+escape(v)+'</t></is></c>' for j,v in enumerate(r))+'</row>' for i,r in enumerate(matrix))+'</sheetData></worksheet>'
  with zipfile.ZipFile(z,'w') as f:f.writestr('xl/worksheets/sheet1.xml',xml)
  payload={'xlsx':base64.b64encode(z.getvalue()).decode(),'action':'import'}
  self.assertEqual(self.call(a,'/api/donors/import','POST',payload)[0],200)
  self.assertEqual(self.call(a,'/api/donors/import','POST',payload)[1]['donationUpdates'],0)
  self.stop();self.start();self.assertEqual(profile()['cumulativePoints'],9000);self.assertEqual(profile()['entitlements']['tree']['used'],1)
  self.assertEqual(self.call(self.client(),'/api/donors/import','POST',{'csv':HEADER+row,'action':'import'})[0],403)

if __name__=='__main__':unittest.main(defaultTest='CumulativeImportTests.test_cumulative_import',verbosity=2)
