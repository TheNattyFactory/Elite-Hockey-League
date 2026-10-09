import tempfile, unittest
from pathlib import Path
from league import League

class OffseasonTests(unittest.TestCase):
 def test_two_seasons_and_archive(self):
  with tempfile.TemporaryDirectory() as t:
   l=League(Path(t)/'e.db');l.initialize();human=l.sign('ATL','Genesis Human','C')['signed']['id']
   l.advance(168);l.seed_playoffs()
   for _ in range(40):
    if l.summary()['phase']=='AWARDS':break
    l.next_playoff()
   self.assertEqual(l.summary()['phase'],'AWARDS')
   award=l.finalize_awards();self.assertIn('scoring_champion',award['awards'])
   with self.assertRaises(ValueError):l.finalize_awards()
   season=l.advance_season();self.assertEqual(season['games_scheduled'],168)
   self.assertEqual(l.summary()['season'],2)
   self.assertEqual(len(l.schedule()),168)
   self.assertEqual(len(l.history()),1)
   with l.db() as db:
    self.assertEqual(db.execute('SELECT COUNT(*) FROM games WHERE season=1').fetchone()[0],168)
    self.assertEqual(db.execute('SELECT COUNT(*) FROM games WHERE season=2').fetchone()[0],168)
    self.assertEqual(db.execute('SELECT human FROM players WHERE id=?',(human,)).fetchone()[0],1)
   self.assertEqual(l.next_game()['id'],169)
   self.assertEqual(l.summary()['games']['FINAL'],1)

if __name__=='__main__':unittest.main()
