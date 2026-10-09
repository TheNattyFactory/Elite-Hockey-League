import unittest,tempfile,json
from pathlib import Path
from league import League
import appearance
class TestM11(unittest.TestCase):
 def test_appearance_validation(self):
  self.assertEqual(appearance.validate({})['helmet'],'on')
  with self.assertRaises(ValueError):appearance.validate({'skin':'neon'})
  with self.assertRaises(ValueError):appearance.validate({'unknown':'yes'})
 def test_creator_and_persistence(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(str(Path(d)/'test.db'));l.initialize()
   signed=l.sign('ATL','Demo Skater','C',look={'skin':'deep','hair':'curly'})['signed']
   with l.db() as db:p=json.loads(db.execute('SELECT profile FROM players WHERE id=?',(signed['id'],)).fetchone()[0]);self.assertEqual(p['appearance']['skin'],'deep')
   appearance.update(l,signed['id'],{'eyes':'wide','helmet':'off'})
   with l.db() as db:p=json.loads(db.execute('SELECT profile FROM players WHERE id=?',(signed['id'],)).fetchone()[0]);self.assertEqual(p['appearance']['eyes'],'wide');self.assertEqual(p['appearance']['helmet'],'off')
 def test_bad_appearance_no_signing(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(str(Path(d)/'test.db'));l.initialize()
   with self.assertRaises(ValueError):l.sign('ATL','Demo Skater','C',look={'hair':'invalid'})
   with l.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM players WHERE human=1').fetchone()[0],0)
