import os,tempfile,unittest
from league import League
import careers
class CareerTests(unittest.TestCase):
 def test_training_and_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   path=os.path.join(d,'test.db');l=League(path);l.initialize()
   p=l.sign('ATL','Test Skater','C')['signed'];pid=p['id']
   before=careers.profile(l,pid);self.assertEqual(before['xp_balance'],50)
   after=careers.train(l,pid,'SHT',3)
   self.assertEqual(after['player']['attributes']['SHT'],13)
   self.assertEqual(after['xp_balance'],47)
   self.assertEqual(careers.profile(League(path),pid)['xp_balance'],47)
   with self.assertRaises(ValueError):careers.train(l,pid,'REF',1)
   with self.assertRaises(ValueError):careers.train(l,pid,'SHT',26)
   self.assertEqual(careers.profile(l,pid)['player']['attributes']['SHT'],13)
 def test_earned_xp_and_career_stats(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(os.path.join(d,'test.db'));l.initialize();pid=l.sign('ATL','Test Goalie','G')['signed']['id']
   l.advance(12)
   data=careers.profile(l,pid)
   self.assertGreaterEqual(data['xp_balance'],50)
   self.assertEqual(data['player']['group'],'G')
   self.assertIn('career',data)
   with self.assertRaises(ValueError):careers.train(l,pid,'SHT')
if __name__=='__main__':unittest.main()
