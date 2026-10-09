import tempfile,unittest
from pathlib import Path
from league import League
class LeagueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.league=League(Path(self.tmp.name)/'test.db');self.league.initialize()
 def tearDown(self):self.tmp.cleanup()
 def test_schedule(self):
  schedule=self.league.schedule();self.assertEqual(len(schedule),168)
  for team in ('ATL','BOS','CHI','DAL','DEN','DET','MIN','NSH'):
   self.assertEqual(sum(team in (g['home'],g['away']) for g in schedule),42)
  for a in ('ATL','BOS','CHI','DAL','DEN','DET','MIN','NSH'):
   for b in ('ATL','BOS','CHI','DAL','DEN','DET','MIN','NSH'):
    if a<b:self.assertEqual(sum(set((g['home'],g['away']))=={a,b} for g in schedule),6)
 def test_sign_and_replay(self):
  signed=self.league.sign('ATL','Test Human','C');self.assertTrue(signed['signed']['human']);self.assertEqual(self.league.summary()['players'],184)
  result=self.league.next_game();saved=self.league.game(result['id']);self.assertEqual(saved['status'],'FINAL');self.assertEqual(len(saved['events']),result['events'])
  self.assertEqual(sum(r['gp'] for r in self.league.standings()),2)
 def test_season(self):
  result=self.league.advance(168);self.assertEqual(result['simulated'],168)
  self.assertEqual(result['state']['phase'],'PLAYOFFS')
  self.assertEqual(sum(r['gp'] for r in self.league.standings()),336)
  self.assertEqual(sum(r['pts'] for r in self.league.standings())>=336,True)
 def test_no_reset(self):
  with self.assertRaises(ValueError):self.league.initialize()
if __name__=='__main__':unittest.main()
