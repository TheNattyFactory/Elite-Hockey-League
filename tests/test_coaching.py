import tempfile,unittest
from pathlib import Path
from league import League
import coaching
class CoachingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.league=League(str(Path(self.tmp.name)/'test.db'));self.league.initialize('COACH')
 def tearDown(self):self.tmp.cleanup()
 def test_approval_and_lineup(self):
  a=coaching.apply(self.league,'ATL','coach_a');coaching.approve(self.league,a['application_id'])
  d=coaching.dashboard(self.league,'ATL');self.assertEqual(len(d['lineup']),20)
  coaching.save_lineup(self.league,'ATL','coach_a',d['lineup'])
  self.assertEqual(coaching.dashboard(self.league,'ATL')['lineup'],d['lineup'])
 def test_human_protection_and_duplicates(self):
  a=coaching.apply(self.league,'ATL','coach_a');coaching.approve(self.league,a['application_id'])
  d=coaching.dashboard(self.league,'ATL');bad=dict(d['lineup']);bad['C1']=bad['LW1']
  with self.assertRaises(ValueError):coaching.save_lineup(self.league,'ATL','coach_a',bad)
  with self.assertRaises(ValueError):coaching.save_lineup(self.league,'ATL','imposter',d['lineup'])
 def test_one_coach_per_team(self):
  a=coaching.apply(self.league,'ATL','coach_a');coaching.approve(self.league,a['application_id'])
  with self.assertRaises(ValueError):coaching.apply(self.league,'ATL','coach_b')
 def test_tactics(self):
  a=coaching.apply(self.league,'ATL','coach_a');coaching.approve(self.league,a['application_id'])
  t={'forecheck':'AGGRESSIVE','offense':'RUSH','defense':'BALANCED','physicality':'LOW','goalie_usage':'TANDEM'}
  coaching.save_tactics(self.league,'ATL','coach_a',t)
  self.assertEqual(coaching.dashboard(self.league,'ATL')['tactics']['offense'],'RUSH')
