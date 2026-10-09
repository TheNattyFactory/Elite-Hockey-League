import unittest, tempfile, pathlib
from league import League
class M13Tests(unittest.TestCase):
 def test_playoff_game_methods_exist(self):
  self.assertTrue(callable(League.playoff_game))
  self.assertTrue(callable(League.playoff_games))
 def test_gamecast_contains_controls(self):
  s=(pathlib.Path(__file__).resolve().parents[1]/'static'/'gamecast.html').read_text()
  for needle in ('/api/playoff-games','/api/playoff-game','/api/saved-game','shots-map','seek','/api/teams/branding'):
   self.assertIn(needle,s)
 def test_empty_playoff_games(self):
  with tempfile.TemporaryDirectory() as td:
   l=League(str(pathlib.Path(td)/'test.db'));l.initialize()
   self.assertEqual(l.playoff_games(),[])
   with self.assertRaises(ValueError):l.playoff_game(999)
