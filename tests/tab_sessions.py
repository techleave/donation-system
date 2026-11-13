import unittest,uuid
from integration import SystemTests,PASSWORD

class TabSessionTests(SystemTests):
 def test_same_browser_independent_accounts(self):
  browser=self.client();setup=self.client()
  self.call(setup,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})
  d=self.call(setup,'/api/donors','POST',{'prefix':'Ms','englishName':'Two Tab Donor','chineseName':'','phone':'','email':'tabs@example.com'})[1]['donor']
  credentials=self.call(setup,'/api/accounts','POST',{'donorId':d['id']})[1]
  admin_tab=str(uuid.uuid4());donor_tab=str(uuid.uuid4())
  ah={'X-Session-Tab':admin_tab};dh={'X-Session-Tab':donor_tab}
  self.assertEqual(self.call(browser,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD},ah)[0],200)
  self.assertEqual(self.call(browser,'/api/auth/login','POST',credentials,dh)[0],200)
  self.assertEqual(self.call(browser,'/api/auth/me',headers=ah)[1]['user']['role'],'admin')
  self.assertEqual(self.call(browser,'/api/auth/me',headers=dh)[1]['user']['role'],'donor')
  self.assertEqual(self.call(browser,'/api/profile',headers=dh)[1]['donor']['id'],d['id'])
  self.assertEqual(self.call(browser,'/api/donors',headers=dh)[0],403)
  self.assertEqual(self.call(browser,'/api/donors',headers=ah)[0],200)
  self.assertEqual(self.call(browser,'/admin/editor?tab=requests&sessionTab='+admin_tab)[0],200)
  self.assertEqual(self.call(browser,'/admin/editor?tab=requests&sessionTab='+donor_tab)[0],403)
  self.assertEqual(self.call(browser,'/api/auth/me',headers={'Referer':self.base+'/?sessionTab='+donor_tab})[1]['user']['role'],'donor')
  self.assertIsNone(self.call(browser,'/api/auth/me',headers={'X-Session-Tab':str(uuid.uuid4())})[1]['user'])
  self.assertIsNone(self.call(browser,'/api/auth/me')[1]['user'])
  # Logging out the donor tab must leave the admin session alive.
  self.call(browser,'/signout?sessionTab='+donor_tab)
  self.assertIsNone(self.call(browser,'/api/auth/me',headers=dh)[1]['user'])
  self.assertEqual(self.call(browser,'/api/auth/me',headers=ah)[1]['user']['role'],'admin')
  self.call(browser,'/api/auth/login','POST',credentials,dh)
  self.call(browser,'/signout?sessionTab='+admin_tab)
  self.assertIsNone(self.call(browser,'/api/auth/me',headers=ah)[1]['user'])
  self.assertEqual(self.call(browser,'/api/auth/me',headers=dh)[1]['user']['role'],'donor')
  self.stop();self.start()
  self.assertEqual(self.call(browser,'/api/auth/me',headers=dh)[1]['user']['role'],'donor')

if __name__=='__main__':unittest.main(defaultTest='TabSessionTests.test_same_browser_independent_accounts',verbosity=2)
