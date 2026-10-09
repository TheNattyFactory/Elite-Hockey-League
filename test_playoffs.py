import unittest,tempfile,os
from league import League
from genesis import simulate
class PlayoffsTest(unittest.TestCase):
 def test_full_postseason(self):
  with tempfile.TemporaryDirectory() as d:
   league=League(os.path.join(d,'ehl.db'))
   league.initialize();league.advance(168)
   seeds=league.seed_playoffs()['seeds']
   self.assertEqual(len(seeds),6)
   self.assertEqual(len(set(x['team'] for x in seeds)),6)
   for _ in range(40):
    r=league.next_playoff()
    if r.get('complete'):break
   self.assertTrue(r['complete'])
   self.assertEqual(len(league.playoff_summary()['champions']),1)
   self.assertEqual(league.summary()['phase'],'AWARDS')
 def test_playoff_no_shootout(self):
  r=simulate(seed='POSTSEASON-TEST',playoff=True)
  self.assertFalse(r['shootout'])
  self.assertNotEqual(r['score']['ATL'],r['score']['NSH'])
if __name__=='__main__':unittest.main()
