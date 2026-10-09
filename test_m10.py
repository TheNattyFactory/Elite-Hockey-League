import unittest, tempfile, os
from league import League
import careers
class M10(unittest.TestCase):
 def test_profile_endpoint_function(self):
  with tempfile.TemporaryDirectory() as d:
   league=League(os.path.join(d,'test.db'));league.initialize();p=league.sign('ATL','Dashboard Player','C');pid=p['signed']['id'];self.assertIsNotNone(pid);self.assertIn('xp_balance',careers.profile(league,pid))
 def test_ui_assets(self):
  from pathlib import Path
  page=(Path(__file__).resolve().parents[1]/'static'/'player.html').read_text();self.assertIn('/api/player/train',page);self.assertIn('Career statistics',page)
