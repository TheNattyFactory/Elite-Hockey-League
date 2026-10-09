import unittest,tempfile,os
from league import League
import branding
class BrandingTests(unittest.TestCase):
 def test_all_franchises(self):
  teams=branding.teams();self.assertEqual(len(teams),8)
  self.assertEqual(set(teams),set(branding.COLORS))
  self.assertTrue(all(v['primary'].startswith('#') for v in teams.values()))
 def test_roster_source_of_truth(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(os.path.join(d,'db.sqlite'));l.initialize('M12')
   before=branding.roster(l,'ATL');self.assertEqual(len(before['players']),23)
   signed=l.sign('ATL','Test Athlete','C');after=branding.roster(l,'ATL')
   self.assertEqual(len(after['players']),23)
   self.assertTrue(any(p['name']=='Test Athlete' and p['human'] for p in after['players']))
 def test_unknown_team(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(os.path.join(d,'db.sqlite'))
   with self.assertRaises(ValueError):branding.roster(l,'XXX')
