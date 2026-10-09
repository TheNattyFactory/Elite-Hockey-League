import unittest
from genesis import make_world,check_world,lineup,sign_human,simulate
class GenesisTests(unittest.TestCase):
 def test_world(self):
  w=make_world();self.assertTrue(check_world(w));self.assertEqual(sum(len(x['roster']) for x in w.values()),184)
 def test_determinism(self):self.assertEqual(simulate('fixed'),simulate('fixed'))
 def test_reconciliation(self):
  for n in range(100):self.assertTrue(simulate(str(n))['reconciled'])
 def test_signing_protects_human(self):
  w=make_world();x=sign_human(w,'ATL','Test Skater');self.assertTrue(x['signed']['human']);self.assertEqual(len(w['ATL']['roster']),23);self.assertTrue(check_world(w))
  self.assertEqual(sum(p['human'] for p in w['ATL']['roster']),1)
 def test_lineup(self):
  w=make_world();l=lineup(w['ATL']);self.assertEqual(tuple(len(l[k]) for k in ('forwards','defense','goalies','scratches')),(12,6,2,3))
if __name__=='__main__':unittest.main()
