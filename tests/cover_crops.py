"""Cover crop persistence and validation against an isolated Java server/database."""
import unittest
from integration import SystemTests, PASSWORD

class CoverTests(SystemTests):
    def test_05_cover_adjustments(self):
        admin=self.client();anon=self.client()
        self.assertEqual(self.call(admin,'/api/auth/login','POST',{'email':'admin@example.com','password':PASSWORD})[0],200)
        cfg=self.call(admin,'/api/config?admin=1')[1]
        prior=self.call(anon,'/api/config')[1]['config']
        settings={'scale':1.45,'x':-12,'y':23}
        for category in cfg['draft']['categories']:category['coverCrop']=dict(settings)
        payload={'config':cfg['draft'],'revision':cfg['revision'],'action':'draft'}
        code,saved=self.call(admin,'/api/config','POST',payload);self.assertEqual(code,200)
        self.assertEqual(self.call(anon,'/api/config')[1]['config'],prior)
        reloaded=self.call(admin,'/api/config?admin=1')[1]
        for category in reloaded['draft']['categories']:self.assertEqual(category['coverCrop'],settings)
        payload.update(revision=saved['revision'],action='publish')
        code,published=self.call(admin,'/api/config','POST',payload);self.assertEqual(code,200)
        for category in self.call(anon,'/api/config')[1]['config']['categories']:self.assertEqual(category['coverCrop'],settings)
        # Invalid adjustments cannot be persisted or published.
        payload['revision']=published['revision']
        for invalid in [{'scale':0,'x':0,'y':0},{'scale':4,'x':0,'y':0},{'scale':1,'x':101,'y':0},{'scale':1,'x':0,'y':-101},{'scale':'1;display:none','x':0,'y':0}]:
            payload['config']['categories'][0]['coverCrop']=invalid
            self.assertEqual(self.call(admin,'/api/config','POST',payload)[0],400)
        self.stop();self.start()
        for category in self.call(anon,'/api/config')[1]['config']['categories']:self.assertEqual(category['coverCrop'],settings)

if __name__=='__main__':unittest.main(verbosity=2)
